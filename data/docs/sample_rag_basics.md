# Retrieval-Augmented Generation (sample knowledge-base document)

> Placeholder data so the pipeline runs end to end. Replace with your real dataset.

## What RAG is
Retrieval-Augmented Generation (RAG) combines a retriever with a generator. The retriever finds
passages related to the user's question in an external knowledge base, and the generator (an LLM)
writes an answer conditioned on those passages. RAG was introduced by Lewis et al. in 2020.

## Why RAG reduces hallucination
Because the answer is grounded in retrieved text, the model has less need to rely on memorised facts,
and answers can cite their sources. However, if the retriever returns irrelevant or outdated passages,
standard RAG will still use them and can produce confident wrong answers.

## Chunking
Documents are split into chunks before embedding. Common strategies are fixed-size chunks with overlap,
sentence-based chunks, and semantic chunks that break where the topic changes. Typical chunk sizes are
between 200 and 1000 characters with 10-20% overlap.

## Embeddings and vector databases
Each chunk is converted into a dense vector by an embedding model such as BGE or MiniLM. The vectors
are stored in a vector database such as ChromaDB or FAISS, which supports fast nearest-neighbour search
using cosine similarity.

## Corrective RAG (CRAG)
Corrective Retrieval-Augmented Generation was proposed by Yan et al. in 2024. A lightweight retrieval
evaluator scores the retrieved documents. If they are judged correct, they are refined and used. If they
are judged incorrect, the system discards them and falls back to web search. If the judgement is
ambiguous, it combines the refined documents with web search results.
