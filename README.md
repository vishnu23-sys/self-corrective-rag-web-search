# Self-Corrective RAG (CRAG) with Fallback Web Search and Routing

Mini project for UE24AM343AB5: Prompt Engineering and Optimization for Generative AI (Problem Statement #8).

A question-answering system that **checks its own retrieved context** before answering:

```
question ─► retrieve (ChromaDB) ─► LLM grades each chunk
                                     │
          ┌──────────────────────────┼──────────────────────────┐
     CORRECT                    AMBIGUOUS                   INCORRECT
 (≥1 chunk relevant)      (only partial matches)      (all chunks irrelevant)
          │                          │                          │
          │                  rewrite query                rewrite query
          │                  + web search                 + web search
          ▼                          ▼                          ▼
 answer from relevant     answer from partial chunks    answer from web
 local chunks             + web results                 results only
```

Based on: Yan et al., *Corrective Retrieval Augmented Generation*, 2024 (arXiv:2401.15884).

## Setup (each team member)

Use **Python 3.11 or 3.12** (3.13+/3.14 may not have wheels for ChromaDB/FastEmbed yet).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then put your API keys in .env
```

Free API keys needed:
- **Groq** (LLM): https://console.groq.com/keys, or use **Gemini**: https://aistudio.google.com/apikey and set `LLM_PROVIDER=gemini`
- **Tavily** (web search): https://app.tavily.com

Embeddings run locally (FastEmbed, `BAAI/bge-small-en-v1.5`), no key needed.

**Groq free-tier limit:** about 8,000 tokens per minute per model. One CRAG question uses about 6 LLM calls, so a 50-question evaluation of both systems takes about 20-30 minutes; retries wait out the limit automatically. To go faster, set `JUDGE_PROVIDER=gemini` (each provider has its own limit) or let each teammate use their own key.

## Run

```bash
python -m crag.ingest --reset                 # chunk + embed everything in data/docs/
python -m crag.graph "What is chain-of-thought prompting?"   # one question in the terminal
streamlit run app.py                          # demo UI
python -m eval.run_eval                       # baseline vs CRAG evaluation
python -m eval.prompt_experiment              # compare grader prompts (zero-shot / few-shot / CoT)
```

### Prompt-optimization experiment
The relevance grader decides the route, so its prompt is the main thing we optimize.
`crag/prompts.py` has five versions:

| Variant | Idea |
|---|---|
| `zero_shot` | Instructions only |
| `few_shot` | Plus 3 worked examples from an unrelated domain (no answer leakage) |
| `cot` | Writes 1-3 sentences of reasoning before the label |
| `few_shot_cot` | Examples and reasoning |
| `batch_few_shot` | Few-shot, but all chunks graded in **one** call instead of one per chunk (cost optimization) |

Each can also run on a smaller model (`--grader-model openai/gpt-oss-20b`). `eval/prompt_experiment.py`
grades the same retrieved chunks with every setup and reports route accuracy, tokens and LLM calls
per question, the spread across repeated runs, confusion matrices and (if labelled) agreement with a human.
It writes `docs/prompt_experiment_results.md`, and if it hits a rate limit, running it again resumes where it stopped.

```bash
python -m eval.prompt_experiment                                           # all variants, main model
python -m eval.prompt_experiment --grader-model openai/gpt-oss-20b --variants zero_shot few_shot batch_few_shot
python -m eval.prompt_experiment --repeats 3                               # measure run-to-run noise
python -m eval.prompt_experiment --make-label-sheet                        # CSV for human chunk labels
python -m eval.prompt_experiment --report-only                             # rebuild report after labelling
```
Human labels: run `--make-label-sheet`, open `eval/passage_labels.csv` in Excel, fill `human_label` with
relevant / partial / irrelevant (20+ questions is enough), save, then `--report-only`.
Pick the winner with `GRADER_VARIANT` (and optionally `GRADER_MODEL`) in `.env`.

## Project layout

| Path | What it is | Owner |
|---|---|---|
| `crag/graph.py` | CRAG LangGraph pipeline + plain-RAG baseline | Member 1 |
| `crag/prompts.py` | All prompts (grader, rewriter, generator, judge) | Member 1 |
| `crag/llm.py`, `crag/websearch.py`, `crag/config.py` | LLM / Tavily / settings | Member 1 |
| `crag/ingest.py`, `crag/retriever.py` | Loading, chunking, ChromaDB | Member 2 |
| `data/docs/` | Knowledge base (sample files are placeholders, replace them) | Member 2 |
| `eval/questions.json`, `eval/run_eval.py` | Test set + evaluation | Member 2 |
| `app.py` | Streamlit demo | Member 3 |
| `docs/` | Diagrams, literature survey, report, slides | Member 3 |

## Team task split

### Member 1: Pipeline lead (CRAG logic and integration)
- [ ] Get keys, run the pipeline end to end on the sample docs
- [ ] Tune the grader prompt in `crag/prompts.py`; try 2-3 variants (zero-shot vs few-shot vs CoT grader) and record which routes questions best. **This is the prompt-engineering contribution, so put it in the report.**
- [ ] Optional upgrade: "knowledge refinement" from the CRAG paper (split chunks into sentences, keep only relevant ones before generating)
- [ ] Handle errors and rate limits; keep `main` working for the other two
- [ ] Own the live demo during reviews

### Member 2: Data and evaluation
- [ ] Choose the knowledge base. Pick a domain with 20-50 pages of real documents (e.g. university rules/handbook PDFs, a textbook chapter, or a public dataset). Put files in `data/docs/` and delete the samples.
- [ ] Write **40-60 test questions** in `eval/questions.json`: ~50% answerable from the docs (`in_kb`), ~25% not in the docs (`out_of_kb`), ~25% partly covered (`partial`)
- [ ] Run `python -m eval.run_eval`; produce the results table: accuracy, hallucination rate, abstain rate, web-search rate, latency for baseline vs CRAG
- [ ] Extra experiments: vary `TOP_K` (2/4/6) and `CHUNK_SIZE` (400/800/1200) in `.env`
- [ ] Hand-check ~20 judge verdicts to report how often the LLM judge agrees with a human

### Member 3: Research, design, UI and documents
- [ ] **Literature survey** (R1): CRAG (Yan et al., 2024), RAG (Lewis et al., 2020), Self-RAG (Asai et al., 2023), Chain-of-Thought (Wei et al., 2022), ReAct (Yao et al., 2022), RAGAS (Es et al., 2023), plus 1-2 more
- [ ] **High-level design** (R2): architecture diagram, flowchart of the routing, data-flow diagram (draw.io / Excalidraw), saved in `docs/`
- [ ] Polish `app.py` for the final demo (show route, trace, sources, baseline side by side)
- [ ] **IEEE report** (10 pages, IEEE conference template on Overleaf): Abstract, Introduction, Literature Survey, Methodology, System Design, Experiments, Results, Conclusion, References
- [ ] Slides for each review

### Review checklist
- **R1 (Idea + Literature Survey):** problem, motivation, CRAG idea, 6-8 papers summarised (Member 3)
- **R2 (High-Level Design + Data Collection):** architecture diagrams (Member 3), dataset + test set + ingestion working (Member 2), pipeline running (Member 1)
- **R3 (Final Demo):** live Streamlit demo, baseline-vs-CRAG results table, report submitted
