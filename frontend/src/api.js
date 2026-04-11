const BASE = '/api'

export async function startGeneration({ sourceContent, originalPrompt, llmProvider, maxRewrites }) {
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_content: sourceContent,
      original_prompt: originalPrompt || 'Podcast Episode',
      llm_provider: llmProvider,
      max_rewrites: maxRewrites,
    }),
  })
  if (!res.ok) throw new Error('Failed to start generation')
  return res.json()  // { job_id }
}

export function openProgressStream(jobId) {
  return new EventSource(`${BASE}/progress/${jobId}`)
}

export async function fetchAudio(jobId) {
  const res = await fetch(`${BASE}/audio/${jobId}`)
  if (!res.ok) throw new Error('Failed to fetch audio')
  return res.blob()
}

export async function fetchScript(jobId) {
  const res = await fetch(`${BASE}/script/${jobId}`)
  if (!res.ok) throw new Error('Failed to fetch script')
  return res.text()
}

export async function ingestUrl(url) {
  const res = await fetch(`${BASE}/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to fetch URL')
  }
  return res.json()  // { text }
}

export async function ingestFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}/ingest/file`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to parse file')
  }
  return res.json()  // { text }
}
