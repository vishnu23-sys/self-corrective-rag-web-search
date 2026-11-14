# Prompt-optimization experiment: relevance grader

_Generated 2026-11-11 09:14 by `python -m eval.prompt_experiment`. 21 questions; every setup grades the same retrieved chunks._

A **setup** is a grader prompt variant plus the model that runs it. The grader labels each retrieved chunk *relevant / partial / irrelevant*, and those labels pick the route. A route counts as correct when it matches the question type: answerable from the notes → CORRECT, partly covered → AMBIGUOUS, not in the notes → INCORRECT.

## Overall

| Setup | Runs | Route accuracy | Spread across runs | Tokens / question | vs zero-shot | LLM calls / question |
|---|---|---|---|---|---|---|
| zero_shot @ gpt-oss-20b | 1 | 95% | - | 1753 | 1.00x | 4 |
| few_shot @ gpt-oss-20b | 1 | 90% | - | 2309 | 1.31x | 4 |
| batch_few_shot @ gpt-oss-20b | 1 | 95% | - | 1104 | 0.63x | 1 |
| zero_shot @ gpt-oss-120b | 1 | 95% | - | 1758 | 1.00x | 4 |
| few_shot @ gpt-oss-120b | 1 | 100% | - | 2328 | 1.32x | 4 |
| cot @ gpt-oss-120b | 1 | 100% | - | 2261 | 1.29x | 4 |
| few_shot_cot @ gpt-oss-120b | 1 | 100% | - | 2818 | 1.60x | 4 |
| batch_few_shot @ gpt-oss-120b | 1 | 100% | - | 1136 | 0.65x | 1 |

## Route accuracy by question type

| Setup | in_kb | partial | out_of_kb |
|---|---|---|---|
| zero_shot @ gpt-oss-20b | 100% | 80% | 100% |
| few_shot @ gpt-oss-20b | 100% | 60% | 100% |
| batch_few_shot @ gpt-oss-20b | 100% | 80% | 100% |
| zero_shot @ gpt-oss-120b | 100% | 80% | 100% |
| few_shot @ gpt-oss-120b | 100% | 100% | 100% |
| cot @ gpt-oss-120b | 100% | 100% | 100% |
| few_shot_cot @ gpt-oss-120b | 100% | 100% | 100% |
| batch_few_shot @ gpt-oss-120b | 100% | 100% | 100% |

## Confusion matrices (rows = expected route, columns = chosen route; all runs)

**zero_shot @ gpt-oss-20b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 4 | 1 |
| INCORRECT | 0 | 0 | 6 |

**few_shot @ gpt-oss-20b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 3 | 2 |
| INCORRECT | 0 | 0 | 6 |

**batch_few_shot @ gpt-oss-20b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 4 | 1 |
| INCORRECT | 0 | 0 | 6 |

**zero_shot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 4 | 1 |
| INCORRECT | 0 | 0 | 6 |

**few_shot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

**cot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

**few_shot_cot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

**batch_few_shot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 10 | 0 | 0 |
| AMBIGUOUS | 0 | 5 | 0 |
| INCORRECT | 0 | 0 | 6 |

## Misrouted questions

| Setup | Run | Question | Expected | Chosen | Chunk grades |
|---|---|---|---|---|---|
| batch_few_shot @ gpt-oss-20b | 1 | Which company originally developed the FAISS library? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| few_shot @ gpt-oss-20b | 1 | Which company originally developed the FAISS library? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| few_shot @ gpt-oss-20b | 1 | Who proposed the ReAct prompting framework and in what year? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | Which company originally developed the FAISS library? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-20b | 1 | Who proposed the ReAct prompting framework and in what year? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |

_No human chunk labels yet: run `--make-label-sheet`, fill in `eval/passage_labels.csv`, then `--report-only` to add chunk-label accuracy._
