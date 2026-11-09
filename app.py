"""Streamlit demo UI.  Run:  streamlit run app.py
(Member 3 owns this file -- polish it for the final demo.)"""
import streamlit as st

from crag.graph import run_baseline, run_crag

st.set_page_config(page_title="Corrective RAG", page_icon="🔎", layout="wide")
st.title("🔎 Self-Corrective RAG with Web Search Fallback")
st.caption("Retrieve → grade relevance → use local docs, fall back to web search, or combine both.")

ACTION_COLOR = {"CORRECT": "green", "AMBIGUOUS": "orange", "INCORRECT": "red"}

question = st.text_input("Ask a question", placeholder="e.g. What does CRAG do when retrieval fails?")
compare = st.checkbox("Also show plain RAG (baseline) for comparison", value=True)

if st.button("Ask", type="primary") and question.strip():
    cols = st.columns(2) if compare else [st.container()]

    with cols[0]:
        st.subheader("CRAG")
        with st.spinner("Running CRAG..."):
            res = run_crag(question)
        action = res["action"]
        st.markdown(f"**Route:** :{ACTION_COLOR.get(action, 'gray')}[{action}]  ·  ⏱ {res['latency_s']} s")
        st.write(res["answer"])
        with st.expander("Pipeline trace"):
            for step in res["trace"]:
                st.write("•", step)
        with st.expander("Retrieved chunks and grades"):
            for d in res.get("documents", []):
                st.markdown(f"**{d.get('grade', '?')}** · `{d['source']}` · score {d['score']}")
                st.caption(d["content"][:400])
        if res.get("web_results"):
            with st.expander("Web results"):
                for w in res["web_results"]:
                    st.markdown(f"- [{w['source']}]({w['source']})")
                    st.caption(w["content"][:300])

    if compare:
        with cols[1]:
            st.subheader("Plain RAG (baseline)")
            with st.spinner("Running baseline..."):
                base = run_baseline(question)
            st.markdown(f"**Route:** always local docs  ·  ⏱ {base['latency_s']} s")
            st.write(base["answer"])
            with st.expander("Retrieved chunks"):
                for d in base["documents"]:
                    st.markdown(f"`{d['source']}` · score {d['score']}")
                    st.caption(d["content"][:400])
