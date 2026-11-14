// Talks to the Python server (POST /api/ask) and turns its streamed events into UI state.

export const ROUTES = {
  CORRECT: { key: 'report', label: 'From the report', why: 'At least one passage answered the question, so the web was not needed.' },
  AMBIGUOUS: { key: 'both', label: 'Report + web', why: 'Passages were only partly useful, so a web search filled the gaps.' },
  INCORRECT: { key: 'web', label: 'Web only', why: 'No passage was useful, so they were dropped and the web was searched instead.' },
}

export const GRADE_LABEL = { relevant: 'Useful', partial: 'Partly useful', irrelevant: 'Not useful' }

export const initialState = {
  status: 'idle', // idle | running | done | error
  stage: null, // search | rate | web | write | done
  question: '',
  docs: [],
  grades: null,
  action: null,
  query: null,
  web: null,
  answer: '',
  sources: [],
  latency: null,
  error: null,
}

export function reducer(state, ev) {
  switch (ev.type) {
    case 'start':
      return { ...initialState, status: 'running', stage: 'search', question: ev.question }
    case 'retrieved':
      return { ...state, docs: ev.documents, stage: 'rate' }
    case 'graded':
      return { ...state, grades: ev.grades, action: ev.action, stage: ev.action === 'CORRECT' ? 'write' : 'web' }
    case 'rewritten':
      return { ...state, query: ev.query }
    case 'web':
      return { ...state, web: ev.results, stage: 'write' }
    case 'token':
      return { ...state, answer: state.answer + ev.text, stage: 'write' }
    case 'done':
      return { ...state, status: 'done', stage: 'done', answer: ev.answer, action: ev.action, sources: ev.sources, latency: ev.latency_s }
    case 'error':
      return { ...state, status: 'error', error: ev.message, errorDetail: ev.detail }
    case 'reset':
      return initialState
    default:
      return state
  }
}

/** Stream the pipeline for one question; calls onEvent for every server event. */
export async function runPipeline(question, onEvent, signal) {
  onEvent({ type: 'start', question })
  let res
  try {
    res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (e) {
    if (e.name === 'AbortError') return
    onEvent({ type: 'error', message: 'Could not reach the server. Is `python -m uvicorn server:app` running?' })
    return
  }
  if (!res.ok || !res.body) {
    onEvent({ type: 'error', message: `The server answered with an error (${res.status}).` })
    return
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let nl
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim()
        buffer = buffer.slice(nl + 1)
        if (line) onEvent(JSON.parse(line))
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') onEvent({ type: 'error', message: 'The connection dropped while answering. Try again.' })
  }
}

/** Split an answer into text and citation markers. Models write [1], 【1】 or 【1†source】. */
export function splitCitations(raw) {
  // the model sometimes uses narrow / no-break spaces, which this font draws with no width
  const text = raw.replace(/[    ]/g, ' ')
  const parts = []
  const re = /\s?[[【](\d+)(?:†[^\]】]*)?[\]】]/g
  let last = 0
  let m
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) })
    parts.push({ cite: Number(m[1]) })
    last = re.lastIndex
  }
  if (last < text.length) parts.push({ text: text.slice(last) })
  return parts
}

export function pageOf(source) {
  const m = /p\.(\d+)/.exec(source || '')
  return m ? Number(m[1]) : null
}

export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
