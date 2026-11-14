import { useEffect, useReducer, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { AlertTriangle, ArrowUp, Moon, Sun } from 'lucide-react'
import Track from './components/Track'
import Answer from './components/Answer'
import Passages from './components/Passages'
import Compare from './components/Compare'
import { ROUTES, initialState, reducer, runPipeline } from './lib/pipeline'

const FALLBACK_META = {
  dataset: 'AI and the Future of Teaching and Learning',
  dataset_detail: 'US Department of Education, 2023, 71 pages',
  samples: [
    { label: 'What is algorithmic bias?', question: 'How does the report define algorithmic bias?', route: 'CORRECT' },
    { label: 'Who released ChatGPT, and when?', question: 'Which company released ChatGPT, and when was it first released to the public?', route: 'AMBIGUOUS' },
    { label: 'Who painted the Mona Lisa?', question: 'Who painted the Mona Lisa?', route: 'INCORRECT' },
  ],
}

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
      <rect width="32" height="32" rx="9" className="fill-fg" />
      <path d="M6 16h8M14 16c4 0 4-7 8-7h4M14 16h12M14 16c4 0 4 7 8 7h4" fill="none" className="stroke-canvas"
        strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="14" cy="16" r="3" style={{ fill: 'rgb(var(--report))' }} />
    </svg>
  )
}

function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'light')
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('crag-theme', theme) } catch { /* private mode: ignore */ }
  }, [theme])
  const dark = theme === 'dark'
  return (
    <button onClick={() => setTheme(dark ? 'light' : 'dark')} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      className="flex h-9 w-9 items-center justify-center rounded-control border border-line bg-panel text-muted transition hover:border-line-strong hover:text-fg">
      {dark ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  )
}

function RouteSummary({ state }) {
  const { status, action, latency } = state
  if (status === 'error') return null
  if (!action) {
    return (
      <p className="text-[14px] text-muted">
        {status === 'idle'
          ? 'Three possible routes. The rating step decides which one each question takes.'
          : 'Following the question down the line…'}
      </p>
    )
  }
  const r = ROUTES[action]
  return (
    <motion.p key={action} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="text-[14.5px]">
      <span className="font-extrabold" style={{ color: `rgb(var(--${r.key}))` }}>{r.label}.</span>{' '}
      <span className="text-fg">{r.why}</span>
      {status === 'done' && latency != null && <span className="text-muted"> Took {latency} s.</span>}
    </motion.p>
  )
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [question, setQuestion] = useState('')
  const [meta, setMeta] = useState(FALLBACK_META)
  const abortRef = useRef(null)
  const inputRef = useRef(null)
  const running = state.status === 'running'

  useEffect(() => {
    fetch('/api/meta').then((r) => (r.ok ? r.json() : null)).then((m) => m && setMeta(m)).catch(() => {})
    return () => abortRef.current?.abort()
  }, [])

  const ask = (q) => {
    const text = (q ?? question).trim()
    if (!text || running) return
    setQuestion(text)
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    runPipeline(text, dispatch, ctrl.signal)
  }

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-[1180px] items-center justify-between px-4 pt-5 sm:px-6">
        <div className="flex items-center gap-3">
          <Logo />
          <div className="leading-tight">
            <div className="text-[16px] font-extrabold tracking-[-0.01em]">Corrective RAG</div>
            <div className="text-[12.5px] text-muted">Prompt Engineering mini project</div>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <main className="mx-auto max-w-[1180px] px-4 pb-16 sm:px-6">
        {/* hero: the question */}
        <section className="pb-6 pt-10 sm:pt-14">
          <h1 className="max-w-[20ch] text-[34px] font-extrabold leading-[1.08] tracking-[-0.025em] sm:text-[46px]">
            Ask the report. Watch it check its own sources.
          </h1>
          <p className="mt-3 max-w-[64ch] text-[15.5px] text-muted">
            Questions are answered from <span className="font-semibold text-fg">{meta.dataset}</span> ({meta.dataset_detail}).
            Before answering, an LLM rates every passage it found. Weak passages send the question to the web instead.
          </p>

          <form
            onSubmit={(e) => { e.preventDefault(); ask() }}
            className="mt-7 flex items-center gap-2 rounded-[14px] border border-line-strong bg-panel p-2 pl-4 transition focus-within:border-fg"
            style={{ boxShadow: 'var(--shadow)' }}
          >
            <input
              ref={inputRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about AI in teaching and learning, or anything else"
              aria-label="Your question"
              maxLength={500}
              className="min-w-0 flex-1 bg-transparent py-2 text-[17px] text-fg outline-none placeholder:text-faint"
            />
            <button
              type="submit"
              disabled={running || !question.trim()}
              className="flex h-11 shrink-0 items-center gap-2 rounded-control bg-fg px-4 text-[15px] font-bold text-canvas transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {running ? 'Working…' : 'Ask'}
              {!running && <ArrowUp size={17} strokeWidth={2.5} />}
            </button>
          </form>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="mr-1 text-[13.5px] text-muted">Try one per route:</span>
            {meta.samples.map((s) => {
              const r = ROUTES[s.route]
              return (
                <button
                  key={s.question}
                  type="button"
                  disabled={running}
                  onClick={() => ask(s.question)}
                  title={`${s.question} (expected route: ${r.label})`}
                  className="group flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5 text-[13.5px] font-semibold text-fg transition hover:border-line-strong disabled:opacity-50"
                >
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: `rgb(var(--${r.key}))` }} />
                  {s.label}
                </button>
              )
            })}
          </div>
        </section>

        {/* the route map */}
        <section className="panel px-4 pb-5 pt-3 sm:px-6">
          <Track state={state} />
          <div className="mt-1 border-t border-line pt-4">
            <RouteSummary state={state} />
          </div>
        </section>

        <AnimatePresence>
          {state.status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              role="alert"
              className="mt-4 flex items-start gap-3 rounded-panel border border-danger/40 bg-danger/5 p-4 text-[14.5px]"
            >
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-danger" />
              <div>
                <p className="font-semibold">{state.error}</p>
                {state.errorDetail && <p className="mt-1 break-all text-[12.5px] text-muted">{state.errorDetail}</p>}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-5 grid gap-5 lg:grid-cols-[3fr_2fr]">
          <Answer state={state} />
          <Passages state={state} />
        </div>

        <Compare state={state} />
      </main>
    </div>
  )
}
