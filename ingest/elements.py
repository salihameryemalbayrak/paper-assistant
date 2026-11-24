"""The project's own document format: a flat list of elements per paper.

The parse step (Docling) writes elements to data/parsed/<paper>.jsonl; the chunk
step reads them. Keeping this format independent of Docling means chunking can be
re-run and tested without the heavy PDF parser.
"""

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

PARSED_DIR = Path("data/parsed")


class ElementType(StrEnum):
    HEADING = "heading"
    TEXT = "text"
    TABLE = "table"  # text is a Markdown table
    CAPTION = "caption"  # figure or table caption


class Element(BaseModel):
    paper: str  # short_name from data/SOURCES.md
    page: int = Field(ge=1)  # physical PDF page, 1-based
    section: str  # nearest preceding section heading, "" before the first one
    type: ElementType
    text: str


def save_elements(elements: list[Element], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (e.model_dump_json() for e in elements)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_elements(path: Path) -> list[Element]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Element.model_validate(json.loads(line)) for line in lines if line.strip()]
