"""Compare two PDF parsers (PyMuPDF vs Docling) on the project's papers.

This is a one-off experiment, not part of the pipeline. Both libraries are
loaded into a temporary environment so they do not become project dependencies:

    uv run --with docling --with pymupdf python -m ingest.experiments.compare_parsers

Outputs:
    data/parsed/<parser>/<paper>.md         full text per parser, for manual inspection
    docs/benchmarks/parser_comparison.md    summary table
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/parsed")
REPORT = Path("docs/benchmarks/parser_comparison.md")

# One real section heading per paper (page = physical PDF page).
EXPECTED_HEADINGS = {
    "ragas": ("The WikiEval Dataset", 4),
    "self_rag": ("Self-RAG Training", 4),
    "bge_m3": ("Cross-Lingual Retrieval", 7),
    "e5": ("CCPairs", 2),
    "qlora": ("Background", 3),
}

# Rows the eval set's table questions depend on: every token must appear in ONE table row.
EXPECTED_TABLE_ROWS = {
    "q07": ("ragas", 5, ["Ragas", "0.95", "0.78", "0.70"]),
    "q08": ("self_rag", 8, ["13B", "55.8", "69.3"]),
    "q09": ("bge_m3", 7, ["tr", "45.8", "75.6"]),
    "q10": ("qlora", 10, ["Guanaco", "7B", "5 GB", "87.0%"]),
}


@dataclass
class ParseResult:
    seconds: float = 0.0
    pages: int = 0
    headings: list[tuple[str, int]] = field(default_factory=list)  # (text, page)
    tables: list[tuple[int, list[list[str]]]] = field(default_factory=list)  # (page, rows)
    figures: int = 0
    captions: int = 0
    markdown: str = ""


def parse_pymupdf(pdf: Path) -> ParseResult:
    import pymupdf

    start = time.perf_counter()
    doc = pymupdf.open(pdf)
    result = ParseResult(pages=doc.page_count)
    # Headings come from the PDF outline (bookmarks), if the authors' tooling created one.
    result.headings = [(title, page) for _level, title, page in doc.get_toc()]
    parts = []
    for page_no, page in enumerate(doc, start=1):
        parts.append(f"\n\n<!-- page {page_no} -->\n\n{page.get_text()}")
        for table in page.find_tables().tables:
            rows = [[cell or "" for cell in row] for row in table.extract()]
            result.tables.append((page_no, rows))
        result.figures += len(page.get_images())
    result.markdown = "".join(parts)
    result.seconds = time.perf_counter() - start
    return result


def make_docling_converter():
    from docling.document_converter import DocumentConverter

    return DocumentConverter()


def parse_docling(pdf: Path, converter) -> ParseResult:
    from docling_core.types.doc import DocItemLabel, TableItem

    start = time.perf_counter()
    doc = converter.convert(pdf).document
    result = ParseResult(pages=len(doc.pages))
    for item, _level in doc.iterate_items():
        label = getattr(item, "label", None)
        page = item.prov[0].page_no if getattr(item, "prov", None) else 0
        if label in (DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE):
            result.headings.append((item.text, page))
        elif label == DocItemLabel.PICTURE:
            result.figures += 1
        elif label == DocItemLabel.CAPTION:
            result.captions += 1
        if isinstance(item, TableItem):
            df = item.export_to_dataframe(doc=doc)
            header = [str(c) for c in df.columns]
            rows = [header] + [[str(v) for v in row] for row in df.itertuples(index=False)]
            result.tables.append((page, rows))
    result.markdown = doc.export_to_markdown()
    result.seconds = time.perf_counter() - start
    return result


def heading_found(result: ParseResult, text: str, page: int) -> bool:
    return any(text.lower() in h.lower() and p == page for h, p in result.headings)


def table_row_found(result: ParseResult, page: int, tokens: list[str]) -> bool:
    for table_page, rows in result.tables:
        if table_page != page:
            continue
        for row in rows:
            joined = " | ".join(c.strip() for c in row)
            # Each token must appear as a whole word: "tr" must not match inside "strong",
            # and "55.8" must not match inside "155.81".
            if all(re.search(rf"(?<![\w.]){re.escape(t)}(?![\w.])", joined) for t in tokens):
                return True
    return False


def main() -> None:
    papers = sorted(p.stem for p in RAW_DIR.glob("*.pdf"))
    converter = make_docling_converter()
    results: dict[str, dict[str, ParseResult]] = {"pymupdf": {}, "docling": {}}

    for paper in papers:
        pdf = RAW_DIR / f"{paper}.pdf"
        results["pymupdf"][paper] = parse_pymupdf(pdf)
        results["docling"][paper] = parse_docling(pdf, converter)
        for parser, by_paper in results.items():
            r = by_paper[paper]
            print(
                f"{parser:8s} {paper:9s} {r.seconds:6.1f}s  headings={len(r.headings):3d}  "
                f"tables={len(r.tables):2d}  figures={r.figures:2d}"
            )
            out = OUT_DIR / parser / f"{paper}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(r.markdown, encoding="utf-8")

    lines = [
        "# PDF parser comparison",
        "",
        "Generated by `ingest/experiments/compare_parsers.py`. "
        "Docling timing for the first paper includes model loading.",
        "",
        "| paper | pages | parser | seconds | headings | tables | figures | captions |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for paper in papers:
        for parser in results:
            r = results[parser][paper]
            lines.append(
                f"| {paper} | {r.pages} | {parser} | {r.seconds:.1f} | {len(r.headings)} "
                f"| {len(r.tables)} | {r.figures} | {r.captions} |"
            )
    lines += [
        "",
        "## Expected section headings (text on the right page)",
        "",
        "| paper | heading | page | pymupdf | docling |",
        "|---|---|---|---|---|",
    ]
    for paper, (text, page) in EXPECTED_HEADINGS.items():
        marks = [
            "yes" if heading_found(results[p][paper], text, page) else "**no**" for p in results
        ]
        lines.append(f"| {paper} | {text} | {page} | {marks[0]} | {marks[1]} |")
    lines += [
        "",
        "## Table rows needed by the eval set (all values in one row)",
        "",
        "| question | paper | page | values | pymupdf | docling |",
        "|---|---|---|---|---|---|",
    ]
    for qid, (paper, page, tokens) in EXPECTED_TABLE_ROWS.items():
        marks = [
            "yes" if table_row_found(results[p][paper], page, tokens) else "**no**" for p in results
        ]
        lines.append(
            f"| {qid} | {paper} | {page} | {' / '.join(tokens)} | {marks[0]} | {marks[1]} |"
        )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
