"""Parse PDFs with Docling into the project's element format.

Requires the "ingest" dependency group (installed locally by default).

Usage:
    uv run python -m ingest.parse            # parse PDFs that have no output yet
    uv run python -m ingest.parse --force    # re-parse everything
"""

import argparse
import time

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel, DoclingDocument, TableItem

from app.text import normalize_text
from ingest.download import RAW_DIR
from ingest.elements import PARSED_DIR, Element, ElementType, save_elements

HEADING_LABELS = {DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER}
# Repeated page furniture and layout-only items carry no searchable content.
SKIPPED_LABELS = {
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
    DocItemLabel.PICTURE,  # the image itself; its caption is kept as a CAPTION element
    DocItemLabel.DOCUMENT_INDEX,
}
# Bibliography entries look relevant to many queries ("BERT: Pre-training of ...") but
# answer none of them. Sections after the bibliography (appendices) are kept.
SKIPPED_SECTIONS = {"references", "bibliography"}


def _is_skipped_section(heading: str) -> bool:
    return heading.strip().lower() in SKIPPED_SECTIONS


def document_to_elements(doc: DoclingDocument, paper: str) -> list[Element]:
    elements: list[Element] = []
    section = ""
    # A table's Markdown export already starts with its caption; keeping the caption
    # as a separate element too would index the same text twice.
    table_caption_refs = {ref.cref for table in doc.tables for ref in table.captions}
    for item, _level in doc.iterate_items():
        label = getattr(item, "label", None)
        if label in SKIPPED_LABELS or not getattr(item, "prov", None):
            continue
        if item.self_ref in table_caption_refs:
            continue
        page = item.prov[0].page_no

        if label in HEADING_LABELS:
            section = normalize_text(item.text)
            if not _is_skipped_section(section):
                elements.append(
                    Element(
                        paper=paper,
                        page=page,
                        section=section,
                        type=ElementType.HEADING,
                        text=section,
                    )
                )
            continue
        if _is_skipped_section(section):
            continue

        if isinstance(item, TableItem):
            element_type = ElementType.TABLE
            text = item.export_to_markdown(doc=doc)
        elif label == DocItemLabel.CAPTION:
            element_type = ElementType.CAPTION
            text = item.text
        else:
            element_type = ElementType.TEXT
            text = getattr(item, "text", "")

        text = normalize_text(text)
        if text:
            elements.append(
                Element(paper=paper, page=page, section=section, type=element_type, text=text)
            )
    return elements


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-parse existing outputs")
    args = parser.parse_args()

    converter = DocumentConverter()
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        out = PARSED_DIR / f"{pdf.stem}.jsonl"
        if out.exists() and not args.force:
            print(f"skip   {pdf.stem} (already parsed)")
            continue
        start = time.perf_counter()
        doc = converter.convert(pdf).document
        elements = document_to_elements(doc, paper=pdf.stem)
        save_elements(elements, out)
        counts = {t.value: sum(e.type == t for e in elements) for t in ElementType}
        print(
            f"ok     {pdf.stem}: {len(elements)} elements {counts} "
            f"in {time.perf_counter() - start:.1f}s -> {out}"
        )


if __name__ == "__main__":
    main()
