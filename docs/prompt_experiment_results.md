# Prompt-optimization experiment: relevance grader

_Generated 2026-11-14 19:18 by `python -m eval.prompt_experiment`. 48 questions; every setup grades the same retrieved chunks._

A **setup** is a grader prompt variant plus the model that runs it. The grader labels each retrieved chunk *relevant / partial / irrelevant*, and those labels pick the route. A route counts as correct when it matches the question type: answerable from the notes → CORRECT, partly covered → AMBIGUOUS, not in the notes → INCORRECT.

## Overall

| Setup | Runs | Route accuracy | Spread across runs | Tokens / question | vs zero-shot | LLM calls / question |
|---|---|---|---|---|---|---|
| zero_shot @ gpt-oss-120b | 1 | 83% | - | 1992 | 1.00x | 4 |
| batch_few_shot @ gpt-oss-120b | 1 | 81% | - | 1301 | 0.65x | 1 |

## Route accuracy by question type

| Setup | in_kb | partial | out_of_kb |
|---|---|---|---|
| zero_shot @ gpt-oss-120b | 79% | 75% | 100% |
| batch_few_shot @ gpt-oss-120b | 71% | 83% | 100% |

## Confusion matrices (rows = expected route, columns = chosen route; all runs)

**zero_shot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 19 | 4 | 1 |
| AMBIGUOUS | 0 | 9 | 3 |
| INCORRECT | 0 | 0 | 12 |

**batch_few_shot @ gpt-oss-120b**

| expected \ chosen | CORRECT | AMBIGUOUS | INCORRECT |
|---|---|---|---|
| CORRECT | 17 | 5 | 2 |
| AMBIGUOUS | 0 | 10 | 2 |
| INCORRECT | 0 | 0 | 12 |

## Misrouted questions

| Setup | Run | Question | Expected | Chosen | Chunk grades |
|---|---|---|---|---|---|
| batch_few_shot @ gpt-oss-120b | 1 | According to the McKinsey report cited, how much could AI reduce teachers' weekly preparation time? | CORRECT | AMBIGUOUS | partial, partial, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | What are some ways automated essay scoring systems can be misled? | CORRECT | AMBIGUOUS | partial, irrelevant, partial, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | What metaphor does the report use to describe the kind of AI it wants in education? | CORRECT | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | How many policy recommendations does the report make, and what is the first one? | CORRECT | AMBIGUOUS | partial, partial, partial, partial |
| batch_few_shot @ gpt-oss-120b | 1 | What are the six desirable characteristics of AI models for education listed in the report? | CORRECT | AMBIGUOUS | partial, partial, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | What does the Children's Internet Protection Act (CIPA) require schools and libraries to do? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | What is the Response to Intervention (RTI) framework in schools? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | What are the four foundations the report uses to frame policies for AI in education? | CORRECT | AMBIGUOUS | partial, irrelevant, irrelevant, irrelevant |
| batch_few_shot @ gpt-oss-120b | 1 | How many tiers of evidence does the Elementary and Secondary Education Act (ESEA) define for evaluating educational technology? | CORRECT | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | According to the McKinsey report cited, how much could AI reduce teachers' weekly preparation time? | CORRECT | AMBIGUOUS | partial, partial, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | What are some ways automated essay scoring systems can be misled? | CORRECT | AMBIGUOUS | partial, irrelevant, partial, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | What metaphor does the report use to describe the kind of AI it wants in education? | CORRECT | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | How many policy recommendations does the report make, and what is the first one? | CORRECT | AMBIGUOUS | partial, partial, partial, partial |
| zero_shot @ gpt-oss-120b | 1 | What are the six desirable characteristics of AI models for education listed in the report? | CORRECT | AMBIGUOUS | partial, partial, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | Which company released ChatGPT, and when was it first released to the public? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | Who directed the film '2001: A Space Odyssey'? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |
| zero_shot @ gpt-oss-120b | 1 | What is the Response to Intervention (RTI) framework in schools? | AMBIGUOUS | INCORRECT | irrelevant, irrelevant, irrelevant, irrelevant |

_No human chunk labels yet: run `--make-label-sheet`, fill in `eval/passage_labels.csv`, then `--report-only` to add chunk-label accuracy._
