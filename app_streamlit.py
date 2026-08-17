"""
Streamlit UI for the AI Video Assistant pipeline.

Drop this file next to main.py (same level as core/ and utils/) and run:
    streamlit run streamlit_app.py

run_pipeline() below is unchanged from your CLI version — everything else
is UI. Your existing print() calls (here and inside audio_processor /
transcriber) are captured, tee'd to the real terminal, and used to drive a
real progress bar by matching known milestone lines from your pipeline.
"""

import os
import re
import sys
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUGGESTED_QUESTIONS = [
    "What were the key decisions?",
    "Summarize the risks discussed",
    "What's still unresolved?",
]


# ============================================================
# Pipeline — unchanged from your CLI version
# ============================================================
def run_pipeline(source: str, language: str = "english") -> dict:
    print("starting AI Video Assistant")

    chunks = process_input(source)

    transcript = transcribe_all(chunks, language)
    print(f"raw transcription (first 300 characters ) {transcript[:300]}")

    title = generate_title(transcript)
    summary = summarize(transcript)
    action_item = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)
    rag_chain = build_rag_chain(transcript)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
        "processed_at": datetime.now().strftime("%b %d, %Y — %I:%M %p"),
        "language": language,
    }


# ============================================================
# Page setup + styling
# ============================================================
st.set_page_config(page_title="AI Video Assistant", page_icon="🎙️", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {
        background: #0c0f14;
        background-image:
            radial-gradient(ellipse 900px 500px at 15% -10%, rgba(79,227,201,0.06), transparent 60%),
            radial-gradient(ellipse 700px 500px at 100% 0%, rgba(177,144,255,0.05), transparent 55%);
    }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.01em; }
    .brand-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .brand-row span.dot { color: #4fe3c9; font-size: 20px; }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #4fe3c9 !important;
        border-bottom-color: #4fe3c9 !important;
    }
    button[kind="primary"] {
        background-color: #4fe3c9 !important;
        color: #04211c !important;
        border: none !important;
        font-weight: 600 !important;
    }
    div[data-testid="stStatusWidget"], div[data-testid="stExpander"] {
        border-left: 2px solid #4fe3c9 !important;
    }
    div[data-testid="stMetricValue"] { color: #4fe3c9 !important; }
    code, pre, .stCodeBlock, textarea {
        font-family: 'IBM Plex Mono', monospace !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Progress heuristics — maps known lines from your pipeline's own
# print() statements to a rough (fraction, label). Approximate by
# nature: extraction/summary steps don't print anything themselves,
# so progress holds steady between "raw transcription" and
# "Building vector Store" — that's expected, not stuck.
# ============================================================
_PROGRESS_RULES = [
    (re.compile(r"starting AI Video Assistant", re.I), lambda m: (0.03, "Starting up")),
    (re.compile(r"Downloading audio", re.I), lambda m: (0.06, "Downloading audio")),
    (re.compile(r"\[download\]\s+([\d.]+)%"),
     lambda m: (0.06 + min(float(m.group(1)), 100) / 100 * 0.16,
                f"Downloading audio — {float(m.group(1)):.0f}%")),
    (re.compile(r"Chunking audio", re.I), lambda m: (0.24, "Chunking audio")),
    (re.compile(r"chunk\(s\) created", re.I), lambda m: (0.27, "Audio ready")),
    (re.compile(r"Loading Whisper model", re.I), lambda m: (0.29, "Loading transcription model")),
    (re.compile(r"Whisper model loaded", re.I), lambda m: (0.31, "Transcribing audio")),
    (re.compile(r"Transcribing chunk (\d+)/(\d+)"),
     lambda m: (0.31 + (int(m.group(1)) - 1) / max(int(m.group(2)), 1) * 0.45,
                f"Transcribing audio — chunk {m.group(1)}/{m.group(2)}")),
    (re.compile(r"Transcription complete", re.I), lambda m: (0.78, "Transcript ready")),
    (re.compile(r"raw transcription", re.I), lambda m: (0.82, "Writing summary & extracting highlights")),
    (re.compile(r"Building vector Store", re.I), lambda m: (0.92, "Indexing transcript for chat")),
]


def _parse_progress(line: str, current: float):
    best = None
    for pattern, resolver in _PROGRESS_RULES:
        match = pattern.search(line)
        if match:
            frac, label = resolver(match)
            if frac > current:
                best = (frac, label)
    return best


class LiveLog:
    """Tees print() output into the UI (log expander + stage label +
    progress bar) while still writing to the real terminal underneath.

    Libraries like yt-dlp probe extra attributes on sys.stdout (.buffer,
    .encoding, .isatty(), .fileno()) to decide how to render progress bars.
    __getattr__ delegates anything not explicitly implemented back to the
    real stdout, so this stays a fully compatible stand-in rather than a
    stripped-down stub that breaks those checks.
    """

    def __init__(self, log_placeholder, stage_placeholder, progress_placeholder, real_stdout, max_lines=40):
        self.log_placeholder = log_placeholder
        self.stage_placeholder = stage_placeholder
        self.progress_placeholder = progress_placeholder
        self.real_stdout = real_stdout
        self.text_buffer = ""
        self.max_lines = max_lines
        self.progress = 0.0

    def write(self, s):
        try:
            self.real_stdout.write(s)
        except Exception:
            pass
        if not s:
            return 0

        self.text_buffer += s.replace("\r", "\n")
        if s.strip():
            lines = self.text_buffer.strip("\n").split("\n")
            self.log_placeholder.code("\n".join(lines[-self.max_lines:]))

            match = _parse_progress(s, self.progress)
            if match:
                self.progress, label = match
                self.stage_placeholder.markdown(f"**{label}**")
                self.progress_placeholder.progress(min(self.progress, 0.97))
        return len(s)

    def flush(self):
        try:
            self.real_stdout.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self.real_stdout, name)


# ============================================================
# Small helpers
# ============================================================
def word_count(text: str) -> int:
    return len(text.split())


def reading_minutes(text: str, wpm: int = 200) -> int:
    return max(1, round(word_count(text) / wpm))


def count_items(value) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        return len([line for line in value.split("\n") if line.strip()])
    return 0


def render_list_or_text(value, empty_msg="Nothing here for this recording."):
    if isinstance(value, list):
        if not value:
            st.caption(empty_msg)
            return
        for item in value:
            st.markdown(f"- {item}")
    else:
        st.write(value or empty_msg)


def build_notes_markdown(result: dict) -> str:
    def fmt(value):
        if isinstance(value, list):
            return "\n".join(f"- {v}" for v in value) if value else "_None noted._"
        return value or "_None noted._"

    return f"""# {result['title']}
_Processed {result.get('processed_at', '')} · Language: {result.get('language', '')}_

## Summary
{result['summary']}

## Action Items
{fmt(result['action_items'])}

## Key Decisions
{fmt(result['key_decisions'])}

## Open Questions
{fmt(result['open_questions'])}

## Full Transcript
{result['transcript']}
"""


def ask_and_render(question: str, rag_chain) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = ask_question(rag_chain, question)
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# ============================================================
# Session state
# ============================================================
if "phase" not in st.session_state:
    st.session_state.phase = "idle"  # idle | ready
if "result" not in st.session_state:
    st.session_state.result = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def reset_session():
    st.session_state.phase = "idle"
    st.session_state.result = None
    st.session_state.messages = []


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("### 🎙️ AI Video Assistant")
    st.caption("Turn a recording into notes you can talk to.")
    st.divider()

    if st.session_state.phase == "idle":
        st.markdown("**How it works**")
        st.markdown("1. Paste a link or upload a file")
        st.markdown("2. It's transcribed and analyzed")
        st.markdown("3. Ask it anything")
    else:
        result = st.session_state.result
        st.markdown(f"**{result['title']}**")
        st.caption(f"{result.get('processed_at', '')} · {result.get('language', '').capitalize()}")
        st.metric("Transcript length", f"{word_count(result['transcript']):,} words")
        st.caption(f"≈ {reading_minutes(result['transcript'])} min read")
        st.divider()
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        if st.button("🔄 New session", use_container_width=True, type="primary"):
            reset_session()
            st.rerun()

    st.divider()
    st.caption("Runs locally — nothing leaves your machine.")


# ============================================================
# Header
# ============================================================
st.markdown(
    '<div class="brand-row"><span class="dot">●</span>'
    "<h2 style='margin:0;'>AI Video Assistant</h2></div>",
    unsafe_allow_html=True,
)
st.divider()


# ============================================================
# Idle phase — input form
# ============================================================
if st.session_state.phase == "idle":
    st.markdown("##### Drop in a recording, get the whole meeting back.")

    mode = st.radio("Source", ["YouTube URL", "Local file"], horizontal=True, label_visibility="collapsed")

    source = None
    if mode == "YouTube URL":
        source = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=…")
    else:
        uploaded = st.file_uploader("Upload audio/video", type=None)
        if uploaded is not None:
            save_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{uploaded.name}")
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            source = save_path
            st.caption(f"Saved: {uploaded.name}")

    language = st.radio("Language", ["english", "hinglish"], horizontal=True)

    process_clicked = st.button("Process recording", type="primary", use_container_width=True)

    if process_clicked:
        if not source:
            st.error(
                "Paste a YouTube URL first."
                if mode == "YouTube URL"
                else "Choose a file first."
            )
        else:
            with st.status("Processing your recording…", expanded=True) as status:
                stage_placeholder = st.empty()
                progress_placeholder = st.empty()
                stage_placeholder.markdown("**Starting up**")
                progress_placeholder.progress(0.0)

                with st.expander("Show detailed log", expanded=False):
                    log_placeholder = st.empty()

                old_stdout = sys.stdout
                sys.stdout = LiveLog(log_placeholder, stage_placeholder, progress_placeholder, old_stdout)
                try:
                    result = run_pipeline(source, language)
                    sys.stdout = old_stdout
                    progress_placeholder.progress(1.0)
                    stage_placeholder.markdown("**Done**")
                    status.update(label="Done", state="complete", expanded=False)
                    st.session_state.result = result
                    st.session_state.phase = "ready"
                    st.toast("Session ready.", icon="✅")
                    st.rerun()
                except Exception as exc:
                    sys.stdout = old_stdout
                    status.update(label="Processing failed", state="error", expanded=True)
                    st.error(str(exc))
                finally:
                    sys.stdout = old_stdout


# ============================================================
# Ready phase — dashboard + chat
# ============================================================
else:
    result = st.session_state.result
    st.markdown(f"## {result['title']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Words", f"{word_count(result['transcript']):,}")
    m2.metric("Read time", f"{reading_minutes(result['transcript'])} min")
    m3.metric("Action items", count_items(result["action_items"]))
    m4.metric("Open questions", count_items(result["open_questions"]))

    e1, e2 = st.columns(2)
    with e1:
        st.download_button(
            "⬇️ Meeting notes (.md)",
            build_notes_markdown(result),
            file_name="meeting_notes.md",
            use_container_width=True,
        )
    with e2:
        st.download_button(
            "⬇️ Transcript (.txt)",
            result["transcript"],
            file_name="transcript.txt",
            use_container_width=True,
        )

    st.write("")
    tabs = st.tabs(["📋 Summary", "✅ Action Items", "🔑 Key Decisions", "❓ Open Questions", "📝 Transcript"])

    with tabs[0]:
        with st.container(border=True):
            st.write(result["summary"])

    with tabs[1]:
        with st.container(border=True):
            render_list_or_text(result["action_items"])

    with tabs[2]:
        with st.container(border=True):
            render_list_or_text(result["key_decisions"])

    with tabs[3]:
        with st.container(border=True):
            render_list_or_text(result["open_questions"])

    with tabs[4]:
        search = st.text_input("Search transcript", placeholder="Search for a word or phrase…")
        transcript = result["transcript"]
        if search:
            matches = [s.strip() for s in transcript.split(". ") if search.lower() in s.lower()]
            st.caption(f"{len(matches)} match(es)")
            with st.container(border=True):
                for snippet in matches[:20]:
                    st.markdown(f"- …{snippet}…")
        with st.container(border=True):
            st.text_area("Full transcript", transcript, height=280, label_visibility="collapsed")

    st.divider()
    st.markdown("##### 💬 Chat with your meeting")

    with st.container(height=380, border=True):
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if not st.session_state.messages:
            st.caption("Try asking:")
            cols = st.columns(len(SUGGESTED_QUESTIONS))
            for col, q in zip(cols, SUGGESTED_QUESTIONS):
                if col.button(q, use_container_width=True, key=f"suggest_{q}"):
                    ask_and_render(q, result["rag_chain"])

    question = st.chat_input("Ask a question about this recording…")
    if question:
        ask_and_render(question, result["rag_chain"])