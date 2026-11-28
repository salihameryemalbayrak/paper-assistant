"""Qdrant naming shared by indexing (ingest) and search (app)."""

import re
from functools import lru_cache

from langchain_qdrant import QdrantVectorStore

from app.config import get_settings
from app.embeddings import get_embeddings


def collection_name(model_name: str) -> str:
    """One collection per embedding model: vector sizes differ between models.

    "BAAI/bge-m3" -> "chunks_bge_m3"
    """
    slug = re.sub(r"[^a-z0-9]+", "_", model_name.split("/")[-1].lower()).strip("_")
    return f"chunks_{slug}"


MEMORY = ":memory:"


def get_vectorstore(model_name: str | None = None) -> QdrantVectorStore:
    """Connect to the existing collection of an embedding model (built by ingest.index).

    QDRANT_URL=:memory: builds the index in-process from data/chunks.jsonl instead (no
    server; used by CI, where the chunks come from a release asset, D42).
    """
    settings = get_settings()
    name = model_name or settings.embedding_model
    if settings.qdrant_url == MEMORY:
        return _in_memory_store(name)
    return QdrantVectorStore.from_existing_collection(
        embedding=get_embeddings(name),
        collection_name=collection_name(name),
        url=settings.qdrant_url,
    )


@lru_cache
def _in_memory_store(model_name: str) -> QdrantVectorStore:
    """Embed every chunk once per process (the dense branches share this index)."""
    import time

    from ingest.chunk import load_chunks
    from ingest.index import chunk_to_document

    start = time.perf_counter()
    docs = [chunk_to_document(c) for c in load_chunks()]
    store = QdrantVectorStore.from_documents(
        docs,
        embedding=get_embeddings(model_name),
        location=MEMORY,
        collection_name=collection_name(model_name),
    )
    print(f"in-memory Qdrant: {len(docs)} chunks embedded in {time.perf_counter() - start:.0f}s")
    return store
