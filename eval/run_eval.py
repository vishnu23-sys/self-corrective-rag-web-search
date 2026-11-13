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
from crag.llm import get_judge_llm

HERE = Path(__file__).resolve().parent
SYSTEMS = {"baseline": run_baseline, "crag": run_crag}


class JudgeOut(BaseModel):
    verdict: Literal["correct", "incorrect", "abstained"]


def judge(question: str, reference: str, answer: str) -> str:
    chain = ChatPromptTemplate.from_messages(
        [("system", prompts.JUDGE_SYSTEM), ("human", prompts.JUDGE_HUMAN)]
    ) | get_judge_llm().with_structured_output(JudgeOut)
    return chain.invoke({"question": question, "reference": reference, "answer": answer}).verdict


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    ap.add_argument("--systems", nargs="+", default=list(SYSTEMS), choices=list(SYSTEMS))
    ap.add_argument("--types", nargs="+", default=None, help="only these question types (in_kb partial out_of_kb)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between questions (free-tier rate limits)")
    ap.add_argument("--fresh", action="store_true", help="discard saved progress and start over")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.types:
        questions = [q for q in questions if q.get("type") in args.types]
    questions = questions[: args.limit]

    # Progress is saved after every question. If a rate limit stops the run, run the same
    # command again: finished questions are skipped and failed ones are retried.
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    progress = out_dir / "run_eval_progress.jsonl"
    if args.fresh and progress.exists():
        progress.unlink()
    saved = {}
    if progress.exists():
        for line in progress.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            saved[(r["system"], r["id"])] = r  # later lines overwrite earlier ones (retries)

    with progress.open("a", encoding="utf-8") as f:
        for system in args.systems:
            for q in questions:
                if saved.get((system, q["id"]), {}).get("verdict") not in (None, "error"):
                    continue
                try:
                    out = SYSTEMS[system](q["question"])
                    verdict = judge(q["question"], q["reference"], out["answer"])
                    err = ""
                except Exception as e:  # record the failure; it is retried on the next run
                    out, verdict, err = {"answer": "", "action": "", "latency_s": None}, "error", repr(e)
                row = {
                    "system": system,
                    "id": q["id"],
                    "type": q.get("type", ""),
                    "question": q["question"],
                    "reference": q["reference"],
                    "answer": out["answer"],
                    "action": out.get("action", ""),
                    "used_web": bool(out.get("web_results")),
                    "latency_s": out.get("latency_s"),
                    "grader": f"{config.GRADER_VARIANT} @ {config.GRADER_MODEL or config.GROQ_MODEL}" if system == "crag" else "",
                    "verdict": verdict,
                    "error": err,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                saved[(system, q["id"])] = row
                print(f"[{system:8}] {q['id']:>4} {out.get('action', ''):10} -> {verdict}")
                if err and ("rate_limit" in err or "RateLimit" in err):
                    print("\nStopped: API rate limit (probably the daily token limit). Progress is saved;\n"
                          "run the same command later (or with another API key) to continue.")
                    break
                time.sleep(args.sleep)
            else:
                continue
            break

    ids = {q["id"] for q in questions}
    df = pd.DataFrame([r for (s_, i), r in saved.items() if s_ in args.systems and i in ids])
    if df.empty:
        return
    summary = df.groupby("system").agg(
        n=("id", "count"),
        accuracy=("verdict", lambda v: (v == "correct").mean()),
        hallucination_rate=("verdict", lambda v: (v == "incorrect").mean()),
        abstain_rate=("verdict", lambda v: (v == "abstained").mean()),
        errors=("verdict", lambda v: int((v == "error").sum())),
        web_search_rate=("used_web", "mean"),
        avg_latency_s=("latency_s", "mean"),
    ).round(3)
    by_type = df.pivot_table(index="system", columns="type", values="verdict",
                             aggfunc=lambda v: (v == "correct").mean()).round(3)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(out_dir / f"results_{stamp}.csv", index=False)
    summary.to_csv(out_dir / f"summary_{stamp}.csv")

    print("\n=== Summary ===\n", summary.to_string())
    print("\n=== Accuracy by question type ===\n", by_type.to_string())
    if summary["errors"].sum():
        print(f"\nWARNING: {summary['errors'].sum()} question(s) failed and count as wrong above. "
              "Run the same command again to retry them before using these numbers.")
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
