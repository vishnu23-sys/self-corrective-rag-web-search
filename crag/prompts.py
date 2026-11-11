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

# ---------------------------------------------------------------------------
# Grader prompt variants (compared in eval/prompt_experiment.py).
# Pick the one the app uses with GRADER_VARIANT in .env.
#
#   zero_shot : instruction + label definitions only (GRADER_SYSTEM above)
#   few_shot  : same, plus 3 worked examples. The examples are deliberately from
#               an unrelated domain so they can't leak answers to the test set.
#   cot       : same as zero-shot, but the model writes a short reasoning note
#               before the label (chain-of-thought), via a "reasoning" field
#               that comes BEFORE "grade" in the output schema.
# ---------------------------------------------------------------------------

GRADER_FEW_SHOT_EXAMPLES = """
Examples:

Question: What gas do plants absorb during photosynthesis?
Chunk: "During photosynthesis, plants take in carbon dioxide from the air and release oxygen."
grade: relevant   (the chunk states the answer directly)

Question: In what year did the Eiffel Tower open to the public?
Chunk: "The Eiffel Tower is a wrought-iron lattice tower in Paris, designed by Gustave Eiffel's company."
grade: partial    (right subject, but the opening year is not given)

Question: What is the boiling point of water at sea level?
Chunk: "The Great Wall of China stretches across northern China for thousands of kilometres."
grade: irrelevant (different subject entirely)
"""

GRADER_COT_SUFFIX = """
Before grading, think briefly in the "reasoning" field (1-3 sentences):
what exact fact does the question need, and does the chunk state that fact,
only touch the topic, or not relate at all? Then give the grade."""

GRADER_BATCH_SYSTEM = """You are a strict relevance grader for a retrieval system.
Given a user question and SEVERAL numbered document chunks, decide for EACH chunk how useful
it is for answering the question. Grade every chunk independently.

- "relevant":   the chunk directly contains the information needed to answer.
- "partial":    the chunk is on the right topic but does not fully answer the question.
- "irrelevant": the chunk does not help answer the question.

Judge only by each chunk's content. Do not use outside knowledge.
Return exactly one grade per chunk, in chunk order."""

GRADER_BATCH_HUMAN = """Question: {question}

{chunks}"""

# Each variant: system prompt, whether the model writes reasoning first (CoT),
# and whether all chunks are graded in ONE call (batch) or one call per chunk.
GRADER_VARIANTS = {
    "zero_shot":      {"system": GRADER_SYSTEM, "reasoning": False, "batch": False},
    "few_shot":       {"system": GRADER_SYSTEM + "\n" + GRADER_FEW_SHOT_EXAMPLES, "reasoning": False, "batch": False},
    "cot":            {"system": GRADER_SYSTEM + "\n" + GRADER_COT_SUFFIX, "reasoning": True, "batch": False},
    #   few_shot_cot   : examples AND reasoning -- is combining them worth the extra tokens?
    "few_shot_cot":   {"system": GRADER_SYSTEM + "\n" + GRADER_FEW_SHOT_EXAMPLES + "\n" + GRADER_COT_SUFFIX,
                       "reasoning": True, "batch": False},
    #   batch_few_shot : all chunks in ONE call (instructions + examples are sent once, not 4x)
    "batch_few_shot": {"system": GRADER_BATCH_SYSTEM + "\n" + GRADER_FEW_SHOT_EXAMPLES, "reasoning": False, "batch": True},
}

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
