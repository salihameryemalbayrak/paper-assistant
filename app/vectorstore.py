"""Qdrant naming shared by indexing (ingest) and search (app)."""

import re

from langchain_qdrant import QdrantVectorStore

from app.config import get_settings
from app.embeddings import get_embeddings


def collection_name(model_name: str) -> str:
    """One collection per embedding model: vector sizes differ between models.

    "BAAI/bge-m3" -> "chunks_bge_m3"
    """
    slug = re.sub(r"[^a-z0-9]+", "_", model_name.split("/")[-1].lower()).strip("_")
    return f"chunks_{slug}"


def get_vectorstore(model_name: str | None = None) -> QdrantVectorStore:
    """Connect to the existing collection of an embedding model (built by ingest.index)."""
    settings = get_settings()
    name = model_name or settings.embedding_model
    return QdrantVectorStore.from_existing_collection(
        embedding=get_embeddings(name),
        collection_name=collection_name(name),
        url=settings.qdrant_url,
    )
