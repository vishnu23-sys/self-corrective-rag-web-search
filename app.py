"""Streamlit demo UI.  Run:  streamlit run app.py"""
import html
import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from crag import config
from crag.graph import run_baseline, stream_crag

st.set_page_config(page_title="Corrective RAG", page_icon="🔎", layout="wide",
                   initial_sidebar_state="collapsed")

DOCS = Path(__file__).parent / "docs"

# (button text, full question): one per route, all from the real test set
SAMPLES = [
    ("What is algorithmic bias?", "How does the report define algorithmic bias?"),
    ("Who released ChatGPT, and when?", "Which company released ChatGPT, and when was it first released to the public?"),
    ("Who painted the Mona Lisa?", "Who painted the Mona Lisa?"),
]

ROUTES = {
    "CORRECT": ("notes", "Answered from the report", "At least one passage was useful, so the web wasn't needed."),
    "AMBIGUOUS": ("mixed", "Report plus a web search", "Passages were only partly useful, so a web search filled the gaps."),
    "INCORRECT": ("web", "Answered from the web", "No passage was useful, so they were dropped and the web was searched."),
}
GRADE_LABEL = {"relevant": "Useful", "partial": "Partly useful", "irrelevant": "Not useful"}

# chart colors (validated with the dataviz palette checker): CRAG in focus, baseline as muted context
C_CRAG, C_BASE, C_INK, C_SOFT, C_LINE = "#0A8F87", "#9AA3B2", "#1C2333", "#5A6478", "#D5DBE4"


def show(markup: str) -> None:
    """Render raw HTML. Blank lines would end Streamlit's HTML block, so collapse them."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines() if line.strip()),
                unsafe_allow_html=True)


show(
    """
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;800&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#EEF1F5; --card:#FFFFFF; --ink:#1C2333; --soft:#5A6478; --line:#D5DBE4;
  --notes:#0F6E6E; --notes-bg:#E1F0EF;
  --web:#4B3FB0;   --web-bg:#E9E7F8;
  --mixed:#A86A12; --mixed-bg:#F6EBD9;
  --off:#8A94A6;
}
html, body, .stApp, .stApp *:not([class*="icon"]):not([data-testid="stIconMaterial"]):not(.material-symbols-rounded){
  font-family:"Schibsted Grotesk", system-ui, sans-serif !important;
}
.stApp{background:var(--paper);}
.block-container{max-width:1180px; padding-top:2rem;}
header[data-testid="stHeader"]{background:transparent;}

.masthead h1{font-size:2.6rem; font-weight:800; letter-spacing:-0.03em; line-height:1.05; color:var(--ink); margin:0 0 .35rem;}
.masthead p{color:var(--soft); font-size:1.05rem; margin:0 0 1rem; max-width:66ch;}

/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:1.6rem; border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{font-size:1rem; font-weight:600; color:var(--soft); padding:.6rem 0;}
.stTabs [aria-selected="true"]{color:var(--ink);}
.stTabs [data-baseweb="tab-highlight"]{background:var(--ink);}

/* question bar */
div[data-testid="stTextInput"] input{font-size:1.1rem; padding:.85rem 1rem; border-radius:10px; border:1.5px solid var(--line); background:var(--card);}
div[data-testid="stTextInput"] input:focus{border-color:var(--ink); box-shadow:0 0 0 3px rgba(28,35,51,.12);}
.stButton button{border-radius:10px; font-weight:600;}
.stButton button[kind="primary"]{background:var(--ink); border-color:var(--ink); padding:.7rem 1.4rem;}
.stButton button[kind="primary"]:hover{background:#2E3850; border-color:#2E3850;}
.stButton button[kind="secondary"]{background:transparent; border:1px solid var(--line); color:var(--soft); font-weight:500;}
.stButton button[kind="secondary"]:hover{border-color:var(--ink); color:var(--ink);}
.hint{color:var(--soft); font-size:.9rem; margin:.3rem 0 .4rem;}

/* live pipeline stepper: the one bold element */
.pipe{background:var(--card); border-radius:14px; padding:1.2rem 1.4rem 1.1rem; margin:1.4rem 0 1.2rem; border:1px solid var(--line);}
.steps{display:grid; grid-template-columns:repeat(5, 1fr); gap:.5rem; position:relative;}
.step{position:relative; padding-top:2.1rem;}
.step::before{content:""; position:absolute; top:.72rem; left:1.6rem; right:-.5rem; height:2px; background:var(--line);}
.step:last-child::before{display:none;}
.step.done::before{background:var(--ink);}
.step .mark{position:absolute; top:0; left:0; width:1.5rem; height:1.5rem; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-size:.75rem; font-weight:700; background:var(--paper); color:var(--off); border:2px solid var(--line);}
.step.done .mark{background:var(--ink); border-color:var(--ink); color:#fff;}
.step.active .mark{background:#fff; border-color:var(--ink); color:var(--ink); animation:pulse 1.1s ease-in-out infinite;}
.step.skipped .mark{border-style:dashed;}
.step .name{font-weight:600; font-size:.92rem; color:var(--ink);}
.step.pending .name, .step.skipped .name{color:var(--off);}
.step .detail{font-size:.82rem; color:var(--soft); margin-top:.15rem; line-height:1.35;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(28,35,51,.35);} 50%{box-shadow:0 0 0 6px rgba(28,35,51,0);}}
@media (prefers-reduced-motion: reduce){ .step.active .mark{animation:none;} }
.branches{display:flex; gap:.5rem; flex-wrap:wrap; margin-top:1rem;}
.branch{border:1.5px dashed var(--line); color:var(--off); border-radius:999px; padding:.3rem .85rem; font-size:.88rem; font-weight:500;}
.branch.on{border-style:solid; font-weight:700;}
.branch.on.notes{background:var(--notes-bg); border-color:var(--notes); color:var(--notes);}
.branch.on.web{background:var(--web-bg); border-color:var(--web); color:var(--web);}
.branch.on.mixed{background:var(--mixed-bg); border-color:var(--mixed); color:var(--mixed);}
.route-why{margin:.8rem 0 0; color:var(--ink); font-size:1rem;}
.route-why b.notes{color:var(--notes);} .route-why b.web{color:var(--web);} .route-why b.mixed{color:var(--mixed);}
.route-meta{color:var(--soft); font-size:.85rem; margin-top:.3rem;}

/* answer */
.panel-title{font-size:.95rem; font-weight:600; color:var(--soft); margin:0 0 .6rem;}
.answer{font-size:1.28rem; line-height:1.6; color:var(--ink); max-width:62ch; margin-bottom:1.4rem;}
.caret{display:inline-block; width:.55em; height:1.1em; background:var(--ink); vertical-align:-.15em; margin-left:.1em; animation:blink 1s steps(1) infinite;}
@keyframes blink{50%{opacity:0;}}
@media (prefers-reduced-motion: reduce){ .caret{animation:none;} }
.cite{display:inline-block; font-size:.72rem; font-weight:700; line-height:1; vertical-align:super; padding:.18rem .38rem; border-radius:6px; margin:0 .1rem; color:#fff; background:var(--ink);}
.sources{list-style:none; padding:0; margin:0;}
.sources li{display:flex; gap:.7rem; padding:.55rem 0; border-top:1px solid var(--line); font-size:.92rem;}
.sources .n{flex:0 0 1.6rem; height:1.6rem; border-radius:6px; background:var(--ink); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.78rem;}
.sources .kind{color:var(--soft); font-size:.8rem;}
.sources a{color:var(--web); text-decoration:none; word-break:break-all;}
.sources a:hover{text-decoration:underline;}

/* evidence slips */
.slip{background:var(--card); border-radius:10px; padding:.8rem .95rem; margin-bottom:.6rem; border-left:4px solid var(--off);}
.slip.relevant{border-left-color:var(--notes);} .slip.partial{border-left-color:var(--mixed);} .slip.irrelevant{opacity:.62;}
.slip-head{display:flex; justify-content:space-between; gap:.5rem; font-size:.82rem; margin-bottom:.35rem;}
.slip-head .verdict{font-weight:700; white-space:nowrap;}
.slip.relevant .verdict{color:var(--notes);} .slip.partial .verdict{color:var(--mixed);} .slip.irrelevant .verdict{color:var(--off);}
.slip-head .src{color:var(--soft); text-align:right;}
.slip-body{font-size:.86rem; color:var(--ink); line-height:1.45; display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden;}

.compare{background:var(--card); border-radius:14px; border:1px solid var(--line); padding:1.2rem 1.4rem;}
.compare .answer{font-size:1.05rem; margin-bottom:.4rem;}
.empty{color:var(--soft); background:var(--card); border:1.5px dashed var(--line); border-radius:14px; padding:2rem; text-align:center; margin-top:1.4rem;}

/* results */
.tiles{display:grid; grid-template-columns:repeat(4, 1fr); gap:.8rem; margin:1.4rem 0 1.6rem;}
.tile{background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem;}
.tile .k{font-size:.88rem; color:var(--soft); font-weight:500;}
.tile .v{font-size:2.1rem; font-weight:800; color:var(--ink); letter-spacing:-.02em; line-height:1.15; margin-top:.2rem;}
.tile .vs{font-size:.88rem; color:var(--soft); margin-top:.1rem;}
.tile .v small{font-size:1rem; font-weight:600; color:var(--soft);}
.section h3{font-size:1.25rem; font-weight:700; color:var(--ink); margin:1.6rem 0 .2rem;}
.section p{color:var(--soft); font-size:.95rem; max-width:70ch; margin:0 0 .6rem;}
.callout{background:var(--card); border-left:4px solid var(--ink); border-radius:10px; padding:.9rem 1.1rem; margin:.6rem 0 1rem; color:var(--ink); font-size:.95rem; max-width:80ch;}

/* how it works */
.diagram{background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1rem; margin:1.2rem 0;}
.diagram svg{width:100%; height:auto; display:block;}
.explain{display:grid; grid-template-columns:repeat(2, 1fr); gap:.8rem 1.6rem; margin-top:.6rem;}
.explain div{font-size:.95rem; color:var(--ink); line-height:1.5;}
.explain b{display:block; margin-bottom:.15rem;}
.explain span{color:var(--soft);}

@media (max-width: 760px){
  .masthead h1{font-size:2rem;} .answer{font-size:1.1rem;}
  .steps{grid-template-columns:1fr; gap:.2rem;}
  .step{padding:0 0 .7rem 2.2rem;} .step::before{top:1.6rem; left:.72rem; right:auto; width:2px; height:calc(100% - 1.4rem);}
  .tiles{grid-template-columns:repeat(2, 1fr);} .explain{grid-template-columns:1fr;}
}
</style>
"""
)


# ------------------------------------------------------------------ helpers

def render_answer(text: str) -> str:
    safe = html.escape(text)
    # models write [1], 【1】 or 【1†source】; render them all as citation chips
    return re.sub(r"\s?[\[【](\d+)(?:†[^\]】]*)?[\]】]", r'<span class="cite">\1</span>', safe)


def render_sources(chunks: list[dict]) -> str:
    items = []
    for i, c in enumerate(chunks, 1):
        src = html.escape(str(c["source"]))
        if src.startswith("http"):
            label, where = f'<a href="{src}" target="_blank" rel="noopener">{src}</a>', "Web"
        else:
            label, where = src, "The report"
        items.append(f'<li><span class="n">{i}</span><span>{label}<br><span class="kind">{where}</span></span></li>')
    return f'<ul class="sources">{"".join(items)}</ul>' if items else ""


def render_slips(docs: list[dict]) -> str:
    out = []
    for d in docs:
        g = d.get("grade", "irrelevant")
        body = re.sub(r"(^|\n)[#>\s]+", " ", d["content"]).strip()
        out.append(
            f'<div class="slip {g}"><div class="slip-head"><span class="verdict">{GRADE_LABEL[g]}</span>'
            f'<span class="src">{html.escape(d["source"])}, match {d["score"]}</span></div>'
            f'<div class="slip-body">{html.escape(body)}</div></div>'
        )
    return "".join(out)


def render_pipeline(state: dict, writing: bool = False, done: bool = False) -> str:
    """The stepper. Works mid-run (from partial state) and for the finished result."""
    docs = state.get("documents")
    action = state.get("action")
    graded = action is not None
    web_needed = graded and action != "CORRECT"
    searched = "web_results" in state

    counts = {g: sum(d.get("grade") == g for d in docs or []) for g in GRADE_LABEL}
    steps = [
        ("Search the report", docs is not None,
         f"Found {len(docs)} closest passages" if docs is not None else "Finding the closest passages"),
        ("Rate each passage", graded,
         f"{counts['relevant']} useful, {counts['partial']} partly, {counts['irrelevant']} not" if graded
         else "The LLM judges if each passage helps"),
        ("Choose a route", graded, ROUTES[action][1] if graded else "Report, web, or both"),
        ("Search the web", searched if web_needed else graded,
         ("Not needed" if graded and not web_needed else
          f"{len(state.get('web_results', []))} results" if searched else "Only if the report falls short")),
        ("Write the answer", done, "Done, with citations" if done else
         "Writing…" if writing else "Using only the chosen sources"),
    ]
    first_open = next((i for i, (_, ok, _) in enumerate(steps) if not ok), None)
    cells = []
    for i, (name, ok, detail) in enumerate(steps):
        skipped = name == "Search the web" and graded and not web_needed
        cls = "skipped" if skipped else "done" if ok else "active" if i == first_open and not done else "pending"
        mark = "–" if skipped else "✓" if ok else str(i + 1)
        cells.append(f'<div class="step {cls}"><span class="mark">{mark}</span>'
                     f'<div class="name">{name}</div><div class="detail">{html.escape(detail)}</div></div>')

    branches = "".join(f'<span class="branch {k} {"on" if action == a else ""}">{t}</span>'
                       for a, (k, t, _) in ROUTES.items())
    footer = ""
    if done and action:
        key, title, why = ROUTES[action]
        q = f' Web query: “{html.escape(state["search_query"])}”.' if state.get("search_query") else ""
        footer = (f'<p class="route-why"><b class="{key}">{title}.</b> {why}</p>'
                  f'<p class="route-meta">Took {state.get("latency_s", "?")} s.{q}</p>')
    return f'<div class="pipe"><div class="steps">{"".join(cells)}</div><div class="branches">{branches}</div>{footer}</div>'


def load_json(name: str):
    p = DOCS / name
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ page

show('<div class="masthead"><h1>Corrective RAG</h1>'
     "<p>Ask a question about the US Department of Education report <i>AI and the Future of Teaching "
     "and Learning</i> (2023), or anything else. Before answering, it checks whether the passages it "
     "found actually help, and searches the web when they don't.</p></div>")

tab_ask, tab_results, tab_how = st.tabs(["Ask a question", "Results", "How it works"])

# ================================================================== ASK
with tab_ask:
    if "q" not in st.session_state:
        st.session_state.q = ""

    c_in, c_btn = st.columns([5, 1], vertical_alignment="bottom")
    with c_in:
        question = st.text_input("Your question", key="q", label_visibility="collapsed",
                                 placeholder="Ask about AI in teaching and learning, or anything else")
    with c_btn:
        ask = st.button("Ask", type="primary", width="stretch")

    show('<p class="hint">Or try one of these. The first is in the report, the second is only partly '
         "covered, the third isn't in it at all.</p>")
    for col, (label, q) in zip(st.columns(len(SAMPLES)), SAMPLES):
        if col.button(label, width="stretch", help=q):
            st.session_state.pending = q
            st.rerun()

    # a sample button sets the question on the next run (text_input value can't change after render)
    if "pending" in st.session_state:
        question = st.session_state.pop("pending")
        ask = True

    if ask and question.strip():
        pipe_ph, answer_ph = st.empty(), st.empty()
        pipe_ph.markdown(render_pipeline({}), unsafe_allow_html=True)
        written, final, last_state = "", None, {}
        try:
            for ev in stream_crag(question.strip()):
                if ev[0] == "step":
                    pipe_ph.markdown(render_pipeline(ev[2]), unsafe_allow_html=True)
                    last_state = ev[2]
                elif ev[0] == "token":
                    if not written:
                        pipe_ph.markdown(render_pipeline(last_state, writing=True), unsafe_allow_html=True)
                    written += ev[1]
                    answer_ph.markdown(f'<div class="answer">{render_answer(written)}<span class="caret"></span></div>',
                                       unsafe_allow_html=True)
                else:
                    final = ev[1]
        except Exception as e:  # rate limits, network, missing index -> say what to do, not a stack trace
            msg = str(e)
            hint = ("Groq's free-tier rate limit was hit. Wait a minute and ask again."
                    if "rate_limit" in msg or "429" in msg else
                    "Check the API keys in .env, your network/VPN, and that `python -m crag.ingest` has been run.")
            st.error(f"The pipeline stopped: {hint}")
            with st.expander("Error details"):
                st.code(msg[:1500])
        if final:
            st.session_state.result = final
            st.session_state.baseline = None
            st.rerun()

    res = st.session_state.get("result")
    if not res:
        if not ask:
            show('<div class="empty">Ask something to watch the pipeline work: it searches the report, rates '
                 "each passage, picks a route, and writes an answer with sources.</div>")
    else:
        show(render_pipeline(res, done=True))
        left, right = st.columns([3, 2], gap="large")
        with left:
            show(f'<p class="panel-title">Answer to “{html.escape(res["question"])}”</p>'
                 f'<div class="answer">{render_answer(res["answer"])}</div>')
            if res.get("context"):
                show('<p class="panel-title">Sources used</p>' + render_sources(res["context"]))
        with right:
            show('<p class="panel-title">How each passage from the report was rated</p>'
                 + render_slips(res.get("documents", [])))

        st.write("")
        if st.toggle("Compare with plain RAG (no rating, no web search)"):
            if not st.session_state.get("baseline") or st.session_state.baseline["question"] != res["question"]:
                with st.spinner("Running plain RAG…"):
                    st.session_state.baseline = run_baseline(res["question"])
            b = st.session_state.baseline
            show(f'<div class="compare"><p class="panel-title">Plain RAG always answers from the top '
                 f'{len(b["documents"])} passages, useful or not. Took {b["latency_s"]} s.</p>'
                 f'<div class="answer">{render_answer(b["answer"])}</div></div>')

# ================================================================== RESULTS
with tab_results:
    ev = load_json("eval_summary.json")
    if not ev:
        st.info("No evaluation summary yet. Run `python -m eval.run_eval` and update docs/eval_summary.json.")
    else:
        c, b = ev["systems"]["crag"], ev["systems"]["baseline"]
        nq = sum(ev["questions"].values())
        pct = lambda x: f"{x * 100:.1f}%"  # noqa: E731
        show(f"""<div class="tiles">
          <div class="tile"><div class="k">Correct answers</div><div class="v">{pct(c['accuracy'])}</div>
            <div class="vs">Plain RAG: {pct(b['accuracy'])}</div></div>
          <div class="tile"><div class="k">Wrong answers (hallucinations)</div><div class="v">{pct(c['hallucination_rate'])}</div>
            <div class="vs">Plain RAG: {pct(b['hallucination_rate'])}</div></div>
          <div class="tile"><div class="k">Average time per question</div><div class="v">{c['avg_latency_s']:.1f}<small> s</small></div>
            <div class="vs">Plain RAG: {b['avg_latency_s']:.1f} s. Rating and web search cost time.</div></div>
          <div class="tile"><div class="k">Test set</div><div class="v">{nq}<small> questions</small></div>
            <div class="vs">{ev['questions']['in_kb']} in the report, {ev['questions']['partial']} partly, {ev['questions']['out_of_kb']} not</div></div>
        </div>""")

        # ---- chart 1: accuracy by question type
        show('<div class="section"><h3>Accuracy by question type</h3>'
             "<p>Plain RAG can only answer from the report, so it scores zero on anything the report doesn't fully "
             "cover. CRAG notices weak passages and fills the gap from the web.</p></div>")
        type_names = {"in_kb": "In the report", "partial": "Partly covered", "out_of_kb": "Not in the report"}
        rows = [{"Question type": type_names[t], "System": s["label"], "Accuracy": s["by_type"][t]}
                for s in (b, c) for t in type_names]
        rows += [{"Question type": "All questions", "System": s["label"], "Accuracy": s["accuracy"]} for s in (b, c)]
        df = pd.DataFrame(rows)
        order = list(type_names.values()) + ["All questions"]
        color = alt.Color("System:N", scale=alt.Scale(domain=["Plain RAG", "CRAG"], range=[C_BASE, C_CRAG]),
                          legend=alt.Legend(orient="top", title=None, labelFontSize=13, symbolType="square"))
        base = alt.Chart(df).encode(
            x=alt.X("Question type:N", sort=order, title=None,
                    axis=alt.Axis(labelAngle=0, labelFontSize=13, labelColor=C_INK, domainColor=C_LINE, ticks=False)),
            xOffset=alt.XOffset("System:N", sort=["Plain RAG", "CRAG"]),
        )
        bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, width=alt.RelativeBandSize(0.38)).encode(
            y=alt.Y("Accuracy:Q", scale=alt.Scale(domain=[0, 1]), title=None,
                    axis=alt.Axis(format=".0%", tickCount=5, labelColor=C_SOFT, gridColor="#E8ECF2", domain=False, ticks=False)),
            color=color,
            tooltip=[alt.Tooltip("System:N"), alt.Tooltip("Question type:N"), alt.Tooltip("Accuracy:Q", format=".1%")],
        )
        labels = base.mark_text(dy=-8, fontSize=12, fontWeight=600, color=C_INK).encode(
            y="Accuracy:Q", text=alt.Text("Accuracy:Q", format=".0%"))
        chart = (bars + labels).properties(height=320).configure_view(strokeWidth=0).configure(background="transparent")
        st.altair_chart(chart, width="stretch")
        with st.expander("Show as a table"):
            st.dataframe(df.pivot(index="Question type", columns="System", values="Accuracy").reindex(order)
                         .style.format("{:.1%}"), width="stretch")
        show('<div class="callout"><b>Where CRAG still misses:</b> questions whose answer is a list spread across '
             "several pages (\"the seven recommendations\", \"the six characteristics\"). The top 4 passages don't hold "
             "the whole list, so it says it doesn't know rather than guess. That's a retrieval limit, not a rating error.</div>")

    # ---- chart 2: prompt optimization
    pe = load_json("prompt_experiment_summary.json")
    show('<div class="section"><h3>Prompt optimization: rating accuracy vs cost</h3>'
         "<p>The rating prompt decides the route, so we tested several versions. Each one rates the same retrieved "
         "passages; we measure how often it picks the right route and how many tokens it spends per question. "
         "Up and to the left is better.</p></div>")
    if not pe:
        st.info("No prompt-experiment summary yet. Run `python -m eval.prompt_experiment`.")
    else:
        names = {"zero_shot": "Zero-shot", "few_shot": "Few-shot", "cot": "Chain-of-thought",
                 "few_shot_cot": "Few-shot + CoT", "batch_few_shot": "Batch few-shot"}
        current = f"{config.GRADER_VARIANT} @ {(config.GRADER_MODEL or config.GROQ_MODEL).split('/')[-1]}"
        pdf = pd.DataFrame(pe["setups"])
        pdf["Setup"] = pdf["variant"].map(names).fillna(pdf["variant"]) + " (" + pdf["model"] + ")"
        pdf["In use"] = pdf["setup"].eq(current).map({True: "Used by the app", False: "Other versions"})
        pts = alt.Chart(pdf).encode(
            x=alt.X("avg_tokens:Q", title="Tokens per question (cost)", scale=alt.Scale(zero=False, padding=30),
                    axis=alt.Axis(format=",.0f", labelColor=C_SOFT, titleColor=C_SOFT, gridColor="#E8ECF2", domain=False, ticks=False)),
            y=alt.Y("route_accuracy:Q", title="Route accuracy", scale=alt.Scale(zero=False, padding=20),
                    axis=alt.Axis(format=".0%", labelColor=C_SOFT, titleColor=C_SOFT, gridColor="#E8ECF2", domain=False, ticks=False)),
        )
        dots = pts.mark_circle(size=170, opacity=1, stroke="#FFFFFF", strokeWidth=2).encode(
            color=alt.Color("In use:N", scale=alt.Scale(domain=["Used by the app", "Other versions"], range=[C_CRAG, C_BASE]),
                            legend=alt.Legend(orient="top", title=None, labelFontSize=13)),
            tooltip=[alt.Tooltip("Setup:N"), alt.Tooltip("route_accuracy:Q", title="Route accuracy", format=".1%"),
                     alt.Tooltip("partial_accuracy:Q", title="Partly-covered accuracy", format=".0%"),
                     alt.Tooltip("avg_tokens:Q", title="Tokens / question", format=","),
                     alt.Tooltip("llm_calls:Q", title="LLM calls / question")],
        )
        text = pts.mark_text(align="left", dx=11, fontSize=12, color=C_INK).encode(text="Setup:N")
        st.altair_chart((dots + text).properties(height=340).configure_view(strokeWidth=0)
                        .configure(background="transparent"), width="stretch")
        with st.expander("Show as a table"):
            st.dataframe(pdf[["Setup", "route_accuracy", "partial_accuracy", "avg_tokens", "llm_calls", "runs"]]
                         .rename(columns={"route_accuracy": "Route accuracy", "partial_accuracy": "Partly-covered accuracy",
                                          "avg_tokens": "Tokens / question", "llm_calls": "LLM calls", "runs": "Runs"})
                         .style.format({"Route accuracy": "{:.1%}", "Partly-covered accuracy": "{:.0%}",
                                        "Tokens / question": "{:,.0f}"}, na_rep="-"),
                         width="stretch", hide_index=True)
        st.caption(f"{pe['questions']} questions, generated {pe['generated']}. Full tables: docs/prompt_experiment_results.md")

# ================================================================== HOW IT WORKS
with tab_how:
    show("""
<div class="diagram">
<svg viewBox="0 0 980 300" role="img" aria-label="CRAG pipeline: search the report, rate passages, then one of three routes, then write the answer">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#1C2333"/></marker>
  </defs>
  <style>
    .bx{fill:#FFFFFF; stroke:#1C2333; stroke-width:1.5;} .t{font:600 15px 'Schibsted Grotesk',sans-serif; fill:#1C2333;}
    .s{font:400 12.5px 'Schibsted Grotesk',sans-serif; fill:#5A6478;} .ln{stroke:#1C2333; stroke-width:1.5; fill:none;}
  </style>
  <rect class="bx" x="10" y="120" width="130" height="60" rx="10"/>
  <text class="t" x="75" y="147" text-anchor="middle">Question</text><text class="s" x="75" y="166" text-anchor="middle">from the user</text>
  <path class="ln" d="M140 150 H178" marker-end="url(#ah)"/>
  <rect class="bx" x="180" y="120" width="150" height="60" rx="10"/>
  <text class="t" x="255" y="147" text-anchor="middle">Search the report</text><text class="s" x="255" y="166" text-anchor="middle">top 4 passages</text>
  <path class="ln" d="M330 150 H368" marker-end="url(#ah)"/>
  <rect class="bx" x="370" y="120" width="160" height="60" rx="10"/>
  <text class="t" x="450" y="147" text-anchor="middle">LLM rates passages</text><text class="s" x="450" y="166" text-anchor="middle">useful / partly / not</text>
  <path class="ln" d="M530 150 C560 150 560 45 598 45" marker-end="url(#ah)"/>
  <path class="ln" d="M530 150 H598" marker-end="url(#ah)"/>
  <path class="ln" d="M530 150 C560 150 560 255 598 255" marker-end="url(#ah)"/>
  <rect x="600" y="18" width="200" height="56" rx="10" fill="#E1F0EF" stroke="#0F6E6E" stroke-width="1.5"/>
  <text class="t" x="700" y="42" text-anchor="middle" style="fill:#0F6E6E">≥1 useful</text><text class="s" x="700" y="60" text-anchor="middle">use the useful passages</text>
  <rect x="600" y="122" width="200" height="56" rx="10" fill="#F6EBD9" stroke="#A86A12" stroke-width="1.5"/>
  <text class="t" x="700" y="146" text-anchor="middle" style="fill:#A86A12">Only partly useful</text><text class="s" x="700" y="164" text-anchor="middle">passages + web search</text>
  <rect x="600" y="226" width="200" height="56" rx="10" fill="#E9E7F8" stroke="#4B3FB0" stroke-width="1.5"/>
  <text class="t" x="700" y="250" text-anchor="middle" style="fill:#4B3FB0">None useful</text><text class="s" x="700" y="268" text-anchor="middle">rewrite query, web search</text>
  <path class="ln" d="M800 46 C830 46 830 150 848 150" marker-end="url(#ah)"/>
  <path class="ln" d="M800 150 H848" marker-end="url(#ah)"/>
  <path class="ln" d="M800 254 C830 254 830 150 848 150" marker-end="url(#ah)"/>
  <rect class="bx" x="850" y="120" width="120" height="60" rx="10"/>
  <text class="t" x="910" y="147" text-anchor="middle">Answer</text><text class="s" x="910" y="166" text-anchor="middle">with citations</text>
</svg>
</div>
<div class="explain">
  <div><b>1. Search the report</b><span>The 71-page report is split into 325 passages and turned into vectors (BGE embeddings,
    ChromaDB). The 4 passages closest to the question are retrieved.</span></div>
  <div><b>2. Rate each passage</b><span>An LLM labels every passage useful, partly useful or not useful. This rating prompt is
    the part we optimized: zero-shot, few-shot, chain-of-thought, and batch rating (all passages in one call).</span></div>
  <div><b>3. Choose a route</b><span>Based on Corrective RAG (Yan et al., 2024): trust the report, combine it with the web,
    or drop it and search the web (Tavily) with a rewritten query.</span></div>
  <div><b>4. Write the answer</b><span>The LLM answers only from the chosen sources and cites them. If they don't contain the
    answer, it says it doesn't know instead of guessing.</span></div>
</div>
""")
    st.caption(f"LLM: {config.GROQ_MODEL} on Groq. Rating prompt in use: {config.GRADER_VARIANT}. "
               f"Embeddings: {config.EMBED_MODEL}. Built with LangGraph, ChromaDB, Tavily and Streamlit.")
