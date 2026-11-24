import json

import pytest

from eval.dataset import EvalItem, SourceRef, load_dataset
from eval.retrieval_metrics import evaluate, recall_at_k, reciprocal_rank

A1 = SourceRef(paper="a", page=1)
A2 = SourceRef(paper="a", page=2)
B5 = SourceRef(paper="b", page=5)
C9 = SourceRef(paper="c", page=9)


# Each hit is the set of (paper, page) pairs one retrieved chunk covers.


def test_recall_at_k():
    hits = [{C9}, {A1}, {A2}]
    assert recall_at_k(hits, [A1], k=1) == 0.0
    assert recall_at_k(hits, [A1], k=2) == 1.0
    # comparison question with two expected sources, only one found
    assert recall_at_k(hits, [A1, B5], k=3) == 0.5


def test_reciprocal_rank():
    assert reciprocal_rank([{A1}, {C9}], [A1]) == 1.0
    assert reciprocal_rank([{C9}, {C9}, {A1}], [A1]) == pytest.approx(1 / 3)
    assert reciprocal_rank([{C9}], [A1]) == 0.0
    # only the FIRST relevant hit counts
    assert reciprocal_rank([{C9}, {B5}, {A1}], [A1, B5]) == 0.5


def test_chunk_spanning_two_pages_matches_either_page():
    # a paragraph that starts on page 1 and continues on page 2
    hits = [{C9}, {A1, A2}]
    assert reciprocal_rank(hits, [A2]) == 0.5
    assert recall_at_k(hits, [A2], k=2) == 1.0


def test_evaluate_with_fake_retriever():
    items = [
        EvalItem(id="q1", type="table", question="q1", answer="x", sources=[A1]),
        EvalItem(id="q2", type="single_page", question="q2", answer="x", sources=[B5]),
        EvalItem(id="q3", type="unanswerable", question="q3", answer="Dokümanda bulamadım."),
    ]
    fake_results = {"q1": [{A1}, {C9}], "q2": [{C9}, {B5}], "q3": [{C9}]}

    result = evaluate(items, lambda q: fake_results[q], ks=(1, 2))

    assert result["all"]["n"] == 2  # unanswerable question is excluded
    assert result["all"]["recall@1"] == 0.5
    assert result["all"]["recall@2"] == 1.0
    assert result["all"]["mrr"] == 0.75  # (1 + 1/2) / 2
    assert result["table"]["mrr"] == 1.0


def test_schema_rules():
    with pytest.raises(ValueError):  # answerable question without a source
        EvalItem(id="x", type="table", question="q", answer="a")
    with pytest.raises(ValueError):  # unanswerable question with a source
        EvalItem(id="x", type="unanswerable", question="q", answer="a", sources=[A1])
    with pytest.raises(ValueError):  # comparison needs two different papers
        EvalItem(id="x", type="comparison", question="q", answer="a", sources=[A1, A2])


def test_load_dataset_reports_line_number(tmp_path):
    path = tmp_path / "d.jsonl"
    good = {
        "id": "q1",
        "type": "table",
        "question": "q",
        "answer": "a",
        "sources": [{"paper": "a", "page": 1}],
    }
    bad = {"id": "q2", "type": "table", "question": "q", "answer": "a"}
    path.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=":2:"):
        load_dataset(path)


def test_real_dataset_is_valid_and_verified():
    from pathlib import Path

    from ingest.download import parse_sources

    items = load_dataset(Path("eval/dataset.jsonl"))
    known_papers = {
        s.short_name for s in parse_sources(Path("data/SOURCES.md").read_text(encoding="utf-8"))
    }

    assert len(items) >= 20
    unverified = [i.id for i in items if not i.verified]
    assert not unverified, f"questions not checked against the PDF yet: {unverified}"
    for item in items:
        for source in item.sources:
            assert source.paper in known_papers, f"{item.id}: unknown paper {source.paper!r}"
