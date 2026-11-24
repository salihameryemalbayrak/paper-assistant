"""Download the papers listed in data/SOURCES.md into data/raw/.

For each paper the license is re-checked against arXiv's metadata (OAI-PMH)
before downloading; papers without an allowed open license are refused.
Already downloaded files are skipped.

Usage:
    uv run python -m ingest.download
"""

import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SOURCES_FILE = Path("data/SOURCES.md")
RAW_DIR = Path("data/raw")

ALLOWED_LICENSES = {
    "http://creativecommons.org/licenses/by/4.0/",
    "http://creativecommons.org/licenses/by/3.0/",
    "http://creativecommons.org/publicdomain/zero/1.0/",
}

# arXiv asks automated clients to wait ~3 seconds between requests.
REQUEST_DELAY_S = 3.0
USER_AGENT = "paper-assistant/0.1 (research project)"
OAI_URL = "https://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{id}&metadataPrefix=arXiv"
PDF_URL = "https://arxiv.org/pdf/{id}"
_OAI_NS = {"a": "http://arxiv.org/OAI/arXiv/"}


@dataclass(frozen=True)
class Source:
    short_name: str
    arxiv_id: str  # with pinned version, e.g. "2309.15217v2"
    title: str

    @property
    def base_id(self) -> str:
        """arXiv id without the version suffix ("2309.15217v2" -> "2309.15217")."""
        return self.arxiv_id.split("v")[0]


def parse_sources(markdown: str) -> list[Source]:
    """Read the first Markdown table; columns are matched by header name."""
    rows = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    if not rows:
        return []

    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header = cells(rows[0])
    sources = []
    for row in rows[2:]:  # skip header and the |---|---| separator
        record = dict(zip(header, cells(row), strict=True))
        sources.append(
            Source(
                short_name=record["short_name"],
                arxiv_id=record["arxiv_id"],
                title=record["title"],
            )
        )
    return sources


def is_allowed_license(license_url: str | None) -> bool:
    return license_url in ALLOWED_LICENSES


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_license(base_id: str) -> str | None:
    root = ET.fromstring(_get(OAI_URL.format(id=base_id)))
    return root.findtext(".//a:arXiv/a:license", default=None, namespaces=_OAI_NS)


def download(source: Source, out_dir: Path) -> Path:
    target = out_dir / f"{source.short_name}.pdf"
    data = _get(PDF_URL.format(id=source.arxiv_id))
    if not data.startswith(b"%PDF"):
        raise ValueError(f"{source.arxiv_id}: response is not a PDF")
    target.write_bytes(data)
    return target


def main() -> None:
    sources = parse_sources(SOURCES_FILE.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for source in sources:
        target = RAW_DIR / f"{source.short_name}.pdf"
        if target.exists():
            print(f"skip      {source.short_name} (already downloaded)")
            continue

        license_url = fetch_license(source.base_id)
        time.sleep(REQUEST_DELAY_S)
        if not is_allowed_license(license_url):
            print(f"REFUSED   {source.short_name}: license {license_url!r} is not allowed")
            continue

        path = download(source, RAW_DIR)
        time.sleep(REQUEST_DELAY_S)
        print(f"ok        {source.short_name} -> {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
