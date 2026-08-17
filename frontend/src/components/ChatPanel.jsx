import { useState, useRef, useEffect } from "react"
import { askQuestion } from "../api"
import Waveform from "./Waveform"

export default function ChatPanel({ jobId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [thinking, setThinking] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, thinking])

  const send = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || thinking) return

    setMessages((m) => [...m, { role: "user", text: question }])
    setInput("")
    setThinking(true)
    try {
      const { answer } = await askQuestion(jobId, question)
      setMessages((m) => [...m, { role: "assistant", text: answer }])
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Couldn't get an answer: ${err.message}` },
      ])
    } finally {
      setThinking(false)
    }
  }

  return (
    <section className="chat-panel">
      <p className="eyebrow">Ask the recording</p>
      <div className="chat-log">
        {messages.length === 0 && (
          <p className="chat-empty">
            Ask anything about this recording — "what did we decide about the budget?"
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            <span className="chat-role">{m.role === "user" ? "You" : "Assistant"}</span>
            <p>{m.text}</p>
          </div>
        ))}
        {thinking && (
          <div className="chat-bubble assistant thinking">
            <Waveform size="small" active />
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form className="chat-input-row" onSubmit={send}>
        <input
          className="text-input"
          placeholder="Type a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary" type="submit" disabled={thinking}>
          Send
        </button>
      </form>
    </section>
  )
}
