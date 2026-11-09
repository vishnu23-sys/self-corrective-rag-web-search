"""Compare plain RAG (baseline) vs CRAG on eval/questions.json.

Usage:
    python -m eval.run_eval                     # both systems, all questions
    python -m eval.run_eval --limit 3           # quick test
    python -m eval.run_eval --systems crag

Outputs:
    eval/results/results_<timestamp>.csv   one row per (system, question)
    eval/results/summary_<timestamp>.csv   accuracy / hallucination / latency per system
"""
import argparse
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from crag import config, prompts
from crag.graph import run_baseline, run_crag
from crag.llm import get_llm

HERE = Path(__file__).resolve().parent
SYSTEMS = {"baseline": run_baseline, "crag": run_crag}


class JudgeOut(BaseModel):
    verdict: Literal["correct", "incorrect", "abstained"]


def judge(question: str, reference: str, answer: str) -> str:
    chain = ChatPromptTemplate.from_messages(
        [("system", prompts.JUDGE_SYSTEM), ("human", prompts.JUDGE_HUMAN)]
    ) | get_llm(config.JUDGE_PROVIDER).with_structured_output(JudgeOut)
    return chain.invoke({"question": question, "reference": reference, "answer": answer}).verdict


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), choices=list(SYSTEMS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between questions (free-tier rate limits)")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))[: args.limit]
    rows = []
    for system in args.systems:
        for q in questions:
            try:
                out = SYSTEMS[system](q["question"])
                verdict = judge(q["question"], q["reference"], out["answer"])
                err = ""
            except Exception as e:  # keep going; record the failure
                out, verdict, err = {"answer": "", "action": "", "latency_s": None}, "error", repr(e)
            rows.append({
                "system": system,
                "id": q["id"],
                "type": q.get("type", ""),
                "question": q["question"],
                "reference": q["reference"],
                "answer": out["answer"],
                "action": out.get("action", ""),
                "used_web": bool(out.get("web_results")),
                "latency_s": out.get("latency_s"),
                "verdict": verdict,
                "error": err,
            })
            print(f"[{system:8}] {q['id']:>4} {out.get('action', ''):10} -> {verdict}")
            time.sleep(args.sleep)

    df = pd.DataFrame(rows)
    summary = df.groupby("system").agg(
        n=("id", "count"),
        accuracy=("verdict", lambda v: (v == "correct").mean()),
        hallucination_rate=("verdict", lambda v: (v == "incorrect").mean()),
        abstain_rate=("verdict", lambda v: (v == "abstained").mean()),
        web_search_rate=("used_web", "mean"),
        avg_latency_s=("latency_s", "mean"),
    ).round(3)
    by_type = df.pivot_table(index="system", columns="type", values="verdict",
                             aggfunc=lambda v: (v == "correct").mean()).round(3)

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(out_dir / f"results_{stamp}.csv", index=False)
    summary.to_csv(out_dir / f"summary_{stamp}.csv")

    print("\n=== Summary ===\n", summary.to_string())
    print("\n=== Accuracy by question type ===\n", by_type.to_string())
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
