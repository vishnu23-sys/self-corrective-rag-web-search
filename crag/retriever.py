"""Vector store (ChromaDB) + local embeddings (FastEmbed, no API key needed)."""
from functools import lru_cache

from crag import config


@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_community.embeddings import FastEmbedEmbeddings

    return FastEmbedEmbeddings(model_name=config.EMBED_MODEL)


@lru_cache(maxsize=1)
def get_vectorstore():
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=config.COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
    )


def retrieve(query: str, k: int | None = None) -> list[dict]:
    """Return top-k chunks as plain dicts: {content, source, score}."""
    results = get_vectorstore().similarity_search_with_relevance_scores(query, k=k or config.TOP_K)
    return [
        {
            "id": doc.id or "",  # chunk id from ingest: "<source>::<n>"
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(float(score), 3),
        }
        for doc, score in results
    ]
