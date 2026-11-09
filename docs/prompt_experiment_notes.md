# Prompt experiment: findings so far

Raw numbers: [prompt_experiment_results.md](prompt_experiment_results.md) (regenerated on every run).
This file is hand-written interpretation; update it after the run on the real dataset.

## Run 1: sample knowledge base, 21 questions, `openai/gpt-oss-120b` (2026-11-09)

| Variant | Route accuracy | Grader tokens / question |
|---|---|---|
| zero-shot | 95% (20/21) | ~1,760 |
| few-shot | 100% (21/21) | ~2,330 (+32%) |
| chain-of-thought | 100% (21/21) | ~2,260 (+29%) |

**What happened**
- All three versions routed every *answerable* and every *not-in-the-notes* question correctly.
- The only difference was on *partly covered* questions. Zero-shot marked every chunk "irrelevant" for
  "Which company originally developed the FAISS library?", where the notes mention FAISS but not who
  built it. That sent the question to web-only (INCORRECT) instead of notes plus web (AMBIGUOUS).
  Few-shot and CoT both recognised that chunk as "partial".
- Few-shot is the most generous with "partial": it also marked a second chunk partial on q4,
  which didn't change the route.
- Both extra techniques cost about 30% more grader tokens per question.

**How much to trust this**
- The difference is **one question out of 21**, which is within run-to-run noise. The sample
  notes are short and the questions easy, so all versions hit the ceiling.
- Latency includes waiting out Groq's free-tier rate limit (8k tokens/min), so compare **tokens**,
  not seconds, as the cost measure.

**Hypothesis to test on the real dataset**
Adding examples or reasoning helps the grader with the *partial* category, the hardest boundary
because "on topic but missing the fact" is a judgement call. It costs about 30% more tokens. Check
whether the gap grows with real documents and more partial questions (aim for 10+).

## Next steps
1. Rerun with the real knowledge base and the 40-60 question test set:
   `python -m eval.prompt_experiment --fresh`
2. Run `--full` once to see whether better routing actually gives better final answers.
3. Run it 2-3 times, or on a second model, to show the result isn't noise.
4. Set the winner as `GRADER_VARIANT` in `.env`.
