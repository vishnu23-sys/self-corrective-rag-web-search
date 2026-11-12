# Evaluation results: baseline RAG vs CRAG

Knowledge base: US Dept. of Education, *AI and the Future of Teaching and Learning* (2023), 71 pages. Test set: 48 questions (24 in_kb, 12 partial, 12 out_of_kb).

## Overall

| system | n | accuracy | hallucination_rate | abstain_rate | errors | web_search_rate | avg_latency_s |
|---|---|---|---|---|---|---|---|
| baseline | 48 | 0.354 | 0.083 | 0.562 | 0 | 0.0 | 6.802 |
| crag | 48 | 0.625 | 0.083 | 0.021 | 13 | 0.333 | 22.649 |

## Accuracy by question type

| system | in_kb | out_of_kb | partial |
|---|---|---|---|
| baseline | 0.708 | 0.0 | 0.0 |
| crag | 0.792 | 0.0 | 0.917 |
