"""Full eval helpers; needs the "eval" group (RAGAS), so CI skips this file."""

import math

import pytest

pytest.importorskip("ragas")

from eval.full import _number, summarize  # noqa: E402


def test_nan_and_none_become_not_scored():
    assert _number(float("nan")) is None
    assert _number(None) is None
    assert _number(0.123456) == 0.1235


def test_summary_counts_unscored_rows_and_groups_by_type():
    rows = [
        {"type": "table", "faithfulness": 1.0, "answer_relevancy": 0.8},
        {"type": "table", "faithfulness": None, "answer_relevancy": 0.6},  # judge failed
        {"type": "figure", "faithfulness": 0.5, "answer_relevancy": None},
    ]
    summary = summarize(rows)
    assert summary["all"]["faithfulness"] == {"mean": 0.75, "n": 2, "not_scored": 1}
    assert math.isclose(summary["table"]["answer_relevancy"]["mean"], 0.7)
    assert summary["figure"]["answer_relevancy"] == {"mean": None, "n": 0, "not_scored": 1}


def test_judge_context_carries_citation_labels():
    # the judge must see the labels the answer cites (D39)
    from langchain_core.documents import Document

    from app.ask import format_docs

    doc = Document(page_content="x", metadata={"paper": "bge_m3", "pages": [7], "page": 7,
                   "section": "4.2 Results", "text": "Sparse is weak."})  # fmt: skip
    assert format_docs([doc]) == "[bge_m3, s.7, §4.2]\nSparse is weak."
