"""Turn parsed elements into retrieval chunks.

Rules (see docs/DECISIONS.md, D20):
- A chunk never crosses a section or a page boundary (citations are per page and section).
- Paragraphs are merged up to TARGET_TOKENS; a paragraph above MAX_TOKENS is split at
  sentence boundaries with a small overlap.
- A table is one chunk; a table above MAX_TOKENS is split into row groups, and every
  piece repeats the caption and the header row so the numbers stay interpretable.
- A figure caption is its own chunk.
- `search_text` (used for embedding and BM25) is prefixed with "paper title > section";
  `text` (shown to the LLM and the user) is the original content.

Usage:
    uv run python -m ingest.chunk
"""

import json
import math
from collections import Counter
from enum import StrEnum
from itertools import groupby
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from ingest.download import SOURCES_FILE, parse_sources
from ingest.elements import PARSED_DIR, Element, ElementType, load_elements

CHUNKS_FILE = Path("data/chunks.jsonl")

# multilingual-e5-small reads at most 512 tokens; MAX_TOKENS leaves a safety margin
# because estimate_tokens() is only an approximation until the real tokenizer is used.
TARGET_TOKENS = 300
MAX_TOKENS = 400
SPLIT_OVERLAP_TOKENS = 30


def estimate_tokens(text: str) -> int:
    """Rough token count for English text: ~1.3 tokens per whitespace-separated word."""
    return math.ceil(len(text.split()) * 1.3)


class ChunkType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"  # a figure caption


class Chunk(BaseModel):
    id: str
    paper: str
    page: int = Field(ge=1)  # page the chunk starts on
    pages: list[int]  # every page its content appears on (a paragraph may continue)
    section: str
    type: ChunkType
    text: str  # original content, shown to the LLM and the user
    search_text: str  # "title > section" header + text, used for embedding and BM25


def split_table(markdown: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    """Split a Markdown table into row groups; each piece keeps the caption and header."""
    if estimate_tokens(markdown) <= max_tokens:
        return [markdown]
    lines = markdown.splitlines()
    first_row = next((i for i, line in enumerate(lines) if line.startswith("|")), None)
    if first_row is None or len(lines) < first_row + 3:  # not a table we understand
        return [markdown]

    caption = "\n".join(lines[:first_row]).strip()
    header = lines[first_row : first_row + 2]  # header row + |---| separator
    rows = lines[first_row + 2 :]
    prefix = ([caption, ""] if caption else []) + header

    pieces: list[str] = []
    group: list[str] = []
    for row in rows:
        candidate = "\n".join(prefix + group + [row])
        if group and estimate_tokens(candidate) > max_tokens:
            pieces.append("\n".join(prefix + group))
            group = []
        group.append(row)
    if group:
        pieces.append("\n".join(prefix + group))
    return pieces


_sentence_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_TOKENS,
    chunk_overlap=SPLIT_OVERLAP_TOKENS,
    length_function=estimate_tokens,
    separators=["\n\n", "\n", ". ", "; ", ", ", " "],
    keep_separator="end",  # keep the period at the end of its sentence
)


Piece = tuple[list[Element], ChunkType, str]  # (source elements, chunk type, chunk text)


def _split_if_long(text: str) -> list[str]:
    if estimate_tokens(text) <= MAX_TOKENS:
        return [text]
    return _sentence_splitter.split_text(text)


def _chunk_group(group: list[Element]) -> list[Piece]:
    """Chunk elements that share one section and one page."""
    pieces: list[Piece] = []
    buffer: list[Element] = []  # consecutive paragraphs waiting to be merged

    def flush() -> None:
        if buffer:
            pieces.append((list(buffer), ChunkType.TEXT, "\n\n".join(e.text for e in buffer)))
            buffer.clear()

    for element in group:
        if element.type == ElementType.HEADING:
            continue  # the heading is carried in `section` and in search_text
        if element.type == ElementType.TABLE:
            flush()
            pieces += [([element], ChunkType.TABLE, t) for t in split_table(element.text)]
        elif element.type in (ElementType.FIGURE, ElementType.CAPTION):
            flush()
            for text in _split_if_long(element.text):
                pieces.append(([element], ChunkType.FIGURE, text))
        elif estimate_tokens(element.text) > MAX_TOKENS:
            flush()
            for text in _split_if_long(element.text):
                pieces.append(([element], ChunkType.TEXT, text))
        else:
            buffer_tokens = sum(estimate_tokens(e.text) for e in buffer)
            if buffer and buffer_tokens + estimate_tokens(element.text) > TARGET_TOKENS:
                flush()
            buffer.append(element)
    flush()
    return pieces


def chunk_paper(elements: list[Element], title: str) -> list[Chunk]:
    """Chunk the elements of one paper (in reading order)."""
    pieces: list[Piece] = []
    for _key, group in groupby(elements, key=lambda e: (e.section, e.page)):
        pieces += _chunk_group(list(group))

    chunks = []
    for n, (sources, chunk_type, text) in enumerate(pieces):
        element = sources[0]
        header = f"{title} > {element.section}" if element.section else title
        chunks.append(
            Chunk(
                id=f"{element.paper}-{n:04d}",
                paper=element.paper,
                page=element.page,
                pages=sorted({page for e in sources for page in e.pages}),
                section=element.section,
                type=chunk_type,
                text=text,
                search_text=f"{header}\n{text}",
            )
        )
    return chunks


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(c.model_dump_json() for c in chunks) + "\n", encoding="utf-8")


def load_chunks(path: Path = CHUNKS_FILE) -> list[Chunk]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Chunk.model_validate(json.loads(line)) for line in lines if line.strip()]


def main() -> None:
    titles = {s.short_name: s.title for s in parse_sources(SOURCES_FILE.read_text("utf-8"))}
    chunks: list[Chunk] = []
    for path in sorted(PARSED_DIR.glob("*.jsonl")):
        chunks += chunk_paper(load_elements(path), title=titles[path.stem])
    save_chunks(chunks, CHUNKS_FILE)

    sizes = sorted(estimate_tokens(c.text) for c in chunks)
    print(f"{len(chunks)} chunks -> {CHUNKS_FILE}")
    print("by type :", dict(Counter(c.type.value for c in chunks)))
    print("by paper:", dict(Counter(c.paper for c in chunks)))
    print(
        f"est. tokens: median={sizes[len(sizes) // 2]} max={sizes[-1]} "
        f"over {MAX_TOKENS}: {sum(s > MAX_TOKENS for s in sizes)}"
    )


if __name__ == "__main__":
    main()
