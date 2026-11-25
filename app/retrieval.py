"""Retriever factory shared by the answer chain (app.ask) and the eval (eval.run).

Every retriever has the same LangChain interface: invoke(query) -> list[Document],
ranked best-first, at most k documents. The query is a dict:

    {"tr": "Turkish question", "en": "English translation"}   # "en" only if translated

The question is translated once (app.translate); each branch then takes its language:

              ┌─ "tr" ─► dense ──┐
    query ────┼─ "en" ─► dense ──┼─► RRF (EnsembleRetriever) ─► top k
              └─ "en" ─► BM25 ───┘

- dense: embedding similarity in Qdrant (meaning; synonyms, Turkish <-> English)
- bm25:  keyword scores in memory (exact terms: "PopQA", "Recall@100", "Figure 1")
- fusion: Reciprocal Rank Fusion. Each chunk gets sum(weight / (RRF_C + rank)) over the
  lists it appears in; rank-based, so BM25 scores (e.g. 12.7) and cosine similarities
  (e.g. 0.83) never have to be put on the same scale.
"""

from collections.abc import Mapping
from operator import itemgetter
from typing import TypedDict

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda

from app.bm25 import load_bm25_retriever
from app.vectorstore import get_vectorstore

RRF_C = 60  # from the original RRF paper; damps the gap between neighbouring top ranks


class Query(TypedDict, total=False):
    tr: str  # the question as asked
    en: str  # its English translation (translated variants only)


# variant -> branches as (query language, search engine). The ablation table in code.
BRANCHES: dict[str, list[tuple[str, str]]] = {
    "dense": [("tr", "dense")],
    "bm25": [("tr", "bm25")],
    "hybrid": [("tr", "dense"), ("tr", "bm25")],
    "dense_en": [("en", "dense")],
    "bm25_en": [("en", "bm25")],
    "dense_tr_en": [("tr", "dense"), ("en", "dense")],
    "hybrid_en": [("tr", "dense"), ("en", "dense"), ("en", "bm25")],
}
RETRIEVERS = tuple(BRANCHES)


def needs_translation(name: str) -> bool:
    return any(lang == "en" for lang, _ in BRANCHES[name])


def uses_dense(name: str) -> bool:
    return any(engine == "dense" for _, engine in BRANCHES[name])


def compose(name: str, engines: Mapping[str, Runnable], k: int) -> Runnable[Query, list[Document]]:
    """Wire the branches of a variant to the given engines (str -> list[Document])."""
    branches = [
        RunnableLambda(itemgetter(lang)) | engines[engine] for lang, engine in BRANCHES[name]
    ]
    if len(branches) == 1:
        return branches[0]
    # EnsembleRetriever types its input as str, but only passes it on to each branch
    # unchanged (langchain-classic 1.1.0, rank_fusion); tests/test_retrieval.py pins this.
    ensemble = EnsembleRetriever(
        retrievers=branches,
        weights=[1 / len(branches)] * len(branches),
        c=RRF_C,
        id_key="chunk_id",  # the same chunk from several lists counts once, scores added
    )
    # Several lists of k can fuse into more unique chunks; keep the top k.
    return ensemble | RunnableLambda(lambda docs: docs[:k])


def build_retriever(name: str, k: int, model: str | None = None) -> Runnable[Query, list[Document]]:
    if name not in BRANCHES:
        raise ValueError(f"unknown retriever {name!r}; choose from {RETRIEVERS}")
    engines: dict[str, Runnable] = {}  # each engine built once, shared by its branches
    if uses_dense(name):
        engines["dense"] = get_vectorstore(model).as_retriever(search_kwargs={"k": k})
    if any(engine == "bm25" for _, engine in BRANCHES[name]):
        engines["bm25"] = load_bm25_retriever(k=k)
    return compose(name, engines, k)
