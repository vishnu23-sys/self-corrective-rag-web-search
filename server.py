"""Web server for the React demo UI.

Run:   python -m uvicorn server:app --port 8000      then open http://localhost:8000

- POST /api/ask   streams the CRAG pipeline as newline-delimited JSON events
- GET  /api/meta  dataset / model info and sample questions
- /               the built React app from web/dist (rebuild with: cd web && npm run build)
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from crag import config
from crag.graph import run_baseline, stream_crag

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "web" / "dist"

app = FastAPI(title="Corrective RAG")

# one sample per route, taken from the real test set (eval/questions.json)
SAMPLES = [
    {"label": "What is algorithmic bias?", "question": "How does the report define algorithmic bias?", "route": "CORRECT"},
    {"label": "Who released ChatGPT, and when?",
     "question": "Which company released ChatGPT, and when was it first released to the public?", "route": "AMBIGUOUS"},
    {"label": "Who painted the Mona Lisa?", "question": "Who painted the Mona Lisa?", "route": "INCORRECT"},
]


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def _doc(d: dict, limit: int = 700) -> dict:
    return {"id": d.get("id", ""), "source": str(d.get("source", "")), "score": d.get("score"),
            "content": (d.get("content") or "")[:limit]}


def _friendly(err: Exception) -> str:
    msg = str(err)
    if "rate_limit" in msg or "429" in msg:
        return "Groq's free-tier rate limit was hit. Wait a minute and ask again."
    if "403" in msg or "Access denied" in msg:
        return "Groq blocked the request from this network. Turn off the VPN and try again."
    if "api_key" in msg.lower() or "401" in msg:
        return "An API key is missing or invalid. Check the .env file."
    return "The pipeline stopped. Check the .env keys, the network, and that `python -m crag.ingest` has been run."


def _events(question: str):
    def line(obj: dict) -> str:
        return json.dumps(obj, ensure_ascii=False) + "\n"

    try:
        for ev in stream_crag(question):
            kind = ev[0]
            if kind == "token":
                yield line({"type": "token", "text": ev[1]})
            elif kind == "step":
                node, state = ev[1], ev[2]
                if node == "retrieve":
                    yield line({"type": "retrieved", "documents": [_doc(d) for d in state.get("documents", [])]})
                elif node == "grade":
                    yield line({"type": "graded", "action": state.get("action"),
                                "grades": [d.get("grade") for d in state.get("documents", [])]})
                elif node == "rewrite":
                    yield line({"type": "rewritten", "query": state.get("search_query", "")})
                elif node == "web_search":
                    yield line({"type": "web", "results": [_doc(r, 300) for r in state.get("web_results", [])]})
            elif kind == "done":
                state = ev[1]
                yield line({
                    "type": "done",
                    "answer": state.get("answer", ""),
                    "action": state.get("action"),
                    "latency_s": state.get("latency_s"),
                    "sources": [{"source": str(c.get("source", "")), "id": c.get("id", ""),
                                 "kind": "web" if str(c.get("source", "")).startswith("http") else "report"}
                                for c in state.get("context", [])],
                })
    except Exception as e:  # send a readable message instead of dropping the connection
        yield line({"type": "error", "message": _friendly(e), "detail": str(e)[:600]})


@app.post("/api/ask")
def ask(body: Ask):
    return StreamingResponse(_events(body.question.strip()), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/baseline")
async def baseline(body: Ask):
    """Plain RAG for the compare view: top-k passages straight into the LLM, no grading, no web."""
    try:
        res = await run_in_threadpool(run_baseline, body.question.strip())
    except Exception as e:
        return JSONResponse(status_code=502, content={"message": _friendly(e)})
    return {
        "answer": res.get("answer", ""),
        "latency_s": res.get("latency_s"),
        "sources": [{"source": str(c.get("source", "")), "id": c.get("id", ""), "kind": "report"}
                    for c in res.get("context", [])],
    }


@app.get("/api/meta")
def meta():
    return {
        "dataset": "AI and the Future of Teaching and Learning",
        "dataset_detail": "US Department of Education, 2023, 71 pages",
        "model": config.GROQ_MODEL if config.LLM_PROVIDER == "groq" else config.GEMINI_MODEL,
        "grader": config.GRADER_VARIANT,
        "top_k": config.TOP_K,
        "samples": SAMPLES,
    }


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
