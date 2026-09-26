import io
import os
import sqlite3
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from ai_summarizer import (
    answer_document_question,
    answer_result_question,
    process_document_tool,
)
from chatbot_ai import (
    chat_reply,
    search_videos,
    study_reply,
)
from document_processor import (
    extract_document,
    extract_text,
)


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

load_dotenv(
    os.path.join(BASE_DIR, ".env"),
    override=True,
)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
STATE_FOLDER = os.path.join(BASE_DIR, "runtime_state")
DATABASE_PATH = os.path.join(STATE_FOLDER, "summarix.db")

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

RESULTS = {}
DOCUMENTS = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATE_FOLDER, exist_ok=True)


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key",
)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


def get_database():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


initialize_database()


def allowed_file(filename):
    extension = os.path.splitext(filename)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def safe_upload_path(file_path):
    try:
        return (
            os.path.commonpath(
                [
                    os.path.abspath(file_path),
                    os.path.abspath(UPLOAD_FOLDER),
                ]
            )
            == os.path.abspath(UPLOAD_FOLDER)
        )

    except ValueError:
        return False


def current_document():
    file_path = session.get("document_path")
    document_name = session.get("document_name")

    if (
        not file_path
        or not document_name
        or not safe_upload_path(file_path)
        or not os.path.exists(file_path)
    ):
        raise ValueError(
            "Please upload a PDF or DOCX document first."
        )

    text = extract_text(file_path)

    if not text.strip():
        raise ValueError(
            "No readable text was found in the document."
        )

    return document_name, text


def selected_chat_documents():
    document_ids = session.get("chat_document_ids", [])

    return [
        DOCUMENTS[document_id]
        for document_id in document_ids
        if document_id in DOCUMENTS
    ]


def save_message(conversation_id, role, content):
    with get_database() as connection:
        connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                datetime.utcnow().isoformat(),
            ),
        )


def ensure_conversation(conversation_id, first_text="New conversation"):
    conversation_id = str(
        conversation_id or uuid.uuid4().hex
    )

    with get_database() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

        if not existing:
            title = " ".join(
                str(first_text).split()
            )[:55]

            if not title:
                title = "New conversation"

            connection.execute(
                """
                INSERT INTO conversations (
                    id,
                    title,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    conversation_id,
                    title,
                    datetime.utcnow().isoformat(),
                ),
            )

    return conversation_id


@app.route("/")
def home():
    return redirect(url_for("workspace"))


@app.route("/workspace", methods=["GET", "POST"])
def workspace():
    result = None
    error = None
    formatting = {}

    active_tool = request.args.get(
        "tool",
        "summary",
    )

    custom_query = ""

    if request.method == "POST":
        active_tool = request.form.get(
            "tool",
            "summary",
        )

        custom_query = request.form.get(
            "custom_query",
            "",
        ).strip()

        try:
            uploaded_file = request.files.get("document")

            if uploaded_file and uploaded_file.filename:
                filename = secure_filename(
                    uploaded_file.filename
                )

                if not allowed_file(filename):
                    raise ValueError(
                        "Only PDF and DOCX files are supported."
                    )

                file_path = os.path.join(
                    UPLOAD_FOLDER,
                    f"{uuid.uuid4().hex}_{filename}",
                )

                uploaded_file.save(file_path)

                session["document_path"] = file_path
                session["document_name"] = filename

            _, document_text = current_document()

            result_data = process_document_tool(
                text=document_text,
                tool=active_tool,
                custom_query=custom_query,
                summary_length=request.form.get(
                    "summary_length",
                    "medium",
                ),
                summary_style=request.form.get(
                    "summary_style",
                    "paragraph",
                ),
                paraphrase_style=request.form.get(
                    "paraphrase_style",
                    "simple",
                ),
                question_count=request.form.get(
                    "question_count",
                    10,
                ),
            )

            result = result_data["content"]
            formatting = result_data["formatting"]

            result_id = uuid.uuid4().hex

            RESULTS[result_id] = {
                "result": result,
                "document": document_text,
            }

            session["last_result_id"] = result_id

        except Exception as exception:
            error = str(exception)

    return render_template(
        "workspace.html",
        result=result,
        error=error,
        formatting=formatting,
        document_name=session.get("document_name"),
        active_tool=active_tool,
        custom_query=custom_query,
        result_id=session.get("last_result_id", ""),
    )


@app.route("/api/document-question", methods=["POST"])
def document_question():
    try:
        data = request.get_json(silent=True) or {}

        _, document_text = current_document()

        answer = answer_document_question(
            document_text,
            data.get("question", ""),
        )

        return jsonify(
            success=True,
            answer=answer,
        )

    except Exception as exception:
        return jsonify(
            success=False,
            error=str(exception),
        ), 400


@app.route("/api/result-question", methods=["POST"])
def result_question():
    try:
        data = request.get_json(silent=True) or {}

        result_id = (
            data.get("result_id")
            or session.get("last_result_id")
        )

        item = RESULTS.get(result_id)

        if not item:
            raise ValueError(
                "Generate a result before asking about it."
            )

        answer = answer_result_question(
            item["result"],
            data.get("question", ""),
            item["document"],
        )

        return jsonify(
            success=True,
            answer=answer,
        )

    except Exception as exception:
        return jsonify(
            success=False,
            error=str(exception),
        ), 400


@app.route(
    "/api/chat/documents",
    methods=["GET", "POST", "DELETE"],
)
def chat_documents():
    if request.method == "DELETE":
        session["chat_document_ids"] = []

        return jsonify(success=True)

    if request.method == "POST":
        try:
            uploaded_files = request.files.getlist(
                "documents"
            )

            if not uploaded_files:
                raise ValueError(
                    "Choose one or more PDF or DOCX files."
                )

            document_ids = session.get(
                "chat_document_ids",
                [],
            )

            for uploaded_file in uploaded_files[:5]:
                filename = secure_filename(
                    uploaded_file.filename
                )

                if (
                    not filename
                    or not allowed_file(filename)
                ):
                    raise ValueError(
                        "Only PDF and DOCX files are supported."
                    )

                file_path = os.path.join(
                    UPLOAD_FOLDER,
                    f"{uuid.uuid4().hex}_{filename}",
                )

                uploaded_file.save(file_path)

                document_id = uuid.uuid4().hex

                extracted_document = extract_document(
                    file_path
                )

                DOCUMENTS[document_id] = {
                    "id": document_id,
                    "path": file_path,
                    **extracted_document,
                }

                document_ids.append(document_id)

            session["chat_document_ids"] = document_ids[-5:]

            return jsonify(
                success=True,
                documents=[
                    {
                        "id": item["id"],
                        "name": item["name"],
                    }
                    for item in selected_chat_documents()
                ],
            )

        except Exception as exception:
            return jsonify(
                success=False,
                error=str(exception),
            ), 400

    return jsonify(
        success=True,
        documents=[
            {
                "id": item["id"],
                "name": item["name"],
            }
            for item in selected_chat_documents()
        ],
    )


@app.route(
    "/api/chat/documents/<document_id>",
    methods=["DELETE"],
)
def remove_chat_document(document_id):
    session["chat_document_ids"] = [
        item
        for item in session.get(
            "chat_document_ids",
            [],
        )
        if item != document_id
    ]

    return jsonify(success=True)


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        messages = data.get("messages", [])

        if not isinstance(messages, list):
            raise ValueError("Invalid chat history.")

        user_text = next(
            (
                item.get("content", "")
                for item in reversed(messages)
                if item.get("role") == "user"
            ),
            "",
        )

        conversation_id = ensure_conversation(
            data.get("conversation_id"),
            user_text,
        )

        answer, sources = chat_reply(
            messages=messages,
            mode=data.get("mode", "general"),
            documents=selected_chat_documents(),
            preferences=data.get("preferences", {}),
        )

        save_message(
            conversation_id,
            "user",
            user_text,
        )

        save_message(
            conversation_id,
            "assistant",
            answer,
        )

        return jsonify(
            success=True,
            conversation_id=conversation_id,
            answer=answer,
            sources=sources,
        )

    except Exception as exception:
        return jsonify(
            success=False,
            error=str(exception),
        ), 400


@app.route("/api/study", methods=["POST"])
def study():
    try:
        data = request.get_json(silent=True) or {}

        answer, sources = study_reply(
            action=data.get("action"),
            topic=data.get("topic"),
            documents=selected_chat_documents(),
            preferences=data.get("preferences", {}),
        )

        return jsonify(
            success=True,
            answer=answer,
            sources=sources,
        )

    except Exception as exception:
        return jsonify(
            success=False,
            error=str(exception),
        ), 400


@app.route("/api/chat/videos", methods=["POST"])
def videos():
    data = request.get_json(silent=True) or {}

    return jsonify(
        success=True,
        videos=search_videos(
            data.get("query", "")
        ),
    )


@app.route("/api/conversations", methods=["GET", "DELETE"])
def conversations():
    with get_database() as connection:
        if request.method == "DELETE":
            connection.execute("DELETE FROM messages")
            connection.execute("DELETE FROM conversations")

            return jsonify(success=True)

        rows = connection.execute(
            """
            SELECT id, title, created_at
            FROM conversations
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()

    return jsonify(
        success=True,
        conversations=[
            dict(row)
            for row in rows
        ],
    )


@app.route(
    "/api/conversations/<conversation_id>",
    methods=["GET", "DELETE"],
)
def conversation(conversation_id):
    with get_database() as connection:
        if request.method == "DELETE":
            connection.execute(
                """
                DELETE FROM messages
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )

            connection.execute(
                """
                DELETE FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            )

            return jsonify(success=True)

        rows = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id
            """,
            (conversation_id,),
        ).fetchall()

    return jsonify(
        success=True,
        messages=[
            dict(row)
            for row in rows
        ],
    )


@app.route("/api/chat/export", methods=["POST"])
def export_chat():
    data = request.get_json(silent=True) or {}

    messages = data.get("messages", [])[-100:]
    export_format = data.get("format", "txt")

    content = "SUMMARIX AI CHAT EXPORT\n\n"

    for item in messages:
        role = str(
            item.get("role", "assistant")
        ).title()

        message = str(item.get("content", ""))

        content += f"{role}: {message}\n\n"

    if export_format == "docx":
        from docx import Document

        document = Document()

        document.add_heading(
            "SUMMARIX AI Chat Export",
            0,
        )

        for item in messages:
            document.add_heading(
                str(
                    item.get(
                        "role",
                        "assistant",
                    )
                ).title(),
                2,
            )

            document.add_paragraph(
                str(item.get("content", ""))
            )

        output = io.BytesIO()

        document.save(output)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="summarix-chat.docx",
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )

    if export_format == "pdf":
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        output = io.BytesIO()

        pdf = canvas.Canvas(
            output,
            pagesize=A4,
        )

        text = pdf.beginText(40, 800)

        for line in content.splitlines():
            parts = [
                line[index:index + 95]
                for index in range(
                    0,
                    max(1, len(line)),
                    95,
                )
            ]

            for part in parts:
                text.textLine(part)

                if text.getY() < 45:
                    pdf.drawText(text)
                    pdf.showPage()
                    text = pdf.beginText(40, 800)

        pdf.drawText(text)
        pdf.save()

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="summarix-chat.pdf",
            mimetype="application/pdf",
        )

    output = io.BytesIO(
        content.encode("utf-8")
    )

    return send_file(
        output,
        as_attachment=True,
        download_name="summarix-chat.txt",
        mimetype="text/plain",
    )


@app.errorhandler(413)
def file_too_large(error):
    return jsonify(
        success=False,
        error="File is too large. Maximum size is 25 MB.",
    ), 413


if __name__ == "__main__":
    print(
        "SUMMARIX AI: "
        "http://127.0.0.1:5000/workspace"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )