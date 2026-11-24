"""Integration test for the Docling parse step.

Skipped when Docling is not installed (CI skips the "ingest" group) or when the
papers have not been downloaded (they are not stored in git).
"""

from pathlib import Path

import pytest

pytest.importorskip("docling")

RAGAS_PDF = Path("data/raw/ragas.pdf")
pytestmark = pytest.mark.skipif(not RAGAS_PDF.exists(), reason="run ingest.download first")


@pytest.fixture(scope="module")
def ragas_elements():
    from docling.document_converter import DocumentConverter

    from ingest.parse import document_to_elements

    doc = DocumentConverter().convert(RAGAS_PDF).document
    return document_to_elements(doc, paper="ragas")


def test_headings_carry_page_and_section(ragas_elements):
    headings = [(e.text, e.page) for e in ragas_elements if e.type == "heading"]
    assert any("WikiEval Dataset" in text and page == 4 for text, page in headings)

    under_wikieval = [e for e in ragas_elements if "WikiEval Dataset" in e.section]
    assert under_wikieval, "elements after the heading should inherit its section"


def test_table_is_kept_as_markdown(ragas_elements):
    tables = [e for e in ragas_elements if e.type == "table" and e.page == 5]
    assert any("0.95" in t.text and "|" in t.text for t in tables)


def test_references_and_page_furniture_are_dropped(ragas_elements):
    assert not any(e.section.lower() == "references" for e in ragas_elements)
    # the arXiv stamp in the page margin is page furniture, not content
    assert not any(e.text.startswith("arXiv:2309.15217") for e in ragas_elements)


def test_table_captions_are_not_duplicated(ragas_elements):
    tables = [e.text for e in ragas_elements if e.type == "table"]
    captions = [e.text for e in ragas_elements if e.type == "caption"]
    assert not [c for c in captions if any(c in t for t in tables)]
