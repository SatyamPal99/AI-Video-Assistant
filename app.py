"""
Flask API for the AI Video Assistant.

Wraps the existing pipeline (utils.audio_processor, core.transcriber,
core.summarizer, core.extractor, core.rag_engine) behind a small REST API
that a React frontend can talk to.

Processing runs in a background thread per request so the client can poll
/api/status/<job_id> and show live progress instead of blocking on one
long HTTP call. This is deliberately an in-memory job store (a plain dict) —
perfect for local/single-user use. If you ever need multiple worker
processes or persistence across restarts, swap `jobs` for Redis or a DB.
"""

import os
import threading
import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

app = Flask(__name__)
CORS(app)  # allow the Vite dev server (different port) to call this API

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# job_id -> {status, stage, result, rag_chain, error, ...}
jobs: dict[str, dict] = {}


def run_pipeline_job(job_id: str, source: str, language: str) -> None:
    """Runs the full pipeline, updating jobs[job_id]['stage'] as it goes
    so the frontend can show real progress instead of a generic spinner."""
    job = jobs[job_id]
    try:
        job["status"] = "processing"

        job["stage"] = "Reading source"
        chunks = process_input(source)

        job["stage"] = "Transcribing audio"
        transcript = transcribe_all(chunks, language)

        job["stage"] = "Naming the session"
        title = generate_title(transcript)

        job["stage"] = "Summarizing"
        summary = summarize(transcript)

        job["stage"] = "Pulling out action items"
        action_items = extract_action_items(transcript)

        job["stage"] = "Pulling out key decisions"
        decisions = extract_key_decisions(transcript)

        job["stage"] = "Pulling out open questions"
        questions = extract_questions(transcript)

        job["stage"] = "Indexing transcript for chat"
        rag_chain = build_rag_chain(transcript)

        job["result"] = {
            "title": title,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
        }
        # rag_chain is not JSON-serializable, so it's kept server-side only
        # and referenced later by job_id in /api/chat.
        job["rag_chain"] = rag_chain
        job["status"] = "done"
        job["stage"] = "Ready"
    except Exception as exc:  # surface pipeline failures to the UI instead of a dead poll
        job["status"] = "error"
        job["error"] = str(exc)


@app.post("/api/process")
def start_process():
    data = request.get_json(force=True) or {}
    source = (data.get("source") or "").strip()
    language = (data.get("language") or "english").strip().lower()

    if not source:
        return jsonify({"error": "source is required"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "stage": "Queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "language": language,
    }

    thread = threading.Thread(
        target=run_pipeline_job, args=(job_id, source, language), daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})


@app.get("/api/status/<job_id>")
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404

    payload = {"job_id": job_id, "status": job["status"], "stage": job.get("stage")}
    if job["status"] == "done":
        payload["result"] = job["result"]
    if job["status"] == "error":
        payload["error"] = job.get("error")
    return jsonify(payload)


@app.post("/api/chat")
def chat():
    data = request.get_json(force=True) or {}
    job_id = data.get("job_id")
    question = (data.get("question") or "").strip()

    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return jsonify({"error": "This session isn't ready yet."}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    answer = ask_question(job["rag_chain"], question)
    return jsonify({"answer": answer})


@app.post("/api/upload")
def upload_file():
    """Accepts a local audio/video file upload and returns a filesystem path
    that can then be passed as `source` to /api/process."""
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    file.save(path)
    return jsonify({"path": path})


# ── Serve the built React app ───────────────────────────────────────────
# Lets one process (and, for self-hosting, one Cloudflare Tunnel) cover
# both the site and the API — no separate frontend host, no CORS to worry
# about. Run `npm run build` in frontend/ first; this serves frontend/dist.
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
