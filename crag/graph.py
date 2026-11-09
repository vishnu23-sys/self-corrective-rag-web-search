"""Corrective RAG (CRAG) as a LangGraph state machine.

Flow (based on Yan et al., 2024, "Corrective Retrieval Augmented Generation"):

    retrieve -> grade each chunk -> decide action
        CORRECT   (>=1 chunk relevant)       -> generate from relevant chunks
        INCORRECT (all chunks irrelevant)    -> rewrite query -> web search -> generate
        AMBIGUOUS (only partial matches)     -> rewrite query -> web search -> generate
                                                 from partial chunks + web results
"""
import time
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from crag import config, prompts
from crag.llm import get_llm
from crag.retriever import retrieve
from crag.websearch import web_search

Grade = Literal["relevant", "partial", "irrelevant"]
Action = Literal["CORRECT", "AMBIGUOUS", "INCORRECT"]


class GradeOut(BaseModel):
    grade: Grade = Field(description="relevant, partial or irrelevant")


class GradeWithReasoning(BaseModel):
    # field order matters: the model writes its reasoning first, then the grade
    reasoning: str = Field(description="1-3 sentences: what fact is needed and whether the chunk states it")
    grade: Grade = Field(description="relevant, partial or irrelevant")


class CragState(TypedDict, total=False):
    question: str
    documents: list[dict]   # retrieved chunks, each gets a "grade" key
    action: Action
    search_query: str
    web_results: list[dict]
    context: list[dict]     # what is finally passed to the generator
    answer: str
    trace: list[str]        # human-readable log of steps (shown in UI)


# ---------------------------------------------------------------- helpers

def _format_context(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{i}] (source: {c['source']})\n{c['content']}" for i, c in enumerate(chunks, 1))


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I don't know based on the available sources."
    chain = ChatPromptTemplate.from_messages(
        [("system", prompts.GENERATE_SYSTEM), ("human", prompts.GENERATE_HUMAN)]
    ) | get_llm()
    return chain.invoke({"context": _format_context(chunks), "question": question}).content.strip()


# ---------------------------------------------------------------- nodes

def node_retrieve(state: CragState) -> CragState:
    docs = retrieve(state["question"])
    return {"documents": docs, "trace": [f"Retrieved {len(docs)} chunks from the vector store"]}


def node_grade(state: CragState) -> CragState:
    variant = config.GRADER_VARIANT
    schema = GradeWithReasoning if variant == "cot" else GradeOut
    chain = ChatPromptTemplate.from_messages(
        [("system", prompts.GRADER_VARIANTS[variant]), ("human", prompts.GRADER_HUMAN)]
    ) | get_llm().with_structured_output(schema)

    # grade all chunks in parallel (one LLM call each)
    outs = chain.batch([{"question": state["question"], "document": d["content"]} for d in state["documents"]])
    graded = [{**d, "grade": o.grade} for d, o in zip(state["documents"], outs)]

    grades = [d["grade"] for d in graded]
    if "relevant" in grades:
        action: Action = "CORRECT"
    elif "partial" in grades:
        action = "AMBIGUOUS"
    else:
        action = "INCORRECT"

    summary = ", ".join(f"{g}" for g in grades) or "no chunks"
    return {
        "documents": graded,
        "action": action,
        "trace": state["trace"] + [f"Grades: {summary} -> action = {action}"],
    }


def node_rewrite(state: CragState) -> CragState:
    chain = ChatPromptTemplate.from_messages(
        [("system", prompts.REWRITE_SYSTEM), ("human", prompts.REWRITE_HUMAN)]
    ) | get_llm()
    q = chain.invoke({"question": state["question"]}).content.strip().strip('"')
    return {"search_query": q, "trace": state["trace"] + [f"Rewrote query for web search: {q!r}"]}


def node_web_search(state: CragState) -> CragState:
    results = web_search(state["search_query"])
    note = f"Web search returned {len(results)} results" if results else "Web search skipped/empty (no TAVILY_API_KEY?)"
    return {"web_results": results, "trace": state["trace"] + [note]}


def node_generate(state: CragState) -> CragState:
    action = state["action"]
    docs = state.get("documents", [])
    if action == "CORRECT":
        context = [d for d in docs if d["grade"] == "relevant"]
    elif action == "AMBIGUOUS":
        context = [d for d in docs if d["grade"] == "partial"] + state.get("web_results", [])
    else:
        context = state.get("web_results", [])
    answer = generate_answer(state["question"], context)
    return {
        "context": context,
        "answer": answer,
        "trace": state["trace"] + [f"Generated answer from {len(context)} context blocks"],
    }


def route_after_grade(state: CragState) -> str:
    return "generate" if state["action"] == "CORRECT" else "rewrite"


# ---------------------------------------------------------------- graph

def build_graph():
    g = StateGraph(CragState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("grade", node_grade)
    g.add_node("rewrite", node_rewrite)
    g.add_node("web_search", node_web_search)
    g.add_node("generate", node_generate)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", route_after_grade, {"generate": "generate", "rewrite": "rewrite"})
    g.add_edge("rewrite", "web_search")
    g.add_edge("web_search", "generate")
    g.add_edge("generate", END)
    return g.compile()


_GRAPH = None


def run_crag(question: str) -> dict:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    t0 = time.perf_counter()
    out = _GRAPH.invoke({"question": question, "trace": []})
    out["latency_s"] = round(time.perf_counter() - t0, 2)
    return out


def run_baseline(question: str) -> dict:
    """Plain RAG: retrieve top-k and generate. No grading, no web fallback."""
    t0 = time.perf_counter()
    docs = retrieve(question)
    answer = generate_answer(question, docs)
    return {
        "question": question,
        "documents": docs,
        "context": docs,
        "answer": answer,
        "action": "BASELINE",
        "latency_s": round(time.perf_counter() - t0, 2),
    }


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    q = " ".join(sys.argv[1:]) or "What is chain-of-thought prompting?"
    res = run_crag(q)
    print("\n".join(res["trace"]))
    print(f"\nAnswer ({res['latency_s']}s):\n{res['answer']}")
