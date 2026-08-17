import { useState } from "react"
import { uploadFile } from "../api"

export default function SourceForm({ onSubmit }) {
  const [mode, setMode] = useState("url") // "url" | "file"
  const [source, setSource] = useState("")
  const [fileName, setFileName] = useState("")
  const [language, setLanguage] = useState("english")
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")

  const switchMode = (next) => {
    setMode(next)
    setSource("")
    setFileName("")
    setError("")
  }

  const handleFile = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFileName(file.name)
    setUploading(true)
    setError("")
    try {
      const { path } = await uploadFile(file)
      setSource(path)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!source.trim()) {
      setError(
        mode === "url"
          ? "Paste a YouTube URL first."
          : "Choose a file first."
      )
      return
    }
    onSubmit({ source: source.trim(), language })
  }

  return (
    <form className="source-form" onSubmit={handleSubmit}>
      <p className="eyebrow">New session</p>
      <h1 className="form-title">
        Drop in a recording, get the whole meeting back.
      </h1>
      <p className="form-sub">
        Paste a YouTube link or upload a local file. We'll transcribe it,
        summarize it, and let you ask it questions afterward.
      </p>

      <div className="mode-toggle" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "url"}
          className={mode === "url" ? "mode-btn active" : "mode-btn"}
          onClick={() => switchMode("url")}
        >
          YouTube URL
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "file"}
          className={mode === "file" ? "mode-btn active" : "mode-btn"}
          onClick={() => switchMode("file")}
        >
          Local file
        </button>
      </div>

      {mode === "url" ? (
        <input
          type="text"
          className="text-input"
          placeholder="https://youtube.com/watch?v=…"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
      ) : (
        <label className="file-drop">
          <input type="file" accept="audio/*,video/*" onChange={handleFile} hidden />
          {uploading ? "Uploading…" : fileName || "Choose an audio or video file"}
        </label>
      )}

      <div className="lang-row">
        <span className="field-label">Language</span>
        <div className="lang-toggle">
          {["english", "hinglish"].map((l) => (
            <button
              type="button"
              key={l}
              className={language === l ? "lang-btn active" : "lang-btn"}
              onClick={() => setLanguage(l)}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}

      <button type="submit" className="btn-primary btn-large" disabled={uploading}>
        Process recording
      </button>
    </form>
  )
}
