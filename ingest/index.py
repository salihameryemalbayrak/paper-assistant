"""Embed the chunks and write them to Qdrant (one collection per embedding model).

The collection is rebuilt from scratch on every run: with a few hundred chunks this is
simpler and safer than tracking which chunks changed.

Usage:
    uv run python -m ingest.index                       # model from EMBEDDING_MODEL
    uv run python -m ingest.index --model BAAI/bge-m3   # another model, own collection
"""

import argparse
import time
import uuid

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore

from app.config import get_settings
from app.embeddings import get_embeddings, prefixes
from app.vectorstore import collection_name
from ingest.chunk import Chunk, load_chunks

# Fixed namespace so that the same chunk id always maps to the same Qdrant point id.
_ID_NAMESPACE = uuid.UUID("5d0f3f3e-6a52-4f0e-9a37-2f8c1b7e9d41")


def point_id(chunk_id: str) -> str:
    """Qdrant point ids must be integers or UUIDs; derive a stable UUID from the chunk id."""
    return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))


def chunk_to_document(chunk: Chunk) -> Document:
    """search_text is embedded; the rest (including the original text) becomes payload."""
    metadata = chunk.model_dump(mode="json", exclude={"id", "search_text"})
    return Document(
        id=point_id(chunk.id),
        page_content=chunk.search_text,
        metadata={"chunk_id": chunk.id, **metadata},
    )


def token_lengths(texts: list[str], model_name: str, prefix: str) -> tuple[list[int], int]:
    """Real token counts (prefix and special tokens included) and the model's input limit.

    sentence-transformers silently truncates longer inputs, so they must be counted here.
    """
    from transformers import AutoTokenizer  # installed with sentence-transformers

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    lengths = [len(tokenizer(prefix + t)["input_ids"]) for t in texts]
    return lengths, tokenizer.model_max_length


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", help="embedding model id (default: EMBEDDING_MODEL)")
    args = parser.parse_args()

    settings = get_settings()
    model = args.model or settings.embedding_model
    collection = collection_name(model)
    chunks = load_chunks()
    documents = [chunk_to_document(c) for c in chunks]

    lengths, limit = token_lengths([d.page_content for d in documents], model, prefixes(model)[1])
    lengths_sorted = sorted(lengths)
    over = [c.id for c, n in zip(chunks, lengths, strict=True) if n > limit]
    print(
        f"tokens ({model}): median={lengths_sorted[len(lengths) // 2]} "
        f"max={lengths_sorted[-1]} limit={limit} over limit={len(over)} {over[:5]}"
    )

    start = time.perf_counter()
    QdrantVectorStore.from_documents(
        documents,
        get_embeddings(model),
        url=settings.qdrant_url,
        collection_name=collection,
        force_recreate=True,
    )
    print(
        f"indexed {len(documents)} chunks -> {settings.qdrant_url} collection '{collection}' "
        f"in {time.perf_counter() - start:.1f}s"
    )


if __name__ == "__main__":
    main()
