"""Parse PDFs with Docling into the project's element format.

Requires the "ingest" dependency group (installed locally by default).

Usage:
    uv run python -m ingest.parse            # parse PDFs that have no output yet
    uv run python -m ingest.parse --force    # re-parse everything
"""

import argparse
import time

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel, DoclingDocument, PictureItem, TableItem

from app.text import normalize_text
from ingest.download import RAW_DIR
from ingest.elements import (
    PARSED_DIR,
    Element,
    ElementType,
    demote_front_matter_headings,
    save_elements,
)

HEADING_LABELS = {DocItemLabel.TITLE, DocItemLabel.SECTION_HEADER}
# Repeated page furniture and layout-only items carry no searchable content.
SKIPPED_LABELS = {
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
    DocItemLabel.DOCUMENT_INDEX,
}
# Bibliography entries look relevant to many queries ("BERT: Pre-training of ...") but
# answer none of them. Sections after the bibliography (appendices) are kept.
SKIPPED_SECTIONS = {"references", "bibliography"}


def _is_skipped_section(heading: str) -> bool:
    return heading.strip().lower() in SKIPPED_SECTIONS


def figure_text(picture: PictureItem, doc: DoclingDocument) -> str:
    """Caption plus the text labels found inside the figure (e.g. boxes in a diagram)."""
    caption = picture.caption_text(doc)
    inner = [
        normalize_text(child.text)
        for child, _level in doc.iterate_items(root=picture, traverse_pictures=True)
        if child is not picture and getattr(child, "text", "").strip()
    ]
    if not inner:
        return caption
    return f"{caption}\n\n[Figure text] " + " | ".join(inner)


def document_to_elements(doc: DoclingDocument, paper: str) -> list[Element]:
    elements: list[Element] = []
    section = ""
    # Table and figure captions are already included in the table/figure element;
    # keeping them as separate elements too would index the same text twice.
    attached_captions = {ref.cref for item in [*doc.tables, *doc.pictures] for ref in item.captions}
    # iterate_items does not descend into pictures here; figure_text() reads them.
    for item, _level in doc.iterate_items():
        label = getattr(item, "label", None)
        if label in SKIPPED_LABELS or not getattr(item, "prov", None):
            continue
        if item.self_ref in attached_captions:
            continue
        page = item.prov[0].page_no
        pages = sorted({p.page_no for p in item.prov})

        if label in HEADING_LABELS:
            section = normalize_text(item.text)
            if not _is_skipped_section(section):
                elements.append(
                    Element(
                        paper=paper,
                        page=page,
                        pages=pages,
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
        elif isinstance(item, PictureItem):
            element_type = ElementType.FIGURE
            text = figure_text(item, doc)
        elif label == DocItemLabel.CAPTION:
            element_type = ElementType.CAPTION
            text = item.text
        else:
            element_type = ElementType.TEXT
            text = getattr(item, "text", "")

        text = normalize_text(text)
        if text:
            elements.append(
                Element(
                    paper=paper,
                    page=page,
                    pages=pages,
                    section=section,
                    type=element_type,
                    text=text,
                )
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
        elements, demoted = demote_front_matter_headings(document_to_elements(doc, paper=pdf.stem))
        save_elements(elements, out)
        counts = {t.value: sum(e.type == t for e in elements) for t in ElementType}
        print(
            f"ok     {pdf.stem}: {len(elements)} elements {counts} "
            f"in {time.perf_counter() - start:.1f}s -> {out}"
            + (f" | page-1 headings demoted to text: {demoted}" if demoted else "")
        )


if __name__ == "__main__":
    main()
