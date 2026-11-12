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

## Run 2: cheaper setups and a smaller model (2026-11-11)
Same 21 questions and same retrieved chunks. Tokens are grader tokens per question.

| Setup | Route accuracy | Partly-covered questions | Tokens / question | vs zero-shot | LLM calls |
|---|---|---|---|---|---|
| zero-shot, 120b | 95% | 80% | 1,758 | 1.00x | 4 |
| few-shot, 120b | 100% | 100% | 2,328 | 1.32x | 4 |
| CoT, 120b | 100% | 100% | 2,261 | 1.29x | 4 |
| few-shot + CoT, 120b | 100% | 100% | 2,818 | 1.60x | 4 |
| **batch few-shot, 120b** | **100%** | **100%** | **1,136** | **0.65x** | **1** |
| zero-shot, 20b | 95% | 80% | 1,753 | 1.00x | 4 |
| few-shot, 20b | 90% | 60% | 2,309 | 1.31x | 4 |
| batch few-shot, 20b | 95% | 80% | 1,104 | 0.63x | 1 |

**Findings**
1. **Batch grading is the best setup.** Batch few-shot on the 120b model matched the best route
   accuracy (100%) while using **35% fewer tokens than zero-shot**, about **half the tokens of
   per-chunk few-shot**, and **1 LLM call instead of 4**. The instructions and examples are sent once instead of
   once per chunk, so the extra cost of few-shot examples disappears.
2. **Combining techniques didn't help here.** Few-shot + CoT scored the same as either alone
   but cost the most (1.60x). Once the grader is right, extra prompting only adds cost.
3. **The smaller model is worse at the hard cases and doesn't benefit from examples.** On gpt-oss-20b,
   few-shot actually *dropped* to 60% on partly covered questions. Prompt techniques that help a large
   model don't automatically transfer to a small one.
4. **Every error is the same kind:** a partly covered question gets every chunk marked "irrelevant",
   so it goes to web-only (INCORRECT) instead of notes plus web (AMBIGUOUS). No setup ever
   misrouted an answerable or an unanswerable question. The *partial* boundary is the hard part of
   the task, and what the prompt work should focus on.

**Decision:** the app now uses `batch_few_shot` on the 120b model by default (`GRADER_VARIANT`): same
accuracy as the best setup, cheaper, and faster in the demo (1 call instead of 4).

**Caveats:** one run each on 21 easy questions with only 5 partly covered. The differences are 1-2
questions, so treat these as hypotheses to confirm on the real dataset with `--repeats 3`.

## Next steps
1. Rerun with the real knowledge base and the 40-60 question test set:
   `python -m eval.prompt_experiment --fresh`
2. Run `--full` once to see whether better routing actually gives better final answers.
3. Run it 2-3 times, or on a second model, to show the result isn't noise.
4. Set the winner as `GRADER_VARIANT` in `.env`.
