import { useState } from "react"

const TABS = [
  { key: "summary", label: "Summary", accent: "base" },
  { key: "action_items", label: "Action items", accent: "amber" },
  { key: "key_decisions", label: "Decisions", accent: "teal" },
  { key: "open_questions", label: "Questions", accent: "violet" },
  { key: "transcript", label: "Transcript", accent: "muted" },
]

function Content({ value }) {
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <p className="content-text">Nothing here for this recording.</p>
    }
    return (
      <ul className="content-list">
        {value.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    )
  }
  return <p className="content-text">{value}</p>
}

export default function Dashboard({ result }) {
  const [active, setActive] = useState("summary")
  const activeTab = TABS.find((t) => t.key === active)

  return (
    <section className="dashboard">
      <div className="dashboard-header">
        <p className="eyebrow">Session ready</p>
        <h2 className="session-title">{result.title}</h2>
      </div>

      <nav className="tab-row">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab-btn accent-${tab.accent} ${active === tab.key ? "active" : ""}`}
            onClick={() => setActive(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className={`tab-panel accent-${activeTab.accent}`}>
        <Content value={result[active]} />
      </div>
    </section>
  )
}
