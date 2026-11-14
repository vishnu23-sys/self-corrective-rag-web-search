"""Prompt-optimization experiment: compare relevance-grader setups.

A "setup" = prompt variant (crag/prompts.py GRADER_VARIANTS) + grader model.
The grader decides the route (CORRECT / AMBIGUOUS / INCORRECT), so we measure:
  * route accuracy   - did the setup pick the route the question type calls for?
                         in_kb -> CORRECT, partial -> AMBIGUOUS, out_of_kb -> INCORRECT
  * label accuracy   - % of chunk labels that match a human's labels
                         (only if eval/passage_labels.csv has been filled in)
  * grader tokens    - LLM tokens spent grading one question (cost)
  * LLM calls        - grader calls per question (batch = 1, otherwise one per chunk)
  * spread           - with --repeats N, the min-max route accuracy across runs
With --full it also runs the whole pipeline and has the judge score the final answer.

Retrieval is done once per question and reused, so every setup grades the SAME chunks.
Results are appended to eval/results/prompt_experiment.jsonl; if a rate limit stops the
run, run the same command again and it continues where it left off.

Usage:
    python -m eval.prompt_experiment                                  # all variants, main model
    python -m eval.prompt_experiment --variants few_shot batch_few_shot
    python -m eval.prompt_experiment --grader-model openai/gpt-oss-20b --variants few_shot
    python -m eval.prompt_experiment --repeats 3                      # 3 runs per setup
    python -m eval.prompt_experiment --report-only                    # rebuild report from saved rows
    python -m eval.prompt_experiment --make-label-sheet               # CSV for human chunk labels
    python -m eval.prompt_experiment --fresh                          # discard saved rows first
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from langchain_core.callbacks import get_usage_metadata_callback

from crag import config, prompts
from crag.graph import grade_chunks, route_from_grades, run_crag
from crag.retriever import retrieve

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
LABELS = HERE / "passage_labels.csv"
REPORT = HERE.parent / "docs" / "prompt_experiment_results.md"
EXPECTED_ROUTE = {"in_kb": "CORRECT", "partial": "AMBIGUOUS", "out_of_kb": "INCORRECT"}
GRADES = {"relevant", "partial", "irrelevant"}


def main_model() -> str:
    return config.GROQ_MODEL if config.LLM_PROVIDER == "groq" else config.GEMINI_MODEL


def short(model: str) -> str:
    return model.split("/")[-1]


# ------------------------------------------------------------------ human labels

def make_label_sheet(questions: list[dict]):
    """Write a CSV with every retrieved chunk per question; a human fills in human_label."""
    existing = {}
    if LABELS.exists():
        with LABELS.open(encoding="utf-8-sig", newline="") as f:
            existing = {(r["question_id"], r["chunk_id"]): r["human_label"] for r in csv.DictReader(f)}
    with LABELS.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig so Excel opens it cleanly
        w = csv.writer(f)
        w.writerow(["question_id", "type", "question", "rank", "chunk_id", "chunk_text", "human_label"])
        for q in questions:
            for rank, d in enumerate(retrieve(q["question"]), 1):
                w.writerow([q["id"], q["type"], q["question"], rank, d["id"],
                            d["content"].replace("\n", " "), existing.get((q["id"], d["id"]), "")])
    print(f"Wrote {LABELS}\nFill human_label with relevant / partial / irrelevant, save, then rerun with --report-only.")


def load_labels() -> dict:
    if not LABELS.exists():
        return {}
    with LABELS.open(encoding="utf-8-sig", newline="") as f:
        return {(r["question_id"], r["chunk_id"]): r["human_label"].strip().lower()
                for r in csv.DictReader(f) if r["human_label"].strip().lower() in GRADES}


# ------------------------------------------------------------------ run

def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", default=list(prompts.GRADER_VARIANTS),
                    choices=list(prompts.GRADER_VARIANTS))
    ap.add_argument("--grader-model", default=None, help="model used for grading (default: GROQ_MODEL)")
    ap.add_argument("--repeats", type=int, default=1, help="runs per setup (to measure run-to-run spread)")
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    ap.add_argument("--full", action="store_true", help="also run the full pipeline and judge answers")
    ap.add_argument("--fresh", action="store_true", help="discard all saved rows first")
    ap.add_argument("--report-only", action="store_true", help="just rebuild the report from saved rows")
    ap.add_argument("--make-label-sheet", action="store_true", help="write eval/passage_labels.csv")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.make_label_sheet:
        return make_label_sheet(questions)

    RESULTS.mkdir(exist_ok=True)
    raw_path = RESULTS / f"prompt_experiment{'_full' if args.full else ''}.jsonl"
    if args.fresh and raw_path.exists():
        raw_path.unlink()
    rows = load_rows(raw_path)

    if not args.report_only:
        model = args.grader_model or main_model()
        done = {(r["variant"], r["grader_model"], r["run"], r["id"]) for r in rows}
        todo = len(args.variants) * args.repeats * len(questions)
        print(f"Grader model: {model} | variants: {args.variants} | {len(questions)} questions x {args.repeats} run(s)")
        print(f"Saved rows: {raw_path} ({len(rows)} rows, {todo} needed for this run)\n")

        chunks_cache: dict[str, list[dict]] = {}
        jobs = [(run, v, q) for run in range(1, args.repeats + 1) for v in args.variants for q in questions]
        with raw_path.open("a", encoding="utf-8") as out:
            for run, variant, q in jobs:
                if (variant, model, run, q["id"]) in done:
                    continue
                if q["id"] not in chunks_cache:
                    chunks_cache[q["id"]] = retrieve(q["question"])
                docs = chunks_cache[q["id"]]
                try:
                    with get_usage_metadata_callback() as cb:
                        t0 = time.perf_counter()
                        grades = grade_chunks(q["question"], docs, variant=variant, model=model)
                        latency = time.perf_counter() - t0
                except Exception as e:
                    print(f"  stopped at {variant}/{q['id']}: {e!r}")
                    print("  Run the same command again to resume.")
                    break
                route = route_from_grades(grades)
                row = {
                    "variant": variant, "grader_model": model, "run": run,
                    "id": q["id"], "type": q["type"], "question": q["question"],
                    "chunk_ids": [d["id"] for d in docs], "grades": grades,
                    "route": route, "expected_route": EXPECTED_ROUTE[q["type"]],
                    "route_ok": route == EXPECTED_ROUTE[q["type"]],
                    "grader_tokens": sum(u.get("total_tokens", 0) for u in cb.usage_metadata.values()),
                    "grader_calls": 1 if prompts.GRADER_VARIANTS[variant]["batch"] else len(docs),
                    "grader_latency_s": round(latency, 2),
                }
                if args.full:
                    from eval.run_eval import judge

                    config.GRADER_VARIANT, config.GRADER_MODEL = variant, model
                    res = run_crag(q["question"])
                    row["answer"] = res["answer"]
                    row["verdict"] = judge(q["question"], q["reference"], res["answer"])
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                rows.append(row)
                print(f"[run {run} {variant:14} {short(model):12}] {q['id']:>4} {q['type']:9} "
                      f"{'ok ' if row['route_ok'] else 'MISS'} {route:9} {row['grader_tokens']:>5} tok"
                      + (f"  answer: {row['verdict']}" if args.full else ""))

    if rows:
        summarise(pd.DataFrame(rows), args.full)


# ------------------------------------------------------------------ report

def summarise(df: pd.DataFrame, full: bool):
    df["setup"] = df["variant"] + " @ " + df["grader_model"].map(short)
    variant_order = list(prompts.GRADER_VARIANTS)
    setups = (df[["setup", "variant", "grader_model"]].drop_duplicates()
              .assign(o=lambda d: d["variant"].map(variant_order.index))
              .sort_values(["grader_model", "o"], ascending=[False, True])["setup"].tolist())

    # human labels -> chunk-level accuracy
    labels = load_labels()

    def label_stats(r):
        pairs = [(g, labels[(r["id"], c)]) for g, c in zip(r["grades"], r.get("chunk_ids", []))
                 if (r["id"], c) in labels]
        return pd.Series({"labelled": len(pairs), "label_hits": sum(g == h for g, h in pairs)})

    if labels:
        df[["labelled", "label_hits"]] = df.apply(label_stats, axis=1)

    per_run = df.groupby(["setup", "run"])["route_ok"].mean()
    g = df.groupby("setup")
    summary = pd.DataFrame({
        "questions": g["id"].nunique(),
        "runs": g["run"].nunique(),
        "route_accuracy": g["route_ok"].mean(),
        "spread": per_run.groupby("setup").agg(lambda s: s.max() - s.min()),
        "avg_tokens": g["grader_tokens"].mean(),
        "llm_calls": g["grader_calls"].mean(),
    }).reindex(setups)
    base_tokens = summary["avg_tokens"].get(f"zero_shot @ {short(df['grader_model'].mode()[0])}")
    summary["tokens_vs_zero_shot"] = summary["avg_tokens"] / base_tokens if base_tokens else float("nan")
    if labels:
        summary["label_accuracy"] = g["label_hits"].sum() / g["labelled"].sum().replace(0, float("nan"))
    if full:
        summary["answer_accuracy"] = g["verdict"].apply(lambda v: (v == "correct").mean())
    by_type = df.pivot_table(index="setup", columns="type", values="route_ok", aggfunc="mean").reindex(setups)
    by_type = by_type[[c for c in ["in_kb", "partial", "out_of_kb"] if c in by_type.columns]]

    pct = lambda x: "-" if pd.isna(x) else f"{x:.0%}"  # noqa: E731
    print("\n=== Grader setups ===")
    print(summary.to_string(formatters={"route_accuracy": pct, "spread": pct, "label_accuracy": pct,
                                         "answer_accuracy": pct, "avg_tokens": "{:.0f}".format,
                                         "llm_calls": "{:.0f}".format, "tokens_vs_zero_shot": "{:.2f}x".format}))
    print("\n=== Route accuracy by question type ===")
    print(by_type.to_string(float_format=pct))

    # ---- markdown report
    n_q = df["id"].nunique()
    lines = [
        "# Prompt-optimization experiment: relevance grader",
        "",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} by `python -m eval.prompt_experiment`. "
        f"{n_q} questions; every setup grades the same retrieved chunks._",
        "",
        "A **setup** is a grader prompt variant plus the model that runs it. The grader labels each retrieved "
        "chunk *relevant / partial / irrelevant*, and those labels pick the route. A route counts as correct "
        "when it matches the question type: answerable from the notes → CORRECT, partly covered → "
        "AMBIGUOUS, not in the notes → INCORRECT.",
        "",
        "## Overall",
        "",
    ]
    cols = ["Setup", "Runs", "Route accuracy", "Spread across runs", "Tokens / question", "vs zero-shot",
            "LLM calls / question"]
    if labels:
        cols.append("Chunk-label accuracy vs human")
    if full:
        cols.append("Answer accuracy")
    lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for s, r in summary.iterrows():
        cells = [s, f"{r.runs:.0f}", pct(r.route_accuracy), pct(r.spread) if r.runs > 1 else "-",
                 f"{r.avg_tokens:.0f}", f"{r.tokens_vs_zero_shot:.2f}x", f"{r.llm_calls:.0f}"]
        if labels:
            cells.append(pct(r.label_accuracy))
        if full:
            cells.append(pct(r.answer_accuracy))
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## Route accuracy by question type", "",
              "| Setup | " + " | ".join(by_type.columns) + " |", "|---|" + "---|" * len(by_type.columns)]
    for s, r in by_type.iterrows():
        lines.append(f"| {s} | " + " | ".join(pct(x) for x in r) + " |")

    lines += ["", "## Confusion matrices (rows = expected route, columns = chosen route; all runs)", ""]
    order = ["CORRECT", "AMBIGUOUS", "INCORRECT"]
    for s in setups:
        cm = pd.crosstab(df[df.setup == s]["expected_route"], df[df.setup == s]["route"]).reindex(
            index=order, columns=order, fill_value=0)
        lines += [f"**{s}**", "", "| expected \\ chosen | " + " | ".join(order) + " |", "|---|---|---|---|"]
        lines += [f"| {i} | " + " | ".join(str(x) for x in row) + " |" for i, row in cm.iterrows()]
        lines.append("")

    misses = df[~df["route_ok"]].sort_values(["setup", "id", "run"])
    lines += ["## Misrouted questions", "", "| Setup | Run | Question | Expected | Chosen | Chunk grades |",
              "|---|---|---|---|---|---|"]
    for _, r in misses.iterrows():
        lines.append(f"| {r.setup} | {r.run} | {r.question} | {r.expected_route} | {r.route} | {', '.join(r.grades)} |")
    if not labels:
        lines += ["", "_No human chunk labels yet: run `--make-label-sheet`, fill in `eval/passage_labels.csv`, "
                      "then `--report-only` to add chunk-label accuracy._"]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # machine-readable summary for the app's Results tab
    part = by_type["partial"] if "partial" in by_type.columns else pd.Series(dtype=float)
    (REPORT.parent / "prompt_experiment_summary.json").write_text(json.dumps({
        "generated": f"{datetime.now():%Y-%m-%d %H:%M}",
        "questions": int(n_q),
        "setups": [{
            "setup": s, "variant": s.split(" @ ")[0], "model": s.split(" @ ")[1],
            "runs": int(r.runs), "route_accuracy": round(float(r.route_accuracy), 4),
            "partial_accuracy": None if pd.isna(part.get(s)) else round(float(part.get(s)), 4),
            "avg_tokens": round(float(r.avg_tokens)), "llm_calls": int(r.llm_calls),
        } for s, r in summary.iterrows()],
    }, indent=2), encoding="utf-8")
    print(f"\nReport written to {REPORT}")


if __name__ == "__main__":
    main()
