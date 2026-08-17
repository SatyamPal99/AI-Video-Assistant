import { useState, useEffect, useRef, useCallback } from "react"
import SourceForm from "./components/SourceForm"
import Dashboard from "./components/Dashboard"
import ChatPanel from "./components/ChatPanel"
import Waveform from "./components/Waveform"
import { startProcess, getStatus } from "./api"

const POLL_INTERVAL_MS = 1500

export default function App() {
  const [phase, setPhase] = useState("idle") // idle | processing | error | ready
  const [jobId, setJobId] = useState(null)
  const [stage, setStage] = useState("")
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState("")
  const pollRef = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => stopPolling, [stopPolling])

  const handleSubmit = async ({ source, language }) => {
    setPhase("processing")
    setErrorMsg("")

    try {
      const { job_id } = await startProcess(source, language)
      setJobId(job_id)

      pollRef.current = setInterval(async () => {
        try {
          const data = await getStatus(job_id)
          setStage(data.stage || "")

          if (data.status === "done") {
            stopPolling()
            setResult(data.result)
            setPhase("ready")
          } else if (data.status === "error") {
            stopPolling()
            setErrorMsg(data.error || "Something went wrong.")
            setPhase("error")
          }
        } catch (err) {
          stopPolling()
          setErrorMsg(err.message)
          setPhase("error")
        }
      }, POLL_INTERVAL_MS)
    } catch (err) {
      setErrorMsg(err.message)
      setPhase("error")
    }
  }

  const reset = () => {
    stopPolling()
    setPhase("idle")
    setJobId(null)
    setResult(null)
    setErrorMsg("")
    setStage("")
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Waveform size="small" active={phase === "processing"} />
          <span className="brand-name">AI Video Assistant</span>
        </div>
        {phase === "ready" && (
          <button className="btn-ghost" onClick={reset}>
            New session
          </button>
        )}
      </header>

      <main className="stage">
        {phase === "idle" && <SourceForm onSubmit={handleSubmit} />}

        {phase === "processing" && (
          <div className="processing-panel">
            <Waveform size="large" active />
            <p className="stage-label">{stage || "Starting up…"}</p>
            <p className="stage-sub">This can take a few minutes for longer recordings.</p>
          </div>
        )}

        {phase === "error" && (
          <div className="error-panel">
            <p className="error-title">Processing failed</p>
            <p className="error-detail">{errorMsg}</p>
            <button className="btn-primary" onClick={reset}>
              Try again
            </button>
          </div>
        )}

        {phase === "ready" && result && (
          <>
            <Dashboard result={result} />
            <ChatPanel jobId={jobId} />
          </>
        )}
      </main>
    </div>
  )
}
