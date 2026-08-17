export default function Waveform({ size = "small", active = false }) {
  const bars = size === "large" ? 24 : 5

  return (
    <div className={`waveform waveform-${size} ${active ? "is-active" : ""}`}>
      {Array.from({ length: bars }).map((_, i) => (
        <span key={i} style={{ animationDelay: `${(i % 7) * 0.09}s` }} />
      ))}
    </div>
  )
}
