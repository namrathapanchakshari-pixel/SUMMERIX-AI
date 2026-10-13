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

try:
    MAX_RETRIES = max(0, min(int(os.getenv("GEMINI_MAX_RETRIES", "1")), 2))
except (TypeError, ValueError):
    MAX_RETRIES = 1

try:
    MAX_DOCUMENT_CHARS = max(
        8000,
        min(int(os.getenv("MAX_DOCUMENT_CHARS", "40000")), 100000),
    )
except (TypeError, ValueError):
    MAX_DOCUMENT_CHARS = 40000

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
    "temporarily",
)


def _is_temporary_error(error):
    message = str(error).lower()
    return any(value in message for value in TRANSIENT_ERRORS)


def ask_gemini(prompt, max_output_tokens=1600):
    """Make one request to the configured Gemini model without switching models."""
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ValueError("The AI prompt is empty.")

    try:
        token_limit = max(128, min(int(max_output_tokens), 4096))
    except (TypeError, ValueError):
        token_limit = 1600

    try:
        config = types.GenerateContentConfig(
            max_output_tokens=token_limit,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        answer = str(getattr(response, "text", "") or "").strip()
        if answer:
            return answer
        raise RuntimeError(f"Gemini model '{MODEL_NAME}' returned an empty response.")
    except Exception as error:
        temporary = _is_temporary_error(error)
        print(
            "\n[SUMMARIX AI Gemini Error]"
            f"\nModel: {MODEL_NAME}"
            "\nAttempt: 1/1"
            f"\nError type: {type(error).__name__}"
            f"\nTemporary error: {temporary}"
            f"\nDetails: {error}\n",
            flush=True,
        )
        if temporary:
            raise RuntimeError(
                 f"Gemini model '{MODEL_NAME}' is temporarily unavailable. "
                 "Please try again shortly."
            ) from error

        raise RuntimeError(
            f"Gemini request failed for {MODEL_NAME}: {str(error)[:400]}"
        ) from error

def _clean_document(text):
    text = str(text or "").strip()
    if not text:
        raise ValueError("No readable document text was provided.")
    return text[:MAX_DOCUMENT_CHARS]


def _offline_document_result(
    document,
    tool,
    summary_length="medium",
    summary_style="paragraph",
    paraphrase_style="simple",
    question_count=10,
):
    """
    Readable offline fallback.
    This is extractive: it selects useful source sentences and does not invent facts.
    """
    import re
    from collections import Counter

    raw = str(document or "").replace("\x00", " ").strip()
    if not raw:
        return "No readable document text was available."

    # Normalize whitespace but preserve boundaries that often separate headings/items.
    raw = raw.replace("\r", "\n")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{2,}", "\n", raw)

    # Split into candidate sentences / lines.
    candidates = []
    for line in raw.splitlines():
        line = line.strip(" \t•*-")
        if not line:
            continue
        pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", line)
        candidates.extend(piece.strip() for piece in pieces if piece.strip())

    if not candidates:
        candidates = [raw]

    code_patterns = (
        r"^\s*(?:<\?php|<\?=|<script\b|</?\w+[^>]*>)",
        r"^\s*(?:echo|print|printf|var_dump|return\s|function\s|class\s|public\s|private\s|if\s*\(|else\b|for\s*\(|while\s*\(|SELECT\b|INSERT\b|UPDATE\b|DELETE\b|import\s+\w+|from\s+\w+\s+import\b)",
        r"^\s*[\$\w]+\s*=\s*[^.]{0,100};\s*$",
        r"^\s*(?:output|result)\s*:\s*",
        r"^\s*[\{\}\[\]();]+$",
    )

    def looks_like_code(sentence):
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in code_patterns):
            return True
        # Drop code-heavy fragments with many programming symbols and little prose.
        letters = sum(ch.isalpha() for ch in sentence)
        symbols = sum(ch in "{}[]();=<>$\\|" for ch in sentence)
        if len(sentence) > 0 and symbols / len(sentence) > 0.16 and letters < 45:
            return True
        return False

    def normalize_sentence(sentence):
        sentence = re.sub(r"^[\d.)\s:-]+", "", sentence).strip()
        sentence = re.sub(r"\s+", " ", sentence)
        return sentence

    cleaned = []
    seen = set()
    for candidate in candidates:
        sentence = normalize_sentence(candidate)
        if len(sentence) < 28 or looks_like_code(sentence):
            continue
        # Exclude common document labels and question-only fragments.
        if re.match(r"^(?:question|query string|output|example|program|syntax)\s*:", sentence, re.I):
            continue
        if sentence.count("?") > 0 and len(sentence.split()) < 12:
            continue
        key = re.sub(r"\W+", "", sentence.lower())
        if key and key not in seen:
            seen.add(key)
            cleaned.append(sentence)

    # If filtering removed everything, retain readable non-code lines instead of returning nothing.
    if not cleaned:
        for candidate in candidates:
            sentence = normalize_sentence(candidate)
            if len(sentence) >= 35 and not looks_like_code(sentence):
                cleaned.append(sentence)
            if len(cleaned) >= 8:
                break

    if not cleaned:
        return (
            "Gemini is temporarily unavailable. The document text did not contain "
            "enough readable prose to create a reliable local summary. Please try again later."
         )

    # Score sentences for informative prose and spread selections across the source.
    stop_words = {
        "the", "and", "for", "that", "with", "this", "from", "are", "was",
        "were", "has", "have", "had", "into", "which", "their", "there",
        "then", "than", "when", "where", "what", "who", "will", "would",
        "can", "could", "should", "not", "but", "you", "your", "they",
        "them", "its", "also", "such", "using", "used", "use", "how",
        "why", "about", "between", "each", "these", "those", "being",
    }
    all_words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", " ".join(cleaned).lower())
    frequencies = Counter(word for word in all_words if word not in stop_words)

    scored = []
    for index, sentence in enumerate(cleaned):
        words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", sentence.lower())
        informative = sum(min(frequencies.get(word, 0), 3) for word in words if word not in stop_words)
        length_bonus = min(len(sentence), 180) / 180
        definition_bonus = 1.5 if re.search(r"\b(is|are|means|refers to|defined as|allows|supports|used for|consists of)\b", sentence, re.I) else 0
        heading_penalty = 1.0 if len(words) < 7 else 0
        score = (informative / max(len(words), 1)) + length_bonus + definition_bonus - heading_penalty
        scored.append((score, index, sentence))

    if tool == "summary":
        limits = {"short": 3, "medium": 6, "long": 10}
        count = limits.get(str(summary_length).lower(), 6)
        # Select highest-scoring sentences, then restore the document's original order.
        chosen = sorted(scored, key=lambda item: item[0], reverse=True)[:count]
        selected = [item[2] for item in sorted(chosen, key=lambda item: item[1])]
        header = "SUMMARY"
        if summary_style == "bullet":
            return header + "\n\n" + "\n".join(f"• {item}" for item in selected)
        return header + "\n\n" + " ".join(selected)

    if tool == "key_points":
        chosen = sorted(scored, key=lambda item: item[0], reverse=True)[:8]
        selected = [item[2] for item in sorted(chosen, key=lambda item: item[1])]
        return " KEY POINTS \n\n" + "\n".join(
            f"• {item}" for item in selected
        )

    if tool == "important_questions":
        selected = [item[2] for item in sorted(scored, key=lambda item: item[0], reverse=True)[:question_count]]
        questions = [
            f"{i}. What does the document explain about {sentence.rstrip('.!?')}?"
            for i, sentence in enumerate(selected, 1)
        ]
        return "IMPORTANT QUESTIONS \n\n" + "\n".join(questions)

    if tool == "paraphraser":
        return (
            "PARAPHRASER.\n\n" + raw
        )

    return " ".join(cleaned)

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
    try:
        content = ask_gemini(prompt, max_output_tokens=output_limit)
    except Exception as error:
        # Do not leave the user's workspace empty during a Gemini outage.
        print(
            f"[SUMMARIX AI] Using local document fallback for '{tool}' because Gemini failed: {error}",
            flush=True,
        )
        content = _offline_document_result(
            document,
            tool,
            summary_length=summary_length,
            summary_style=summary_style,
            paraphrase_style=paraphrase_style,
            question_count=question_count,
        )
    return {
        "content": content,
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

    context = str(context or "").strip()
    if not context:
        raise ValueError("No context was provided to answer the question.")

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
    try:
        return ask_gemini(prompt, max_output_tokens=1200)
    except Exception as error:
        if not _is_temporary_error(error) and "temporarily busy or unavailable" not in str(error).lower():
            raise
        # A simple source-grounded fallback: return sentences containing question keywords.
        import re
        from collections import Counter

        words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", question.lower())
        stop = {"what", "when", "where", "which", "who", "whom", "does", "this", "that", "with", "from", "about", "explain", "tell", "please", "document"}
        keywords = [word for word in words if word not in stop]
        sentences = re.split(r"(?<=[.!?])\s+|\n+", context)
        ranked = []
        for index, sentence in enumerate(sentences):
            sentence = sentence.strip(" \t•*-")
            if len(sentence) < 25:
                continue
            sentence_words = set(re.findall(r"[A-Za-z][A-Za-z'-]{2,}", sentence.lower()))
            score = sum(1 for word in keywords if word in sentence_words)
            if score:
                ranked.append((score, index, sentence))
        if not ranked:
            return (
                "Gemini 3.6 Flash is temporarily unavailable, and I could not find a "
                "clear matching passage in the available text. Please try this question again later."
            )
        selected = sorted(ranked, key=lambda item: (-item[0], item[1]))[:4]
        selected.sort(key=lambda item: item[1])
        return (
            "LOCAL DOCUMENT ANSWER (Gemini temporarily unavailable)\n\n"
            + " ".join(item[2] for item in selected)
            + "\n\nNote: This is extracted from matching document passages, not an AI-generated answer."
        )


def answer_document_question(text, question):
    return _answer_from_context(
        _clean_document(text),
        question,
        "uploaded document",
    )


def answer_result_question(result_text, question, source_text=None):
    context = str(result_text or "").strip()
    if source_text:
        source = _clean_document(source_text)
        context += "\n\nOriginal document context:\n" + source
    if not context:
        raise ValueError("Generated result is empty.")
    return _answer_from_context(context, question, "generated result")
