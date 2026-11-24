"""Retriever factory shared by the answer chain (app.ask) and the eval (eval.run).

Every retriever has the same LangChain interface: invoke(question) -> list[Document],
ranked best-first, at most k documents.

- dense:  embedding similarity in Qdrant (meaning; synonyms, Turkish <-> English)
- bm25:   keyword scores in memory (exact terms: "PopQA", "Recall@100", "Figure 1")
- hybrid: both lists fused with Reciprocal Rank Fusion (RRF) by LangChain's
          EnsembleRetriever. Each chunk gets sum(weight / (RRF_C + rank)) over the lists
          it appears in; rank-based, so BM25 scores (e.g. 12.7) and cosine similarities
          (e.g. 0.83) never have to be put on the same scale.
"""

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda

from app.bm25 import load_bm25_retriever
from app.vectorstore import get_vectorstore

RETRIEVERS = ("dense", "bm25", "hybrid")
RRF_C = 60  # from the original RRF paper; damps the gap between neighbouring top ranks


def build_retriever(name: str, k: int, model: str | None = None) -> Runnable[str, list[Document]]:
    if name == "dense":
        return get_vectorstore(model).as_retriever(search_kwargs={"k": k})
    if name == "bm25":
        return load_bm25_retriever(k=k)
    if name == "hybrid":
        ensemble = EnsembleRetriever(
            retrievers=[build_retriever("dense", k, model), build_retriever("bm25", k)],
            weights=[0.5, 0.5],
            c=RRF_C,
            id_key="chunk_id",  # the same chunk from both lists counts once
        )
        # Two lists of k can fuse into up to 2k unique chunks; keep the top k.
        return ensemble | RunnableLambda(lambda docs: docs[:k])
    raise ValueError(f"unknown retriever {name!r}; choose from {RETRIEVERS}")
