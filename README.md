# 🎥 AI Video Assistant

Turn any YouTube video, meeting recording, or local audio/video file into a **searchable, chat-ready knowledge base** — automatically transcribed, summarized, and broken down into action items, key decisions, and open questions.

Give it a link or a file. Get back a title, a summary, action items, decisions, unresolved questions, and a chat interface to ask follow-up questions about the content — grounded in the transcript via Retrieval-Augmented Generation (RAG).

---

## ✨ Features

- **Two input sources** — paste a YouTube URL or upload a local audio/video file.
- **Automatic audio pipeline** — downloads/converts the source, normalizes it to mono 16kHz WAV, and chunks long recordings for reliable transcription.
- **Multilingual transcription**
  - **English** — transcribed locally with **OpenAI Whisper** (no API cost, runs offline).
  - **Hinglish** — routed to the **Sarvam AI** speech-to-text-translate API, which transcribes and translates code-mixed Hindi-English speech into English.
- **LLM-powered analysis** (via **LangChain** + **Mistral AI**)
  - Auto-generated meeting/video title
  - Map-reduce summarization for long transcripts
  - Structured extraction of **action items** (task, owner, deadline), **key decisions**, and **open questions**
- **Chat with your transcript (RAG)** — transcript is embedded with HuggingFace sentence-transformers and indexed in **ChromaDB**, so you can ask natural-language questions and get answers grounded strictly in the source content (with a graceful fallback when the answer isn't in the transcript).
- **Three ways to use it**
  - A CLI pipeline for quick local runs
  - A **Streamlit** app with a live progress UI
  - A **Flask REST API** (async job queue with polling) backing a **React + Vite** single-page frontend

---

## 🏗️ Architecture

```
                ┌─────────────────┐
 YouTube URL /  │  audio_processor │  → download / convert → chunk (10 min chunks)
 local file ───►│    (utils/)      │
                └────────┬─────────┘
                         ▼
                ┌─────────────────┐
                │   transcriber    │  Whisper (English) or Sarvam AI (Hinglish)
                │    (core/)       │
                └────────┬─────────┘
                         ▼
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
   ┌───────────┐  ┌─────────────┐  ┌─────────────┐
   │summarizer │  │  extractor   │  │ vector_store │
   │(title +   │  │ (action     │  │  + rag_engine│
   │ summary)  │  │  items /    │  │  (ChromaDB + │
   │           │  │  decisions /│  │  HuggingFace │
   │           │  │  questions) │  │  embeddings) │
   └───────────┘  └─────────────┘  └──────┬──────┘
                                            ▼
                                    Chat / Q&A over
                                     the transcript
```

Every interface (CLI, Streamlit, Flask API) wraps the **same core pipeline** (`utils/audio_processor.py` → `core/transcriber.py` → `core/summarizer.py` / `core/extractor.py` → `core/rag_engine.py`), so the logic is written once and reused everywhere.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Audio/video acquisition | `yt-dlp`, `pydub`, `ffmpeg-python` |
| Speech-to-text | `openai-whisper` (local, English), Sarvam AI API (Hinglish) |
| LLM orchestration | `LangChain`, `langchain-mistralai` (Mistral `mistral-small-latest`) |
| RAG / vector search | `ChromaDB`, `sentence-transformers` (`all-MiniLM-L6-v2`), `langchain-huggingface` |
| Backend API | `Flask`, `Flask-CORS` |
| Frontend | `React 18`, `Vite` |
| Interactive UI (alt.) | `Streamlit` |
| Export | `reportlab`, `fpdf2` |

---

## 📁 Project Structure

```
AI-Video-Assistant/
├── core/
│   ├── transcriber.py     # Whisper / Sarvam AI transcription
│   ├── summarizer.py      # Title + map-reduce summary generation
│   ├── extractor.py       # Action items / decisions / open questions
│   ├── rag_engine.py      # RAG chain for chatting with the transcript
│   └── vector_store.py    # ChromaDB + HuggingFace embeddings
├── utils/
│   └── audio_processor.py # Download, convert, and chunk audio
├── frontend/               # React + Vite single-page app
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/     # SourceForm, Dashboard, ChatPanel, Waveform
├── app.py                  # Flask REST API (async jobs + polling)
├── app_streamlit.py        # Streamlit UI
├── main.py                 # CLI entry point
├── test.py                 # Sample pipeline run
└── requirement.txt
```

---

## 🚀 Getting Started

### Prerequisites

- Python ≥ 3.10
- Node.js ≥ 18 (only if you want the React frontend)
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your `PATH`
- A [Mistral AI](https://mistral.ai) API key (required)
- A [Sarvam AI](https://www.sarvam.ai) API key (optional — only needed for Hinglish transcription)

### 1. Clone and install

```bash
git clone https://github.com/SatyamPal99/AI-Video-Assistant.git
cd AI-Video-Assistant
pip install -r requirement.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
MISTRAL_API_KEY=your_mistral_api_key
SARVAM_API_KEY=your_sarvam_api_key        # optional, only for Hinglish
WHISPER_MODEL=small                       # optional, defaults to "small"
SARVAM_STT_MODEL=saaras:v2.5              # optional
```

### 3. Run it — pick an interface

**CLI**
```bash
python main.py
# Enter a YouTube URL or local file path when prompted
```

**Streamlit UI**
```bash
streamlit run app_streamlit.py
```

**Flask API + React frontend**
```bash
# Terminal 1 — backend
python app.py            # serves the REST API on http://localhost:5000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev               # serves the SPA on http://localhost:5173
```

---

## 🔌 API Reference (Flask backend)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/process` | Starts an async pipeline job for a given `source` (URL or path) and `language`. Returns a `job_id`. |
| `GET` | `/api/status/<job_id>` | Polls job status/stage; returns the full result once `status` is `done`. |
| `POST` | `/api/chat` | Asks a question against a completed job's transcript via the RAG chain. |
| `POST` | `/api/upload` | Uploads a local audio/video file and returns a server-side path to pass to `/api/process`. |

---

## 🗺️ Roadmap

- [ ] Persist jobs to a database (currently in-memory, single-process)
- [ ] Export summaries/action items to PDF (`reportlab`/`fpdf2` are already wired in as dependencies)
- [ ] Support additional languages beyond English/Hinglish
- [ ] Speaker diarization

---

## 📄 License

No license specified yet — add one (e.g. MIT) if you plan to accept external contributions.
