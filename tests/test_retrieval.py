"""Fusion and variant wiring with fake retrievers: no Qdrant, no model download."""

import pytest
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.retrieval import RETRIEVERS, RRF_C, compose, needs_translation


def doc(chunk_id: str) -> Document:
    return Document(page_content=f"text of {chunk_id}", metadata={"chunk_id": chunk_id})


def fixed(*ids: str) -> RunnableLambda:
    return RunnableLambda(lambda _question: [doc(i) for i in ids])


def fuse(*lists: tuple[str, ...]) -> list[str]:
    ensemble = EnsembleRetriever(
        retrievers=[fixed(*ids) for ids in lists], c=RRF_C, id_key="chunk_id"
    )
    return [d.metadata["chunk_id"] for d in ensemble.invoke("question")]


def test_chunk_found_by_both_lists_beats_a_single_first_place():
    # "b" is 2nd in both lists: 2 * 0.5/62 = 0.0161 > 0.5/61 = 0.0082 for "a" or "x"
    assert fuse(("a", "b", "c"), ("x", "b", "y"))[0] == "b"


def test_duplicates_are_merged_by_chunk_id():
    fused = fuse(("a", "b"), ("b", "a"))
    assert sorted(fused) == ["a", "b"]


def test_chunk_from_one_list_is_kept():
    # BM25 alone finds "z" (e.g. a figure number); fusion must not drop it
    assert "z" in fuse(("a", "b"), ("z",))


# Variant wiring: fake engines that return the query text they received as a chunk id.
def echo(engine: str) -> RunnableLambda:
    return RunnableLambda(lambda text: [doc(f"{engine}:{text}")])


ENGINES = {"dense": echo("dense"), "bm25": echo("bm25")}
QUERY = {"tr": "seyrek arama", "en": "sparse retrieval"}


def ids(name: str, k: int = 10) -> list[str]:
    return [d.metadata["chunk_id"] for d in compose(name, ENGINES, k).invoke(QUERY)]


def test_each_branch_gets_its_language():
    assert ids("dense") == ["dense:seyrek arama"]
    assert ids("bm25_en") == ["bm25:sparse retrieval"]
    assert sorted(ids("hybrid_en")) == [
        "bm25:sparse retrieval",
        "dense:seyrek arama",
        "dense:sparse retrieval",
    ]


def test_ensemble_passes_a_dict_query_unchanged():
    # EnsembleRetriever types its input as str; the translated variants rely on it handing
    # the dict to every branch as is. If a new version converts or checks it, this fails.
    seen = []
    branch = RunnableLambda(lambda query: seen.append(query) or [doc("a")])
    EnsembleRetriever(retrievers=[branch, branch], id_key="chunk_id").invoke(QUERY)
    assert seen == [QUERY, QUERY]


def test_fused_result_is_cut_to_k():
    assert len(ids("hybrid_en", k=2)) == 2


def test_untranslated_variants_never_read_english():
    # {"tr"} alone must be enough for them: no LLM call in the answer chain.
    for name in RETRIEVERS:
        if not needs_translation(name):
            compose(name, ENGINES, 10).invoke({"tr": "soru"})


def test_translated_variant_without_english_fails_loudly():
    with pytest.raises(KeyError):
        compose("bm25_en", ENGINES, 10).invoke({"tr": "soru"})


def test_single_branch_is_cut_to_k_even_when_the_engine_returns_more():
    many = {"dense": RunnableLambda(lambda text: [doc(f"d{i}") for i in range(20)])}
    assert len(compose("dense", many, 5).invoke(QUERY)) == 5
