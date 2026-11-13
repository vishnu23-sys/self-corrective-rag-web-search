# Evaluation results: baseline RAG vs CRAG

Knowledge base: US Dept. of Education, *AI and the Future of Teaching and Learning* (2023), 71 pages, 325 chunks. Test set: 48 questions (24 in_kb, 12 partial, 12 out_of_kb).

Generator and grader model: `openai/gpt-oss-120b` (Groq). CRAG grader: `batch_few_shot`. Judge: same model.

## Overall

| system | n | accuracy | hallucination_rate | abstain_rate | errors | web_search_rate | avg_latency_s |
|---|---|---|---|---|---|---|---|
| baseline | 48 | 0.354 | 0.083 | 0.562 | 0 | 0.0 | 6.802 |
| crag | 48 | **0.938** | **0.021** | 0.042 | 0 | 0.625 | 15.844 |

## Accuracy by question type

| system | in_kb | partial | out_of_kb |
|---|---|---|---|
| baseline | 0.708 | 0.0 | 0.0 |
| crag | **0.875** | **1.0** | **1.0** |

## Notes

- **Rerun of CRAG (2026-11-13).** The first CRAG run (2026-11-12) had 13 errors: it hit the Groq
  daily token limit near the end of the file, so the last 12 questions (all out_of_kb) and one partial
  question failed and were counted as wrong (accuracy 0.625). CRAG was rerun cleanly with zero errors.
  `eval/run_eval.py` now saves after every question and retries failed ones, so this can't silently
  happen again. The baseline numbers are from the first run, which had no errors.
- **Where CRAG still fails: list and summary questions.** All 3 misses are in_kb questions whose answer is
  spread across several pages: the 7 policy recommendations (q20), the 6 desirable characteristics (q21),
  and the electric-bike metaphor (q19). The top 4 retrieved chunks don't contain the whole answer, so the
  grader correctly sees no single complete chunk and the generator says "I don't know". **This is a
  retrieval limit, not a grader mistake.** Try `TOP_K=6` or larger chunks (planned TOP_K and CHUNK_SIZE
  experiments).
- 6 of 24 in_kb questions went to AMBIGUOUS (notes plus web). 3 of those were still answered correctly
  from the combined context.
- Judge quirk: q19's "I don't know" answer was labelled *incorrect* rather than *abstained*, so the
  hallucination rate may be slightly overstated. Worth checking in the human-agreement test of the judge.
- The baseline abstains a lot (56%) because it must answer from the top 4 chunks even when they're
  irrelevant. It never hallucinates much, but it can't answer anything outside the report.
