import { AnimatePresence, motion } from 'motion/react'
import { GRADE_LABEL, pageOf } from '../lib/pipeline'

const GRADE_TONE = {
  relevant: { text: 'text-report', bar: 'bg-report', chip: 'bg-report/10 text-report ring-report/30' },
  partial: { text: 'text-both', bar: 'bg-both', chip: 'bg-both/10 text-both ring-both/30' },
  irrelevant: { text: 'text-faint', bar: 'bg-line-strong', chip: 'bg-sunken text-muted ring-line' },
}

function clean(text) {
  return (text || '').replace(/(^|\n)[#>\s]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function Card({ doc, grade, index }) {
  const tone = GRADE_TONE[grade] || null
  const page = pageOf(doc.source)
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: grade === 'irrelevant' ? 0.6 : 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.07, ease: [0.2, 0.9, 0.3, 1] }}
      className="relative overflow-hidden rounded-control border border-line bg-panel p-3.5 pl-4"
    >
      <span className={`absolute inset-y-0 left-0 w-1 transition-colors duration-500 ${tone ? tone.bar : 'bg-line'}`} />
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[13px]">
        <span className="font-semibold text-muted">
          {page ? `Page ${page}` : 'Passage'}
          <span className="num ml-2 font-normal text-faint">match {Number(doc.score).toFixed(2)}</span>
        </span>
        <AnimatePresence>
          {grade && (
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 28, delay: index * 0.08 }}
              className={`rounded-full px-2.5 py-0.5 text-[12px] font-bold ring-1 ring-inset ${tone.chip}`}
            >
              {GRADE_LABEL[grade]}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <p className="clamp-4 text-[13.5px] leading-[1.5] text-fg/90">{clean(doc.content)}</p>
    </motion.li>
  )
}

export default function Passages({ state }) {
  const { status, docs, grades, stage } = state
  return (
    <section className="panel p-5">
      <h2 className="text-[15px] font-bold">Passages from the report</h2>
      <p className="mb-4 mt-0.5 text-[13.5px] text-muted">
        {grades
          ? 'Each passage as the LLM rated it. Only useful ones are trusted.'
          : stage === 'rate'
            ? 'The LLM is rating each passage…'
            : 'The 4 passages closest to the question, and how the LLM rates them.'}
      </p>
      {status === 'idle' ? (
        <div className="rounded-control border border-dashed border-line-strong px-4 py-8 text-center text-[13.5px] text-muted">
          Passages show up here once you ask.
        </div>
      ) : docs.length === 0 && status === 'running' ? (
        <ul className="space-y-2.5">
          {[0, 1, 2, 3].map((i) => (
            <li key={i} className="rounded-control border border-line p-3.5">
              <div className="skeleton mb-2.5 h-3 w-24" />
              <div className="skeleton mb-1.5 h-3 w-full" />
              <div className="skeleton h-3 w-4/5" />
            </li>
          ))}
        </ul>
      ) : (
        <ul className="space-y-2.5">
          {docs.map((d, i) => (
            <Card key={d.id || i} doc={d} grade={grades?.[i]} index={i} />
          ))}
        </ul>
      )}
    </section>
  )
}
