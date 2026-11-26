"""Reranking with a fake cross-encoder: no model download."""

import pytest
from langchain_core.cross_encoders import BaseCrossEncoder
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.rerank import compact, with_reranker
from app.retrieval import build_retriever, needs_translation


class WordOverlap(BaseCrossEncoder):
    """Score = words shared by query and passage; records the queries it saw."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def score(self, text_pairs: list[tuple[str, str]]) -> list[float]:
        self.queries += [q for q, _ in text_pairs]
        return [len(set(q.lower().split()) & set(p.lower().split())) for q, p in text_pairs]


def doc(chunk_id: str, text: str) -> Document:
    return Document(page_content=text, metadata={"chunk_id": chunk_id})


CANDIDATES = [
    doc("a", "training details"),
    doc("b", "sparse retrieval is weak across languages"),
    doc("c", "sparse vectors"),
]
QUERY = {"tr": "seyrek arama neden zayıf", "en": "why is sparse retrieval weak"}


def rerank(lang: str, top_n: int = 3) -> tuple[list[str], WordOverlap]:
    ce = WordOverlap()
    chain = with_reranker(RunnableLambda(lambda _query: CANDIDATES), ce, lang, top_n)
    return [d.metadata["chunk_id"] for d in chain.invoke(QUERY)], ce


def test_candidates_are_reordered_by_score_and_cut_to_top_n():
    ids, _ = rerank("en", top_n=2)
    assert ids == ["b", "c"]  # b shares 3 words, c 1, a 0


def test_reranker_reads_its_own_language():
    _, ce = rerank("tr")
    assert set(ce.queries) == {"seyrek arama neden zayıf"}
    _, ce = rerank("en")
    assert set(ce.queries) == {"why is sparse retrieval weak"}


def test_compact_collapses_table_padding_only():
    table = "| Model    | Recall@100 |\n|----------|------------|\n| Ağırlık  | 55.8       |"
    assert compact(table) == "| Model | Recall@100 |\n|---|---|\n| Ağırlık | 55.8 |"
    assert compact("Şekil 1 - ığdır") == "Şekil 1 - ığdır"  # single dashes, Turkish kept


def test_english_reranker_needs_translation_even_for_turkish_retrievers():
    assert not needs_translation("dense")
    assert not needs_translation("dense", "bge_m3")
    assert needs_translation("dense", "minilm_en")


def test_unknown_reranker_fails_before_loading_anything():
    with pytest.raises(ValueError, match="unknown reranker"):
        build_retriever("bm25", 5, reranker="nope")
