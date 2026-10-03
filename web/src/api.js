export const DECISION_SKILL = 'make_decision'

export const MODE_STATE = {
  heuristic: { label: 'heuristic, not a model', color: 'var(--sb-caution)' },
  gemini: { label: 'live model run', color: 'var(--sb-live)' },
  vertex: { label: 'live model run on Vertex AI', color: 'var(--sb-cloud)' },
}

export const EVIDENCE_STANCE = {
  decision: { label: 'for', color: 'var(--sb-live)' },
  against: { label: 'against', color: 'var(--sb-caution)' },
  context: { label: 'context', color: 'var(--sb-ink-muted)' },
}

export function apiUrl(path) {
  const base = import.meta.env.VITE_API || '/api'
  return `${base}${path}`
}

async function call(path, options = {}) {
  let response
  try {
    response = await fetch(apiUrl(path), options)
  } catch (cause) {
    const error = new Error(
      `The decision service did not answer. It runs as a separate process from this page, on ` +
        `${import.meta.env.VITE_API || 'the same host via /api'}.`,
    )
    error.kind = 'unreachable'
    throw error
  }

  if (response.status >= 500) {
    const error = new Error(
      `The decision service failed while handling ${path} (HTTP ${response.status}). Check the ` +
        `API log; this page will not retry on your behalf.`,
    )
    error.kind = 'unreachable'
    throw error
  }

  if (response.status >= 400) {
    let detail = ''
    try {
      const body = await response.json()
      detail = body.detail || ''
    } catch {
      detail = ''
    }
    const error = new Error(detail || `The service rejected ${path} (HTTP ${response.status}).`)
    error.kind = 'rejected'
    throw error
  }

  return response.json()
}

export const getHealth = () => call('/health')

export const getAudit = (limit = 8) => call(`/audit?limit=${limit}`)

export function recordOverride(runId, verdict, note) {
  const form = new FormData()
  form.append('verdict', verdict)
  form.append('note', note)
  return call(`/audit/${runId}/override`, { method: 'POST', body: form })
}

export function getOverride(runId) {
  return call(`/audit/${runId}/override`)
}

export function decide(scenario, files) {
  const form = new FormData()
  form.append('scenario', scenario)
  for (const file of files) {
    form.append('files', file, file.name)
  }
  return call('/process', { method: 'POST', body: form })
}