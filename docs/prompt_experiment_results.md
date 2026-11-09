# Prompt-optimization experiment: relevance grader

_Generated 2026-11-09 18:52 by `python -m eval.prompt_experiment`. Model: `openai/gpt-oss-120b`. 21 questions, same retrieved chunks for every variant._

The grader labels each retrieved chunk *relevant / partial / irrelevant*, and those labels pick the route. A route is counted correct when it matches the question type: answerable from the notes → CORRECT, partly covered → AMBIGUOUS, not in the notes → INCORRECT.

## Overall

| Variant | Route accuracy | Avg grader tokens / question | Avg grader latency (s) |
|---|---|---|---|
| zero_shot | 95% | 1758 | 9.39 |
| few_shot | 100% | 2328 | 12.48 |
| cot | 100% | 2261 | 11.89 |

## Route accuracy by question type

| Variant | in_kb | partial | out_of_kb |
|---|---|---|---|
| zero_shot | 100% | 80% | 100% |
| few_shot | 100% | 100% | 100% |
| cot | 100% | 100% | 100% |

## Confusion matrices (rows = expected route, columns = chosen route)

**zero_shot**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 4 | 1 |
| INCORRECT | 0 | 0 | 6 |

**few_shot**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

**cot**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

## Misrouted questions

| Variant | Question | Expected | Chosen | Chunk grades |
|---|---|---|---|---|
| zero_shot | Which company originally developed the FAISS library? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
