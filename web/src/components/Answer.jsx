import { motion } from 'motion/react'
import { ExternalLink, FileText } from 'lucide-react'
import { ROUTES, hostOf, pageOf, splitCitations } from '../lib/pipeline'

const WAITING = {
  search: 'Searching the report…',
  rate: 'Rating the passages…',
  web: 'Searching the web…',
  write: 'Writing the answer…',
}

function Cite({ n, tone }) {
  return (
    <sup className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-0.5 items-center justify-center rounded-md px-1 text-[11px] font-bold text-white"
      style={{ background: tone }}>
      {n}
    </sup>
  )
}

export default function Answer({ state }) {
  const { status, stage, question, answer, sources, action, query } = state
  const tone = action ? `rgb(var(--${ROUTES[action].key}))` : 'rgb(var(--fg))'
  const writing = stage === 'write' && answer
  const parts = splitCitations(answer)

  return (
    <section className="panel p-6">
      {status === 'idle' ? (
        <div className="py-6">
          <h2 className="text-[15px] font-bold">Answer</h2>
          <p className="mt-1 max-w-[52ch] text-[14px] text-muted">
            Ask something and watch the route map above: the question travels down the line, the LLM rates what it
            found, and the switch sends it to the report, the web, or both.
          </p>
        </div>
      ) : (
        <>
          <p className="text-[13.5px] font-semibold text-muted">Answer to</p>
          <h2 className="mb-4 text-[19px] font-bold leading-snug">{question}</h2>

          {!answer && status === 'running' && (
            <div aria-live="polite">
              <p className="mb-3 text-[14px] font-semibold text-muted">{WAITING[stage] || 'Working…'}</p>
              <div className="skeleton mb-2 h-4 w-full" />
              <div className="skeleton mb-2 h-4 w-11/12" />
              <div className="skeleton h-4 w-2/3" />
            </div>
          )}

          {answer && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="max-w-[62ch] text-[19px] leading-[1.6] text-fg"
              aria-live="polite"
            >
              {parts.map((p, i) => (p.cite ? <Cite key={i} n={p.cite} tone={tone} /> : <span key={i}>{p.text}</span>))}
              {writing && <span className="ml-0.5 inline-block h-[1.05em] w-[0.5em] translate-y-[3px] animate-blink bg-fg" />}
            </motion.p>
          )}

          {status === 'done' && sources.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mt-6">
              <h3 className="mb-2 text-[13.5px] font-bold text-muted">Sources</h3>
              <ol className="divide-y divide-line border-y border-line">
                {sources.map((s, i) => {
                  const web = s.kind === 'web'
                  const page = pageOf(s.source)
                  return (
                    <li key={i} className="flex items-center gap-3 py-2.5 text-[14px]">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[12px] font-bold text-white"
                        style={{ background: tone }}>
                        {i + 1}
                      </span>
                      {web ? (
                        <a href={s.source} target="_blank" rel="noopener noreferrer"
                          className="group flex min-w-0 items-center gap-1.5 font-semibold text-web hover:underline">
                          <span className="truncate">{hostOf(s.source)}</span>
                          <ExternalLink size={14} className="shrink-0 opacity-60 group-hover:opacity-100" />
                        </a>
                      ) : (
                        <span className="flex items-center gap-1.5 font-semibold">
                          <FileText size={15} className="text-muted" />
                          The report{page ? `, page ${page}` : ''}
                        </span>
                      )}
                      <span className="ml-auto shrink-0 text-[12.5px] text-faint">{web ? 'Web' : 'Report'}</span>
                    </li>
                  )
                })}
              </ol>
              {query && (
                <p className="mt-3 text-[13px] text-muted">
                  Web search query, rewritten by the LLM: <span className="font-semibold text-fg">“{query}”</span>
                </p>
              )}
            </motion.div>
          )}
        </>
      )}
    </section>
  )
}
