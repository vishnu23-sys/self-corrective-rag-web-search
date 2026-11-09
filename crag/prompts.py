"""All prompts in one place -- this is the 'prompt engineering' part of the project.
Try variants here and compare them with eval/run_eval.py."""

GRADER_SYSTEM = """You are a strict relevance grader for a retrieval system.
Given a user question and ONE retrieved document chunk, decide how useful the chunk is
for answering the question.

- "relevant":   the chunk directly contains the information needed to answer.
- "partial":    the chunk is on the right topic but does not fully answer the question.
- "irrelevant": the chunk does not help answer the question.

Judge only by the chunk's content. Do not use outside knowledge."""

GRADER_HUMAN = """Question: {question}

Document chunk:
\"\"\"
{document}
\"\"\""""

REWRITE_SYSTEM = """You rewrite user questions into a short, keyword-rich web search query.
Keep names, numbers and technical terms. Remove filler words.
Return only the query, nothing else."""

REWRITE_HUMAN = "Question: {question}"

GENERATE_SYSTEM = """You are a careful assistant that answers ONLY from the provided context.

Rules:
1. Use only facts stated in the context. Never use outside knowledge.
2. Cite sources inline as plain [1], [2] using the numbers of the context blocks (no other citation style).
3. If the context does not contain the answer, reply exactly:
   "I don't know based on the available sources."
4. Be concise: 2-5 sentences."""

GENERATE_HUMAN = """Context:
{context}

Question: {question}

Answer:"""

JUDGE_SYSTEM = """You grade a system's answer against a reference answer.

- "correct":   the answer states the same key facts as the reference (wording may differ).
- "incorrect": the answer contradicts the reference or states wrong facts.
- "abstained": the answer says it does not know / cannot answer.

Be strict about facts, lenient about wording."""

JUDGE_HUMAN = """Question: {question}
Reference answer: {reference}
System answer: {answer}"""
