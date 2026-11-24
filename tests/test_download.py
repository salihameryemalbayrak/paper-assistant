"""Offline tests for the download script (no network access)."""

from pathlib import Path

from ingest.download import Source, is_allowed_license, parse_sources

TABLE = """
# Sources

Some intro text.

| short_name | arxiv_id | title | license |
|---|---|---|---|
| ragas | 2309.15217v2 | Ragas: Automated Evaluation | CC BY 4.0 |
| e5 | 2212.03533v2 | Text Embeddings | CC BY 4.0 |
"""


def test_parse_sources_reads_rows_by_header():
    sources = parse_sources(TABLE)

    assert sources == [
        Source(short_name="ragas", arxiv_id="2309.15217v2", title="Ragas: Automated Evaluation"),
        Source(short_name="e5", arxiv_id="2212.03533v2", title="Text Embeddings"),
    ]


def test_base_id_strips_version():
    assert Source("x", "2309.15217v2", "t").base_id == "2309.15217"


def test_license_allow_list():
    assert is_allowed_license("http://creativecommons.org/licenses/by/4.0/")
    # arXiv's default license does not allow redistribution
    assert not is_allowed_license("http://arxiv.org/licenses/nonexclusive-distrib/1.0/")
    # ShareAlike and NonCommercial are excluded by the project's rules
    assert not is_allowed_license("http://creativecommons.org/licenses/by-sa/4.0/")
    assert not is_allowed_license("http://creativecommons.org/licenses/by-nc/4.0/")
    assert not is_allowed_license(None)


def test_real_sources_file_is_valid():
    sources = parse_sources(Path("data/SOURCES.md").read_text(encoding="utf-8"))

    assert len(sources) >= 5
    assert len({s.short_name for s in sources}) == len(sources), "short names must be unique"
    assert all("v" in s.arxiv_id for s in sources), "versions must be pinned"
