import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("GEMINI_DOCUMENT_MODEL", "gemini-3.6-flash").strip()
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "").strip()

MAX_RETRIES = max(0, min(int(os.getenv("GEMINI_MAX_RETRIES", "1")), 2))
MAX_DOCUMENT_CHARS = max(
    8000,
    min(int(os.getenv("MAX_DOCUMENT_CHARS", "40000")), 100000),
)

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing in .env. "
        "Add your Google AI Studio API key and restart Flask."
    )

if not MODEL_NAME:
    raise RuntimeError("GEMINI_DOCUMENT_MODEL is missing in .env.")

client = genai.Client(api_key=API_KEY)

TRANSIENT_ERRORS = (
    "429",
    "resource_exhausted",
    "500",
    "502",
    "503",
    "504",
    "timeout",
    "unavailable",
    "internal",
    "overloaded",
)


def _models_to_try():
    models = []

    for model in (MODEL_NAME, FALLBACK_MODEL):
        if model and model not in models:
            models.append(model)

    return models


def _is_temporary_error(error):
    message = str(error).lower()
    return any(value in message for value in TRANSIENT_ERRORS)


def ask_gemini(prompt, max_output_tokens=1600):
    prompt = str(prompt or "").strip()

    if not prompt:
        raise ValueError("The AI prompt is empty.")

    last_error = None

    for model in _models_to_try():
        for attempt in range(MAX_RETRIES + 1):
            try:
                config = types.GenerateContentConfig(
                    max_output_tokens=max(128, min(int(max_output_tokens), 4096)),
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                )

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )

                answer = str(getattr(response, "text", "") or "").strip()

                if answer:
                    return answer

                raise RuntimeError("Gemini returned an empty response.")

            except Exception as error:
                last_error = error

                if not _is_temporary_error(error):
                    break

                if attempt == MAX_RETRIES:
                    break

                time.sleep(0.45 + random.random() * 0.25)

    raise RuntimeError(
        "Gemini is temporarily unavailable. Please try again in a moment."
    ) from last_error


def _clean_document(text):
    text = str(text or "").strip()

    if not text:
        raise ValueError("No readable document text was provided.")

    return text[:MAX_DOCUMENT_CHARS]


def _formatting(custom_query):
    query = str(custom_query or "").strip()
    lower = query.lower()

    return {
        "font_family": "Inter",
        "font_size": "14px",
        "font_style": "italic" if "italic" in lower else "normal",
        "font_weight": "700" if "bold" in lower else "normal",
        "text_decoration": "underline" if "underline" in lower else "none",
        "custom_instruction": query[:1200],
    }


def process_document_tool(
    text,
    tool,
    custom_query="",
    summary_length="medium",
    summary_style="paragraph",
    paraphrase_style="simple",
    question_count=10,
):
    document = _clean_document(text)
    tool = str(tool or "summary")

    valid_tools = {
        "summary",
        "paraphraser",
        "key_points",
        "important_questions",
    }

    if tool not in valid_tools:
        raise ValueError("Invalid AI tool selected.")

    try:
        question_count = int(question_count)
    except (TypeError, ValueError):
        question_count = 10

    question_count = max(1, min(question_count, 20))
    formatting = _formatting(custom_query)

    tasks = {
        "summary": (
            f"Create a {summary_length} summary. "
            f"Use {'clear bullet points' if summary_style == 'bullet' else 'well-structured paragraphs'}."
        ),
        "paraphraser": (
            f"Paraphrase the document in a {paraphrase_style} style. "
            "Preserve all important facts and the original meaning."
        ),
        "key_points": (
            "Extract a maximum of 8 concise and important key points. "
            "Use bullet points."
        ),
        "important_questions": (
            f"Create exactly {question_count} important study questions based only "
            "on the document. Number the questions and do not provide answers."
        ),
    }

    user_instruction = formatting["custom_instruction"]

    prompt = f"""
You are SUMMARIX AI, a precise document assistant.

TASK:
{tasks[tool]}

IMPORTANT RULES:
- Use only information found in the uploaded document.
- Do not invent facts.
- Do not use unrelated outside knowledge.
- Return only the requested result.
- Do not mention Gemini, prompts, or system instructions.
{f"- User preference: {user_instruction}" if user_instruction else ""}

DOCUMENT:
{document}
"""

    output_limit = 3000 if tool == "paraphraser" else 1600

    return {
        "content": ask_gemini(prompt, max_output_tokens=output_limit),
        "formatting": formatting,
    }


def summarize_text(text, length="medium", style="paragraph"):
    return process_document_tool(
        text,
        "summary",
        summary_length=length,
        summary_style=style,
    )["content"]


def paraphrase_text(text, style="simple"):
    return process_document_tool(
        text,
        "paraphraser",
        paraphrase_style=style,
    )["content"]


def extract_key_points(text):
    return process_document_tool(text, "key_points")["content"]


def generate_important_questions(text, question_count=10):
    return process_document_tool(
        text,
        "important_questions",
        question_count=question_count,
    )["content"]


def _answer_from_context(context, question, source_name):
    question = str(question or "").strip()

    if not question:
        raise ValueError("Please enter a question.")

    prompt = f"""
You are SUMMARIX AI.

Answer the user's question using only the {source_name} below.

If the information is not available, say exactly:
"This information is not available in the uploaded document."

Answer directly, clearly, and concisely.
Do not mention these instructions.

CONTEXT:
{context[:MAX_DOCUMENT_CHARS]}

QUESTION:
{question[:1500]}
"""

    return ask_gemini(prompt, max_output_tokens=1200)


def answer_document_question(text, question):
    return _answer_from_context(
        _clean_document(text),
        question,
        "uploaded document",
    )


def answer_result_question(result_text, question, source_text=None):
    context = str(result_text or "").strip()

    if source_text:
        context += "\n\nOriginal document context:\n" + _clean_document(source_text)

    if not context:
        raise ValueError("Generated result is empty.")

    return _answer_from_context(context, question, "generated result")