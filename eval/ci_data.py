"""Chunk file for the CI fast eval, published as a GitHub Release asset (D42).

The PDFs and the index stay out of git (CLAUDE.md). CI still needs the chunks to rebuild
an in-memory index, so a gzipped copy of data/chunks.jsonl is attached to a release, and
eval/ci_data.json (in git) records which release and which content (SHA-256):

    build   (local)  data/chunks.jsonl -> dist/ci-data/{chunks.jsonl.gz, NOTICE.md},
                     update eval/ci_data.json, print the `gh release create` command
    verify  (CI)     the downloaded file must have the recorded SHA-256

The release tag comes from the content hash, so every chunk version gets its own release
and old ones stay downloadable. The chunks are adapted CC BY 4.0 material: NOTICE.md
points to the attribution and the list of modifications in data/SOURCES.md.

Usage:
    uv run python -m eval.ci_data build
    uv run python -m eval.ci_data verify data/chunks.jsonl
"""

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

CHUNKS = Path("data/chunks.jsonl")
SOURCES = Path("data/SOURCES.md")
RECORD = Path("eval/ci_data.json")
OUT_DIR = Path("dist/ci-data")
ASSET = "chunks.jsonl.gz"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notice() -> str:
    attribution = SOURCES.read_text(encoding="utf-8").split("## Attribution", 1)[1]
    return (
        "# Chunk file for the CI fast eval\n\n"
        "Adapted text from the CC BY 4.0 papers below (https://creativecommons.org/licenses/by/4.0/).\n"
        "Authors, links, copyright notices and the modifications made are listed below and in\n"
        "data/SOURCES.md of the repository.\n\n## Attribution" + attribution
    )


def build() -> None:
    if not CHUNKS.exists():
        sys.exit(f"{CHUNKS} not found: run the ingest steps first")
    digest = sha256(CHUNKS)
    lines = CHUNKS.read_text(encoding="utf-8").splitlines()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # mtime=0: same content -> byte-identical .gz (gzip would store the creation time)
    with gzip.GzipFile(OUT_DIR / ASSET, "wb", mtime=0) as f:
        f.write(CHUNKS.read_bytes())
    (OUT_DIR / "NOTICE.md").write_text(notice(), encoding="utf-8")
    record = {
        "tag": f"ci-data-{digest[:12]}",
        "asset": ASSET,
        "sha256": digest,  # of the uncompressed data/chunks.jsonl
        "chunks": len(lines),
        "docs": len({json.loads(line)["paper"] for line in lines}),
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_DIR / ASSET} ({(OUT_DIR / ASSET).stat().st_size // 1024} KB) and {RECORD}")
    print("publish it (then commit eval/ci_data.json):")
    print(
        f"  gh release create {record['tag']} {OUT_DIR / ASSET} {OUT_DIR / 'NOTICE.md'} "
        f'--prerelease --title "CI eval data {digest[:12]}" --notes-file {OUT_DIR / "NOTICE.md"}'
    )


def verify(path: Path) -> None:
    expected = json.loads(RECORD.read_text(encoding="utf-8"))["sha256"]
    if (actual := sha256(path)) != expected:
        sys.exit(f"{path}: sha256 {actual[:12]} != {expected[:12]} recorded in {RECORD}")
    print(f"{path}: sha256 matches {RECORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("verify").add_argument("path", type=Path)
    args = parser.parse_args()
    build() if args.command == "build" else verify(args.path)


if __name__ == "__main__":
    main()
