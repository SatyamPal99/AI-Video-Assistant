const BASE = "/api"

async function handle(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`)
  }
  return data
}

export async function startProcess(source, language) {
  const res = await fetch(`${BASE}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, language }),
  })
  return handle(res)
}

export async function getStatus(jobId) {
  const res = await fetch(`${BASE}/status/${jobId}`)
  return handle(res)
}

export async function askQuestion(jobId, question) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, question }),
  })
  return handle(res)
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form })
  return handle(res)
}
