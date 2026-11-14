import { useState } from 'react'
import { motion } from 'motion/react'
import { GitCompare } from 'lucide-react'
import { ROUTES, splitCitations } from '../lib/pipeline'

function Cite({ n, tone }) {
  return (
    <sup className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-0.5 items-center justify-center rounded-md px-1 text-[11px] font-bold text-white"
      style={{ background: tone }}>
      {n}
    </sup>
  )
}

function Column({ label, tone, answer, seconds, children }) {
  return (
    <div>
      <p className="mb-2 text-[13.5px] font-bold" style={{ color: tone }}>{label}</p>
      <p className="text-[16px] leading-[1.6] text-fg">
        {splitCitations(answer).map((p, i) => (p.cite ? <Cite key={i} n={p.cite} tone={tone} /> : <span key={i}>{p.text}</span>))}
      </p>
      <p className="mt-3 text-[13px] text-muted">Took {seconds} s</p>
      {children}
    </div>
  )
}

// keyed on the question in the parent, so every new question starts with a fresh comparison
function CompareBody({ state }) {
  const [phase, setPhase] = useState('idle') // idle | loading | done | error
  const [plain, setPlain] = useState(null)
  const [error, setError] = useState('')

  const run = async () => {
    setPhase('loading')
    try {
      const res = await fetch('/api/baseline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: state.question }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.message || `The server answered with an error (${res.status}).`)
      setPlain(data)
      setPhase('done')
    } catch (e) {
      setError(e instanceof TypeError ? 'Could not reach the server.' : e.message)
      setPhase('error')
    }
  }

  const route = ROUTES[state.action]
  const cragTone = `rgb(var(--${route.key}))`

  return (
    <>
      {(phase === 'idle' || phase === 'error') && (
        <button onClick={run}
          className="flex items-center gap-2 rounded-control border border-line bg-panel px-4 py-2.5 text-[14.5px] font-bold text-fg transition hover:border-line-strong">
          <GitCompare size={16} />
          Compare with plain RAG
        </button>
      )}
      {phase === 'error' && <p role="alert" className="mt-3 text-[14px] text-danger">{error}</p>}

      {phase === 'loading' && (
        <div className="panel p-6" aria-live="polite">
          <p className="mb-3 text-[14px] font-semibold text-muted">Plain RAG answers from the top 4 passages, no checking, no web search…</p>
          <div className="skeleton mb-2 h-4 w-full" />
          <div className="skeleton mb-2 h-4 w-11/12" />
          <div className="skeleton h-4 w-2/3" />
        </div>
      )}

      {phase === 'done' && (
        <motion.section initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="panel grid gap-6 p-6 lg:grid-cols-2">
          <Column label="Plain RAG" tone="rgb(var(--faint))" answer={plain.answer} seconds={plain.latency_s} />
          <Column label="CRAG" tone={cragTone} answer={state.answer} seconds={state.latency}>
            <p className="mt-1 text-[13px] font-semibold" style={{ color: cragTone }}>{route.label}</p>
          </Column>
        </motion.section>
      )}
    </>
  )
}

export default function Compare({ state }) {
  if (state.status !== 'done' || !ROUTES[state.action]) return null
  return (
    <div className="mt-5">
      <CompareBody key={state.question} state={state} />
    </div>
  )
}
