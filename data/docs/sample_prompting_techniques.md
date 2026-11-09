# Prompting Techniques (sample knowledge-base document)

> Placeholder data so the pipeline runs end to end. Replace with your real dataset.

## Zero-shot prompting
Zero-shot prompting gives the model only an instruction and the input, with no worked examples.
It relies entirely on what the model learned during pre-training and instruction tuning.
It is the cheapest approach in tokens but is often less reliable on tasks with a strict output format.

## Few-shot prompting
Few-shot prompting places a small number of input-output examples (typically 2 to 8) in the prompt
before the real input. The examples show the model the expected format and reasoning style.
Performance is sensitive to the choice and order of the examples.

## Chain-of-thought prompting
Chain-of-thought (CoT) prompting asks the model to write out intermediate reasoning steps before the
final answer. It was introduced by Wei et al. in 2022 and gives the largest gains on multi-step
arithmetic, commonsense and symbolic reasoning tasks. The zero-shot variant simply appends the phrase
"Let's think step by step" to the question (Kojima et al., 2022).

## Self-consistency
Self-consistency samples several chain-of-thought answers at a non-zero temperature and returns the
answer that appears most often (majority vote). It trades extra cost for higher accuracy.

## ReAct
ReAct interleaves reasoning traces ("Thought") with tool calls ("Action") and their results
("Observation"). It lets an LLM agent look things up, call APIs or run code while reasoning.
