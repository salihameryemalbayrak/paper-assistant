import re

from ingest.chunk import MAX_TOKENS, TARGET_TOKENS, estimate_tokens, short_caption
from ingest.chunk import chunk_paper as _chunk_paper
from ingest.chunk import split_table as _split_table
from ingest.elements import Element, ElementType

TITLE = "A Paper"


# The tests count tokens with the word-based estimate so they need no tokenizer download.
def chunk_paper(elements: list[Element], title: str):
    return _chunk_paper(elements, title, estimate_tokens)


def split_table(markdown: str) -> list[str]:
    return _split_table(markdown, estimate_tokens)


def el(
    type_: str, text: str, page: int = 1, section: str = "1 Intro", pages: list[int] | None = None
) -> Element:
    return Element(
        paper="p",
        page=page,
        pages=pages or [page],
        section=section,
        type=ElementType(type_),
        text=text,
    )


def words(n: int, word: str = "word") -> str:
    return " ".join([word] * n)


def test_small_paragraphs_are_merged_and_headings_dropped():
    chunks = chunk_paper(
        [el("heading", "1 Intro"), el("text", "First paragraph."), el("text", "Second one.")],
        TITLE,
    )
    assert len(chunks) == 1
    assert chunks[0].text == "First paragraph.\n\nSecond one."


def test_merging_stops_near_target_size():
    paragraph = words(100)  # ~130 tokens each
    chunks = chunk_paper([el("text", paragraph) for _ in range(5)], TITLE)
    assert len(chunks) > 1
    assert all(estimate_tokens(c.text) <= TARGET_TOKENS for c in chunks)


def test_chunks_never_cross_section_or_page():
    chunks = chunk_paper(
        [
            el("text", "a", page=1, section="1 Intro"),
            el("text", "b", page=1, section="2 Method"),
            el("text", "c", page=2, section="2 Method"),
        ],
        TITLE,
    )
    assert [(c.section, c.page, c.text) for c in chunks] == [
        ("1 Intro", 1, "a"),
        ("2 Method", 1, "b"),
        ("2 Method", 2, "c"),
    ]


def test_long_paragraph_is_split_at_sentences():
    sentence = words(20) + ". "
    chunks = chunk_paper([el("text", sentence * 30)], TITLE)  # ~800 tokens
    assert len(chunks) > 1
    assert all(estimate_tokens(c.text) <= MAX_TOKENS for c in chunks)
    assert all(c.text.endswith(".") for c in chunks), "pieces should end at a sentence"


def test_caption_becomes_figure_chunk():
    chunks = chunk_paper([el("text", "Body."), el("caption", "Figure 1: Overview.")], TITLE)
    assert [(c.type, c.text) for c in chunks] == [
        ("text", "Body."),
        ("figure", "Figure 1: Overview."),
    ]


def test_search_text_has_context_header_but_text_does_not():
    chunks = chunk_paper([el("text", "We set k = 2.", section="3 CCPairs")], TITLE)
    assert chunks[0].search_text == "A Paper > 3 CCPairs\nWe set k = 2."
    assert chunks[0].text == "We set k = 2."


def test_ids_are_unique_and_ordered():
    chunks = chunk_paper([el("text", "a", page=1), el("text", "b", page=2)], TITLE)
    assert [c.id for c in chunks] == ["p-0000", "p-0001"]


def test_turkish_text_is_preserved():
    chunks = chunk_paper([el("text", "Şekil 2'de ığdır ve İstanbul örnekleri.")], TITLE)
    assert chunks[0].text == "Şekil 2'de ığdır ve İstanbul örnekleri."


TABLE = "\n".join(
    ["Table 2: Recall@100 per language.", "", "| lang | BM25 | Dense |", "|---|---|---|"]
    + [f"| l{i} | {i}.1 | {i}.2 |" for i in range(200)]
)


def test_small_table_is_one_chunk():
    small = "Table 1: x\n\n| a | b |\n|---|---|\n| 1 | 2 |"
    assert split_table(small) == [small]


def test_big_table_pieces_repeat_caption_and_header_and_keep_every_row():
    pieces = split_table(TABLE)

    assert len(pieces) > 1
    for piece in pieces:
        assert piece.startswith("Table 2: Recall@100 per language.")
        assert "| lang | BM25 | Dense |\n|---|---|---|" in piece
        assert estimate_tokens(piece) <= MAX_TOKENS
    # data rows are "| l<number> |"; the repeated header row "| lang |" must not be counted
    data_rows = [line for p in pieces for line in p.splitlines() if re.match(r"\| l\d", line)]
    assert data_rows == [f"| l{i} | {i}.1 | {i}.2 |" for i in range(200)]


def test_big_table_element_becomes_several_table_chunks():
    chunks = chunk_paper([el("table", TABLE, page=7)], TITLE)
    assert len(chunks) > 1
    assert all(c.type == "table" and c.page == 7 for c in chunks)


def test_chunk_pages_include_continued_paragraphs():
    chunks = chunk_paper(
        [
            el("text", "Starts on page 2 ...", page=2, pages=[2, 3]),
            el("text", "Same page.", page=2),
        ],
        TITLE,
    )
    assert (chunks[0].page, chunks[0].pages) == (2, [2, 3])


def test_figure_element_becomes_figure_chunk():
    text = "Figure 1: Overview.\n\n[Figure text] Retriever | No Retrieval"
    chunks = chunk_paper([el("figure", text)], TITLE)
    assert [(c.type, c.text) for c in chunks] == [("figure", text)]


def test_token_counter_drives_the_sizes():
    """A table that fits by word count is split when the counter says it is too long."""
    table = "Table 1: x\n\n| a | b |\n|---|---|\n" + "\n".join(
        f"| {i} | 0.{i} |" for i in range(40)
    )
    assert _split_table(table, estimate_tokens) == [table]
    pieces = _split_table(table, lambda text: 4 * len(text.split()))  # numbers: more tokens
    assert len(pieces) > 1


def test_author_names_on_page_one_are_not_sections():
    from ingest.elements import Element, ElementType, demote_front_matter_headings

    def el(text, type_=ElementType.TEXT, page=1):
        return Element(paper="ares", page=page, section="?", type=type_, text=text)

    H = ElementType.HEADING
    elements = [
        el("ARES: An Automated Evaluation Framework", H),  # title: kept
        el("Christopher Potts", H),  # author: demoted
        el("Abstract", H),
        el("We introduce ARES."),
        el("1 Introduction", H),
        el("Matei Zaharia", H),  # author block in the middle of the introduction
        el("RAG systems are evaluated ..."),
        el("Related Work", H, page=2),  # unnumbered, but not on page 1: kept
        el("Prior work ...", page=2),
    ]

    out, demoted = demote_front_matter_headings(elements)

    assert demoted == 2
    assert [(e.type.value, e.section) for e in out] == [
        ("heading", "ARES: An Automated Evaluation Framework"),
        ("text", "ARES: An Automated Evaluation Framework"),
        ("heading", "Abstract"),
        ("text", "Abstract"),
        ("heading", "1 Introduction"),
        ("text", "1 Introduction"),
        ("text", "1 Introduction"),  # was "Matei Zaharia"
        ("heading", "Related Work"),
        ("text", "Related Work"),
    ]


def test_long_table_caption_is_indexed_once_and_shortened_in_pieces():
    explanation = " ".join(["word"] * 60)
    caption = f"Table 1: ARES Ranking vs. RAGAS: {explanation}"
    table = "\n".join(
        [caption, "", "| a | b |", "|---|---|", *[f"| r{i} | {i} |" for i in range(40)]]
    )
    count = lambda text: len(text.split())  # noqa: E731  one token per word

    pieces = _split_table(table, count, max_tokens=100)

    assert short_caption(caption) == "Table 1: ARES Ranking vs. RAGAS"
    assert pieces[0] == caption  # the full caption, once
    assert all(p.startswith("Table 1: ARES Ranking vs. RAGAS\n") for p in pieces[1:])
    assert all(count(p) <= 100 for p in pieces)
    rows = [line for p in pieces[1:] for line in p.splitlines() if line.startswith("| r")]
    assert len(rows) == 40  # every row kept exactly once


def test_short_caption_falls_back_to_first_words():
    assert short_caption("Table 2: Overall results on six tasks.") == (
        "Table 2: Overall results on six tasks."
    )
    assert short_caption(" ".join(["w"] * 50)) == " ".join(["w"] * 30)
