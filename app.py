"""Streamlit demo UI.  Run:  streamlit run app.py"""
import html
import re

import streamlit as st

from crag.graph import run_baseline, run_crag

st.set_page_config(page_title="Corrective RAG", page_icon="🔎", layout="wide",
                   initial_sidebar_state="collapsed")

# (button text, full question)
SAMPLES = [
    ("How does CRAG fix bad retrieval?", "What does CRAG do when retrieved documents are judged incorrect?"),
    ("What is the capital of Australia?", "What is the capital city of Australia?"),
    ("Who proposed ReAct, and when?", "Who proposed the ReAct prompting framework and in what year?"),
]

ROUTES = {
    "CORRECT": ("notes", "Answered from your notes", "At least one passage was useful, so the web wasn't needed."),
    "AMBIGUOUS": ("mixed", "Notes plus a web search", "Passages were only partly useful, so a web search filled the gaps."),
    "INCORRECT": ("web", "Answered from the web", "No passage was useful, so they were dropped and the web was searched."),
}
GRADE_LABEL = {"relevant": "Useful", "partial": "Partly useful", "irrelevant": "Not useful"}


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
html, body, .stApp, .stApp *:not([class*="icon"]):not(.material-symbols-rounded){
  font-family:"Schibsted Grotesk", system-ui, sans-serif !important;
}
.stApp{background:var(--paper);}
.block-container{max-width:1180px; padding-top:2.2rem;}
header[data-testid="stHeader"]{background:transparent;}

.masthead h1{font-size:2.6rem; font-weight:800; letter-spacing:-0.03em; line-height:1.05;
  color:var(--ink); margin:0 0 .35rem;}
.masthead p{color:var(--soft); font-size:1.05rem; margin:0 0 1.4rem; max-width:62ch;}

/* question bar */
div[data-testid="stTextInput"] input{font-size:1.1rem; padding:.85rem 1rem; border-radius:10px;
  border:1.5px solid var(--line); background:var(--card);}
div[data-testid="stTextInput"] input:focus{border-color:var(--ink); box-shadow:0 0 0 3px rgba(28,35,51,.12);}
.stButton button{border-radius:10px; font-weight:600;}
.stButton button[kind="primary"]{background:var(--ink); border-color:var(--ink); padding:.7rem 1.4rem;}
.stButton button[kind="primary"]:hover{background:#2E3850; border-color:#2E3850;}
.stButton button[kind="secondary"]{background:transparent; border:1px solid var(--line); color:var(--soft);
  font-weight:500; text-align:left;}
.stButton button[kind="secondary"]:hover{border-color:var(--ink); color:var(--ink);}
.samples-hint{color:var(--soft); font-size:.9rem; margin:.3rem 0 .4rem;}

/* route strip: the one bold element */
.route{background:var(--card); border-radius:14px; padding:1.3rem 1.5rem; margin:1.6rem 0 1.2rem;
  border:1px solid var(--line);}
.route-steps{display:flex; align-items:center; gap:.6rem; flex-wrap:wrap; color:var(--soft); font-size:.95rem;}
.route-steps .step{display:flex; align-items:center; gap:.45rem;}
.route-steps .dot{width:.55rem; height:.55rem; border-radius:50%; background:var(--ink);}
.route-steps .arrow{color:var(--line); font-size:1.2rem;}
.branches{display:flex; gap:.6rem; flex-wrap:wrap;}
.branch{border:1.5px dashed var(--line); color:var(--off); border-radius:999px; padding:.35rem .9rem;
  font-size:.9rem; font-weight:500;}
.branch.on{border-style:solid; font-weight:700;}
.branch.on.notes{background:var(--notes-bg); border-color:var(--notes); color:var(--notes);}
.branch.on.web{background:var(--web-bg); border-color:var(--web); color:var(--web);}
.branch.on.mixed{background:var(--mixed-bg); border-color:var(--mixed); color:var(--mixed);}
.route-why{margin:.9rem 0 0; color:var(--ink); font-size:1rem;}
.route-why b.notes{color:var(--notes);} .route-why b.web{color:var(--web);} .route-why b.mixed{color:var(--mixed);}
.route-meta{color:var(--soft); font-size:.85rem; margin-top:.35rem;}

/* answer */
.panel-title{font-size:.95rem; font-weight:600; color:var(--soft); margin:0 0 .6rem;}
.answer{font-size:1.28rem; line-height:1.6; color:var(--ink); max-width:62ch; margin-bottom:1.4rem;}
.cite{display:inline-block; font-size:.72rem; font-weight:700; line-height:1; vertical-align:super;
  padding:.18rem .38rem; border-radius:6px; margin:0 .1rem; color:#fff; background:var(--ink);}
.sources{list-style:none; padding:0; margin:0;}
.sources li{display:flex; gap:.7rem; padding:.55rem 0; border-top:1px solid var(--line); font-size:.92rem;}
.sources .n{flex:0 0 1.6rem; height:1.6rem; border-radius:6px; background:var(--ink); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.78rem;}
.sources .kind{color:var(--soft); font-size:.8rem;}
.sources a{color:var(--web); text-decoration:none; word-break:break-all;}
.sources a:hover{text-decoration:underline;}

/* evidence slips */
.slip{background:var(--card); border-radius:10px; padding:.8rem .95rem; margin-bottom:.6rem;
  border-left:4px solid var(--off);}
.slip.relevant{border-left-color:var(--notes);}
.slip.partial{border-left-color:var(--mixed);}
.slip.irrelevant{opacity:.62;}
.slip-head{display:flex; justify-content:space-between; gap:.5rem; font-size:.82rem; margin-bottom:.35rem;}
.slip-head .verdict{font-weight:700; white-space:nowrap;}
.slip.relevant .verdict{color:var(--notes);} .slip.partial .verdict{color:var(--mixed);}
.slip.irrelevant .verdict{color:var(--off);}
.slip-head .src{color:var(--soft); text-align:right;}
.slip-body{font-size:.86rem; color:var(--ink); line-height:1.45;
  display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden;}

/* comparison */
.compare{background:var(--card); border-radius:14px; border:1px solid var(--line); padding:1.2rem 1.4rem;}
.compare .answer{font-size:1.05rem; margin-bottom:.4rem;}

.empty{color:var(--soft); background:var(--card); border:1.5px dashed var(--line); border-radius:14px;
  padding:2rem; text-align:center; margin-top:1.6rem;}
@media (max-width: 640px){ .masthead h1{font-size:2rem;} .answer{font-size:1.1rem;} }
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
            label, where = src, "Your notes"
        items.append(f'<li><span class="n">{i}</span><span>{label}<br><span class="kind">{where}</span></span></li>')
    return f'<ul class="sources">{"".join(items)}</ul>' if items else ""


def render_route(res: dict) -> str:
    key, title, why = ROUTES[res["action"]]
    graded = res.get("documents", [])
    counts = {g: sum(d.get("grade") == g for d in graded) for g in GRADE_LABEL}
    branches = "".join(
        f'<span class="branch {k} {"on" if k == key else ""}">{t}</span>'
        for k, t, _ in ROUTES.values()
    )
    search = f' Web query: “{html.escape(res["search_query"])}”.' if res.get("search_query") else ""
    return f"""
<div class="route">
  <div class="route-steps">
    <span class="step"><span class="dot"></span>Searched your notes</span><span class="arrow">›</span>
    <span class="step"><span class="dot"></span>Checked {len(graded)} passages
      ({counts['relevant']} useful, {counts['partial']} partly, {counts['irrelevant']} not)</span>
    <span class="arrow">›</span>
    <span class="branches">{branches}</span>
  </div>
  <p class="route-why"><b class="{key}">{title}.</b> {why}</p>
  <p class="route-meta">Took {res['latency_s']} s.{search}</p>
</div>"""


def render_slips(docs: list[dict]) -> str:
    out = []
    for d in docs:
        g = d.get("grade", "irrelevant")
        out.append(
            f'<div class="slip {g}"><div class="slip-head"><span class="verdict">{GRADE_LABEL[g]}</span>'
            f'<span class="src">{html.escape(d["source"])} · match {d["score"]}</span></div>'
            f'<div class="slip-body">{html.escape(re.sub(r"(^|\n)[#>\s]+", " ", d["content"]).strip())}</div></div>'
        )
    return "".join(out)


# ------------------------------------------------------------------ page

st.markdown(
    '<div class="masthead"><h1>Corrective RAG</h1>'
    "<p>Ask a question. Before answering, it checks whether the passages it found in your notes "
    "actually help, and searches the web when they don't.</p></div>",
    unsafe_allow_html=True,
)

if "q" not in st.session_state:
    st.session_state.q = ""

c_in, c_btn = st.columns([5, 1], vertical_alignment="bottom")
with c_in:
    question = st.text_input("Your question", key="q", label_visibility="collapsed",
                             placeholder="Ask about prompting or RAG, or anything else")
with c_btn:
    ask = st.button("Ask", type="primary", use_container_width=True)

st.markdown('<p class="samples-hint">Or try one of these. The first is in the notes, the second '
            "isn't, the third is partly covered.</p>", unsafe_allow_html=True)
sample_cols = st.columns(len(SAMPLES))
for col, (label, q) in zip(sample_cols, SAMPLES):
    if col.button(label, use_container_width=True, help=q):
        st.session_state.pending = q
        st.rerun()

# a sample button sets the question on the next run (text_input value can't change after render)
if "pending" in st.session_state:
    question = st.session_state.pop("pending")
    ask = True

if ask and question.strip():
    with st.spinner("Searching notes and checking passages…"):
        try:
            st.session_state.result = run_crag(question.strip())
            st.session_state.baseline = None
        except Exception as e:  # show a useful message instead of a stack trace
            st.session_state.result = None
            st.error(f"The pipeline stopped: {e}. Check the API keys in .env and that you ran "
                     "`python -m crag.ingest`.")

res = st.session_state.get("result")
if not res:
    st.markdown('<div class="empty">Your answer, its sources and the route it took will show up here.</div>',
                unsafe_allow_html=True)
    st.stop()

show(render_route(res))

left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown(f'<p class="panel-title">Answer to “{html.escape(res["question"])}”</p>'
                f'<div class="answer">{render_answer(res["answer"])}</div>', unsafe_allow_html=True)
    if res.get("context"):
        st.markdown('<p class="panel-title">Sources used</p>' + render_sources(res["context"]),
                    unsafe_allow_html=True)
with right:
    st.markdown('<p class="panel-title">How each passage from your notes was judged</p>'
                + render_slips(res.get("documents", [])), unsafe_allow_html=True)

st.write("")
if st.toggle("Compare with plain RAG (no checking, no web search)"):
    if not st.session_state.get("baseline") or st.session_state.baseline["question"] != res["question"]:
        with st.spinner("Running plain RAG…"):
            st.session_state.baseline = run_baseline(res["question"])
    b = st.session_state.baseline
    st.markdown(
        f'<div class="compare"><p class="panel-title">Plain RAG always answers from the top '
        f'{len(b["documents"])} passages, useful or not · {b["latency_s"]} s</p>'
        f'<div class="answer">{render_answer(b["answer"])}</div></div>',
        unsafe_allow_html=True,
    )
