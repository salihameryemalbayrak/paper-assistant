from eval.check_evidence import missing_quotes, normalize, present_terms
from eval.dataset import EvalItem

PAGES = {
    ("vllm", 2): "Indeed, our profiling shows that only  20.4% - 38.2% of the KV\ncache memory"
}
DOCS = {"mistral": "Mistral 7B uses Sliding Window Attention. İnce ayar verisi."}


def item(**fields) -> EvalItem:
    base = {"id": "x", "phrasing": "term", "question": "?", "answer": "a"}
    return EvalItem.model_validate(base | fields)


def answerable(page: int) -> EvalItem:
    return item(
        type="single_page",
        sources=[{"paper": "vllm", "page": page}],
        evidence=[{"paper": "vllm", "page": page, "quote": "only 20.4% - 38.2% of the KV cache"}],
    )


def test_quote_is_found_ignoring_case_and_line_breaks():
    assert missing_quotes(answerable(2), PAGES) == []


def test_quote_on_the_wrong_page_is_reported():
    assert missing_quotes(answerable(3), PAGES) == ["only 20.4% - 38.2% of the KV cache"]


def test_absent_term_found_in_the_document_is_reported():
    q = item(type="unanswerable", absent_terms={"mistral": ["trillion", "sliding window"]})
    assert present_terms(q, DOCS) == ["mistral: sliding window"]


def test_turkish_text_survives_normalization():
    assert normalize("  İnce   ayar\nverisi ") == "ince ayar verisi"
    assert present_terms(item(type="unanswerable", absent_terms={"mistral": ["ince ayar"]}), DOCS)


def test_unverified_question_without_evidence_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="no evidence"):
        item(type="single_page", sources=[{"paper": "vllm", "page": 2}])
    with pytest.raises(ValueError, match="absent_terms"):
        item(type="unanswerable")
