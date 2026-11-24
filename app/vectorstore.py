"""Qdrant naming shared by indexing (ingest) and search (app)."""

import re


def collection_name(model_name: str) -> str:
    """One collection per embedding model: vector sizes differ between models.

    "BAAI/bge-m3" -> "chunks_bge_m3"
    """
    slug = re.sub(r"[^a-z0-9]+", "_", model_name.split("/")[-1].lower()).strip("_")
    return f"chunks_{slug}"
