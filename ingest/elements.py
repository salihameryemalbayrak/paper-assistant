"""The project's own document format: a flat list of elements per paper.

The parse step (Docling) writes elements to data/parsed/<paper>.jsonl; the chunk
step reads them. Keeping this format independent of Docling means chunking can be
re-run and tested without the heavy PDF parser.
"""

import json
import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

PARSED_DIR = Path("data/parsed")


class ElementType(StrEnum):
    HEADING = "heading"
    TEXT = "text"
    TABLE = "table"  # text is a Markdown table
    CAPTION = "caption"  # a caption not attached to a table or figure
    FIGURE = "figure"  # figure caption + text found inside the figure


class Element(BaseModel):
    paper: str  # short_name from data/SOURCES.md
    page: int = Field(ge=1)  # first physical PDF page, 1-based
    # every page the element appears on: a paragraph can continue on the next page
    pages: list[int] = []
    section: str  # nearest preceding section heading, "" before the first one
    type: ElementType
    text: str

    @model_validator(mode="after")
    def _default_pages(self) -> "Element":
        if not self.pages:
            self.pages = [self.page]
        return self


def save_elements(elements: list[Element], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (e.model_dump_json() for e in elements)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_elements(path: Path) -> list[Element]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Element.model_validate(json.loads(line)) for line in lines if line.strip()]


# "3.2 Training", "A Appendix": a numbered section heading
_NUMBERED = re.compile(r"^(?:\d+|[A-Z])(?:\.\d+)*\.?\s")
FRONT_MATTER_HEADINGS = {"abstract", "introduction"}


def demote_front_matter_headings(elements: list[Element]) -> tuple[list[Element], int]:
    """Turn page-1 author-block "headings" into text and recompute every section.

    Docling sometimes labels author names on the first page as section headers
    ("Matei Zaharia" in the middle of ARES's introduction), so the following paragraphs
    were cited as "§Matei Zaharia". On page 1, an unnumbered heading counts only if it
    is the document title (the first heading), "Abstract" or "Introduction".
    Returns the new elements and how many headings were demoted.
    """
    out: list[Element] = []
    section, seen_heading, demoted = "", False, 0
    for e in elements:
        if e.type == ElementType.HEADING:
            is_front_matter = (
                e.page == 1
                and seen_heading
                and not _NUMBERED.match(e.text)
                and e.text.strip().lower() not in FRONT_MATTER_HEADINGS
            )
            seen_heading = True
            if is_front_matter:
                demoted += 1
                out.append(e.model_copy(update={"type": ElementType.TEXT, "section": section}))
                continue
            section = e.text
        out.append(e.model_copy(update={"section": section}))
    return out, demoted
