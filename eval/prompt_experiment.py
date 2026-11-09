"""Prompt-optimization experiment: compare relevance-grader prompt variants.

The grader decides the route (CORRECT / AMBIGUOUS / INCORRECT), so we measure:
  * route accuracy   - did the variant pick the route the question type calls for?
                         in_kb -> CORRECT, partial -> AMBIGUOUS, out_of_kb -> INCORRECT
  * grader tokens    - LLM tokens spent grading one question (cost)
  * grader latency   - seconds spent grading one question
With --full it also runs the whole pipeline and has the judge score the final answer.

Retrieval is done once per question and reused, so every variant grades the SAME chunks
(only the prompt changes). Results are appended to a .jsonl file, so if a rate limit
stops the run, just run the same command again and it continues where it left off.

Usage:
    python -m eval.prompt_experiment                         # all variants, routing only
    python -m eval.prompt_experiment --variants zero_shot cot
    python -m eval.prompt_experiment --full                  # + end-to-end answer accuracy
    python -m eval.prompt_experiment --fresh                 # ignore earlier results
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from langchain_core.callbacks import get_usage_metadata_callback

from crag import config, prompts
from crag.graph import node_grade, run_crag
from crag.retriever import retrieve

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
REPORT = HERE.parent / "docs" / "prompt_experiment_results.md"
EXPECTED_ROUTE = {"in_kb": "CORRECT", "partial": "AMBIGUOUS", "out_of_kb": "INCORRECT"}


def tokens(cb) -> int:
    return sum(u.get("total_tokens", 0) for u in cb.usage_metadata.values())


def load_done(path: Path) -> dict:
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[(r["variant"], r["id"])] = r
    return done


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", default=list(prompts.GRADER_VARIANTS),
                    choices=list(prompts.GRADER_VARIANTS))
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    ap.add_argument("--full", action="store_true", help="also run the full pipeline and judge answers")
    ap.add_argument("--fresh", action="store_true", help="discard earlier results for this model")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    RESULTS.mkdir(exist_ok=True)
    model = config.GROQ_MODEL if config.LLM_PROVIDER == "groq" else config.GEMINI_MODEL
    raw_path = RESULTS / f"prompt_experiment_{model.replace('/', '_')}{'_full' if args.full else ''}.jsonl"
    if args.fresh and raw_path.exists():
        raw_path.unlink()
    done = load_done(raw_path)

    print(f"Model: {model} | variants: {args.variants} | {len(questions)} questions")
    print(f"Raw results: {raw_path} ({len(done)} already done)\n")

    chunks_cache: dict[str, list[dict]] = {}
    with raw_path.open("a", encoding="utf-8") as out:
        for variant in args.variants:
            config.GRADER_VARIANT = variant
            for q in questions:
                if (variant, q["id"]) in done:
                    continue
                if q["id"] not in chunks_cache:
                    chunks_cache[q["id"]] = retrieve(q["question"])
                docs = chunks_cache[q["id"]]

                try:
                    with get_usage_metadata_callback() as cb:
                        t0 = time.perf_counter()
                        graded = node_grade({"question": q["question"], "documents": docs, "trace": []})
                        latency = time.perf_counter() - t0
                except Exception as e:
                    print(f"  stopped at {variant}/{q['id']}: {e!r}\n  Run the same command again to resume.")
                    return
                row = {
                    "variant": variant, "id": q["id"], "type": q["type"], "question": q["question"],
                    "grades": [d["grade"] for d in graded["documents"]],
                    "route": graded["action"], "expected_route": EXPECTED_ROUTE[q["type"]],
                    "route_ok": graded["action"] == EXPECTED_ROUTE[q["type"]],
                    "grader_tokens": tokens(cb), "grader_latency_s": round(latency, 2),
                }

                if args.full:
                    from eval.run_eval import judge

                    res = run_crag(q["question"])
                    row["answer"] = res["answer"]
                    row["verdict"] = judge(q["question"], q["reference"], res["answer"])

                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done[(variant, q["id"])] = row
                mark = "ok " if row["route_ok"] else "MISS"
                print(f"[{variant:9}] {q['id']:>4} {q['type']:9} {mark} {row['route']:9} "
                      f"(expected {row['expected_route']:9}) {row['grader_tokens']:>5} tok"
                      + (f"  answer: {row['verdict']}" if args.full else ""))

    summarise(pd.DataFrame([r for (v, _), r in done.items() if v in args.variants]), model, args.full)


def summarise(df: pd.DataFrame, model: str, full: bool):
    order = [v for v in prompts.GRADER_VARIANTS if v in df["variant"].unique()]
    summary = df.groupby("variant").agg(
        questions=("id", "count"),
        route_accuracy=("route_ok", "mean"),
        avg_grader_tokens=("grader_tokens", "mean"),
        avg_grader_latency_s=("grader_latency_s", "mean"),
    ).reindex(order)
    if full:
        summary["answer_accuracy"] = df.groupby("variant")["verdict"].apply(lambda v: (v == "correct").mean())
    by_type = df.pivot_table(index="variant", columns="type", values="route_ok", aggfunc="mean").reindex(order)
    by_type = by_type[[c for c in ["in_kb", "partial", "out_of_kb"] if c in by_type.columns]]
    confusion = {
        v: pd.crosstab(g["expected_route"], g["route"]).reindex(
            index=["CORRECT", "AMBIGUOUS", "INCORRECT"], columns=["CORRECT", "AMBIGUOUS", "INCORRECT"], fill_value=0)
        for v, g in df.groupby("variant")
    }
    misses = df[~df["route_ok"]].sort_values(["variant", "id"])

    pct = lambda x: f"{x:.0%}"  # noqa: E731
    print("\n=== Route accuracy and cost per variant ===")
    print(summary.to_string(formatters={"route_accuracy": pct, "answer_accuracy": pct,
                                         "avg_grader_tokens": "{:.0f}".format,
                                         "avg_grader_latency_s": "{:.2f}".format}))
    print("\n=== Route accuracy by question type ===")
    print(by_type.to_string(float_format=pct))

    # ---- markdown report for the project report / slides
    lines = [
        "# Prompt-optimization experiment: relevance grader",
        "",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} by `python -m eval.prompt_experiment`. "
        f"Model: `{model}`. {df['id'].nunique()} questions, same retrieved chunks for every variant._",
        "",
        "The grader labels each retrieved chunk *relevant / partial / irrelevant*, and those labels pick the "
        "route. A route is counted correct when it matches the question type: answerable from the notes "
        "→ CORRECT, partly covered → AMBIGUOUS, not in the notes → INCORRECT.",
        "",
        "## Overall",
        "",
        "| Variant | Route accuracy | Avg grader tokens / question | Avg grader latency (s) |"
        + (" Answer accuracy |" if full else ""),
        "|---|---|---|---|" + ("---|" if full else ""),
    ]
    for v, r in summary.iterrows():
        lines.append(f"| {v} | {r.route_accuracy:.0%} | {r.avg_grader_tokens:.0f} | {r.avg_grader_latency_s:.2f} |"
                     + (f" {r.answer_accuracy:.0%} |" if full else ""))
    lines += ["", "## Route accuracy by question type", "",
              "| Variant | " + " | ".join(by_type.columns) + " |",
              "|---|" + "---|" * len(by_type.columns)]
    for v, r in by_type.iterrows():
        lines.append(f"| {v} | " + " | ".join(f"{x:.0%}" for x in r) + " |")
    lines += ["", "## Confusion matrices (rows = expected route, columns = chosen route)", ""]
    for v in order:
        cm = confusion[v]
        lines += [f"**{v}**", "", "| expected \\ chosen | " + " | ".join(cm.columns) + " |",
                  "|---|" + "---|" * len(cm.columns)]
        lines += [f"| {i} | " + " | ".join(str(x) for x in row) + " |" for i, row in cm.iterrows()]
        lines.append("")
    lines += ["## Misrouted questions", "", "| Variant | Question | Expected | Chosen | Chunk grades |",
              "|---|---|---|---|---|"]
    for _, r in misses.iterrows():
        lines.append(f"| {r.variant} | {r.question} | {r.expected_route} | {r.route} | {', '.join(r.grades)} |")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written to {REPORT}")


if __name__ == "__main__":
    main()
