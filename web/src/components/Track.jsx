import { motion, useReducedMotion } from 'motion/react'
import { ROUTES } from '../lib/pipeline'

// Transit-map view of the CRAG pipeline. The main line runs left to right; at the
// "Rate passages" switch it splits into three branches, and the one the grader picks lights up.
//
// viewBox geometry (1000 x 250): main line at y=125, branches at y=45 / 125 / 205.
const Y = 125
const X = { question: 36, search: 200, rate: 450, web: 700, answer: 950 }

const BRANCHES = {
  CORRECT: {
    a: 'M450 125 C505 125 505 45 560 45 H700',
    b: 'M700 45 H840 C895 45 895 125 950 125',
    labelY: 33,
    stop: null,
  },
  AMBIGUOUS: { a: 'M450 125 H700', b: 'M700 125 H950', labelY: 113, stop: 125 },
  INCORRECT: {
    a: 'M450 125 C505 125 505 205 560 205 H700',
    b: 'M700 205 H840 C895 205 895 125 950 125',
    labelY: 193,
    stop: 205,
  },
}

const color = (key) => `rgb(var(--${key}))`

// "1 useful, 3 not" -- only non-zero counts, so the label stays short
function countText({ useful, partly, not }) {
  const parts = []
  if (useful) parts.push(`${useful} useful`)
  if (partly) parts.push(`${partly} partly`)
  if (not) parts.push(`${not} ${parts.length ? 'not' : 'not useful'}`)
  return parts.join(', ')
}

function Segment({ d, lit, tone, delay = 0, dim = false, reduce }) {
  return (
    <>
      <path d={d} fill="none" stroke="rgb(var(--line))" strokeWidth="6" strokeLinecap="round"
        style={{ opacity: dim ? 0.45 : 1, transition: 'opacity .5s' }} />
      {lit && (
        <motion.path
          d={d}
          fill="none"
          stroke={tone}
          strokeWidth="6"
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.65, ease: [0.2, 0.9, 0.3, 1], delay }}
        />
      )}
    </>
  )
}

function Station({ x, y, state, tone, reduce }) {
  // state: idle | active | done
  const ring = tone || 'rgb(var(--fg))'
  return (
    <g>
      {state === 'active' && !reduce && (
        <motion.circle
          cx={x}
          cy={y}
          fill="none"
          stroke={ring}
          strokeWidth="2"
          initial={{ r: 10, opacity: 0.7 }}
          animate={{ r: 26, opacity: 0 }}
          transition={{ duration: 1.3, repeat: Infinity, ease: 'easeOut' }}
        />
      )}
      <motion.circle
        cx={x}
        cy={y}
        r="10"
        strokeWidth="4"
        initial={false}
        animate={{
          fill: state === 'done' ? ring : 'rgb(var(--panel))',
          stroke: state === 'idle' ? 'rgb(var(--line-strong))' : ring,
          scale: state === 'active' ? 1.12 : 1,
        }}
        transition={{ duration: 0.3 }}
        style={{ transformOrigin: `${x}px ${y}px` }}
      />
    </g>
  )
}

function Label({ x, y, name, detail, anchor = 'middle', active }) {
  return (
    <g style={{ transition: 'opacity .3s' }}>
      <text x={x} y={y} textAnchor={anchor} className="fill-fg" style={{ fontSize: 16, fontWeight: 700 }}>
        {name}
      </text>
      {detail && (
        <text x={x} y={y + 19} textAnchor={anchor}
          style={{ fontSize: 13.5, fontWeight: 500, fill: active ? 'rgb(var(--fg))' : 'rgb(var(--muted))' }}>
          {detail}
        </text>
      )}
    </g>
  )
}

export default function Track({ state }) {
  const reduce = useReducedMotion()
  const { status, stage, docs, grades, action, web, latency } = state
  const running = status !== 'idle'
  const retrieved = docs.length > 0
  const decided = Boolean(action) && Boolean(grades)
  const routeTone = decided ? color(ROUTES[action].key) : null
  const branchBLit = decided && (action === 'CORRECT' || Boolean(web))
  const failed = status === 'error'

  const counts = grades
    ? { useful: grades.filter((g) => g === 'relevant').length, partly: grades.filter((g) => g === 'partial').length,
        not: grades.filter((g) => g === 'irrelevant').length }
    : null

  const st = (name) => {
    if (failed) return 'idle'
    const order = ['search', 'rate', 'web', 'write', 'done']
    const at = order.indexOf(stage)
    const me = order.indexOf(name)
    if (stage === null) return 'idle'
    if (at > me) return 'done'
    return at === me ? 'active' : 'idle'
  }
  const answerState = stage === 'done' ? 'done' : stage === 'write' ? 'active' : 'idle'

  return (
    <div className="-mx-2 overflow-x-auto px-2">
      <svg viewBox="0 0 1000 250" className="block w-full min-w-[720px]" role="img"
        aria-label={decided ? `Pipeline took the route: ${ROUTES[action].label}` : 'CRAG pipeline route map'}>
        {/* main line */}
        <Segment d={`M${X.question} ${Y} H${X.search}`} lit={running && !failed} tone="rgb(var(--fg))" reduce={reduce} />
        <Segment d={`M${X.search} ${Y} H${X.rate}`} lit={retrieved} tone="rgb(var(--fg))" reduce={reduce} />

        {/* three branches: base track for all, lit overlay for the chosen one */}
        {Object.entries(BRANCHES).map(([key, b]) => {
          const chosen = decided && key === action
          const dim = decided && !chosen
          const tone = color(ROUTES[key].key)
          return (
            <g key={key}>
              <Segment d={b.a} lit={chosen} tone={tone} dim={dim} reduce={reduce} />
              <Segment d={b.b} lit={chosen && branchBLit} tone={tone} dim={dim} delay={key === 'CORRECT' ? 0.5 : 0} reduce={reduce} />
              <text x="600" y={b.labelY} textAnchor="middle"
                style={{ fontSize: 13.5, fontWeight: chosen ? 800 : 600, fill: chosen ? tone : 'rgb(var(--faint))',
                  opacity: dim ? 0.55 : 1, transition: 'all .4s' }}>
                {ROUTES[key].label}
              </text>
              {b.stop && (
                <>
                  <Station x={X.web} y={b.stop} reduce={reduce}
                    state={chosen ? (web ? 'done' : 'active') : 'idle'} tone={chosen ? tone : null} />
                  <text x={X.web} y={b.stop + 32} textAnchor="middle"
                    style={{ fontSize: 13, fontWeight: 600, fill: chosen ? 'rgb(var(--fg))' : 'rgb(var(--faint))',
                      opacity: dim ? 0.55 : 1, transition: 'all .4s' }}>
                    {chosen && web ? `Web search, ${web.length} results` : 'Web search'}
                  </text>
                </>
              )}
            </g>
          )
        })}

        {/* stations on the main line */}
        <rect x={X.question - 4} y={Y - 16} width="8" height="32" rx="4"
          style={{ fill: running && !failed ? 'rgb(var(--fg))' : 'rgb(var(--line-strong))', transition: 'fill .3s' }} />
        <Station x={X.search} y={Y} state={st('search')} reduce={reduce} />
        <Station x={X.rate} y={Y} state={st('rate')} reduce={reduce} />
        <Station x={X.answer} y={Y} state={answerState} tone={routeTone} reduce={reduce} />

        <Label x={X.question} y={84} name="Question" detail={running ? 'asked' : 'you ask'} />
        <Label x={X.search} y={84} name="Search the report" active={st('search') === 'active'}
          detail={retrieved ? `${docs.length} passages found` : st('search') === 'active' ? 'searching…' : 'top 4 passages'} />
        <Label x={X.rate - 8} y={84} anchor="end" name="Rate passages" active={st('rate') === 'active'}
          detail={counts ? countText(counts) : st('rate') === 'active' ? 'the LLM is judging…' : 'useful, partly, or not'} />
        <Label x={X.answer + 10} y={84} anchor="end" name="Answer" active={answerState === 'active'}
          detail={stage === 'done' && latency != null ? `${latency} s` : answerState === 'active' ? 'writing…' : 'with sources'} />
      </svg>
    </div>
  )
}
