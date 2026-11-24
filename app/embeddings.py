"""Embedding models: Hugging Face sentence-transformers, wrapped for LangChain."""

from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings

# Some models were trained with prefixes that mark a text as a question or a passage and
# expect the same prefixes at inference time (see each model card). Forgetting them
# silently lowers retrieval quality. Models not listed here use no prefix (e.g. bge-m3).
#   model id -> (query prefix, passage prefix)
PREFIXES: dict[str, tuple[str, str]] = {
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
    "intfloat/multilingual-e5-base": ("query: ", "passage: "),
}


def prefixes(model_name: str) -> tuple[str, str]:
    return PREFIXES.get(model_name, ("", ""))


def encode_kwargs(model_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Arguments for SentenceTransformer.encode(): (for passages, for queries).

    Both dicts are always non-empty on purpose: HuggingFaceEmbeddings falls back to the
    passage arguments when the query arguments are empty, which would give queries the
    passage prefix.
    """
    query_prefix, passage_prefix = prefixes(model_name)
    # Unit-length vectors: cosine similarity then equals the dot product.
    passage: dict[str, Any] = {"normalize_embeddings": True}
    query: dict[str, Any] = {"normalize_embeddings": True}
    if passage_prefix:
        passage["prompt"] = passage_prefix
    if query_prefix:
        query["prompt"] = query_prefix
    return passage, query


def get_embeddings(model_name: str | None = None) -> HuggingFaceEmbeddings:
    """Load the embedding model (downloaded to ~/.cache/huggingface on first use)."""
    name = model_name or get_settings().embedding_model
    passage, query = encode_kwargs(name)
    return HuggingFaceEmbeddings(model_name=name, encode_kwargs=passage, query_encode_kwargs=query)
