"""Hybrid fusion with fake retrievers: no Qdrant, no model download."""

from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.retrieval import RRF_C


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
