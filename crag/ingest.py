"""Load documents from data/docs (txt, md, pdf), chunk them and store them in ChromaDB.

Usage:
    python -m crag.ingest            # add/refresh everything in data/docs
    python -m crag.ingest --reset    # wipe the vector store first
"""
import argparse
import shutil

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from crag import config


def load_documents() -> list[Document]:
    docs: list[Document] = []
    for path in sorted(config.DOCS_DIR.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        rel = str(path.relative_to(config.DOCS_DIR))
        if suffix in {".txt", ".md"}:
            docs.append(Document(page_content=path.read_text(encoding="utf-8", errors="ignore"),
                                 metadata={"source": rel}))
        elif suffix == ".pdf":
            from pypdf import PdfReader

            for i, page in enumerate(PdfReader(str(path)).pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append(Document(page_content=text, metadata={"source": f"{rel} p.{i}"}))
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete the existing vector store first")
    args = ap.parse_args()

    if args.reset and config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
        print(f"Deleted {config.CHROMA_DIR}")

    docs = load_documents()
    if not docs:
        print(f"No .txt/.md/.pdf files found in {config.DOCS_DIR}")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    # deterministic ids so re-running ingest doesn't create duplicates
    ids = [f"{c.metadata['source']}::{i}" for i, c in enumerate(chunks)]

    from crag.retriever import get_vectorstore

    get_vectorstore().add_documents(chunks, ids=ids)
    print(f"Ingested {len(docs)} documents -> {len(chunks)} chunks into {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
