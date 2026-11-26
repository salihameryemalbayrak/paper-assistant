"""Machine verification of eval questions that no human checked (verified=false).

The questions and expected answers are drafted by an LLM (Claude). Instead of a human
reading every PDF page, each unverified question carries evidence that is checked here
against the parsed text the system itself sees (data/parsed/<paper>.jsonl):

- evidence: every quote must appear on the cited page (case and whitespace ignored).
  Catches a wrong page, a wrong document and misremembered or invented quotes.
- absent_terms (unanswerable questions): none of the words may appear anywhere in the
  named document.

Not caught: a correct quote misread into a wrong answer (e.g. a wrong subtraction), or
an ambiguous question. See docs/DECISIONS.md, D35.

Needs data/parsed/ (not in git), so it runs locally, not in CI.

Usage:
    uv run python -m eval.check_evidence
"""

import re
import sys
from collections.abc import Iterable

from eval.dataset import EvalItem, QuestionType


def normalize(text: str) -> str:
    """Collapse whitespace and lowercase ("İ" first: Python's lower() adds a combining dot)."""
    return re.sub(r"\s+", " ", text.replace("İ", "i")).strip().lower()


def missing_quotes(item: EvalItem, page_text: dict[tuple[str, int], str]) -> list[str]:
    """Evidence quotes not found on their cited page."""
    return [
        e.quote
        for e in item.evidence
        if normalize(e.quote) not in normalize(page_text.get((e.paper, e.page), ""))
    ]


def present_terms(item: EvalItem, doc_text: dict[str, str]) -> list[str]:
    """Absent terms that do appear in the document: the question is answerable after all."""
    return [
        f"{paper}: {term}"
        for paper, terms in item.absent_terms.items()
        for term in terms
        if normalize(term) in normalize(doc_text.get(paper, ""))
    ]


def build_texts(elements: Iterable) -> tuple[dict[tuple[str, int], str], dict[str, str]]:
    """(paper, page) -> text of that page, and paper -> whole document text."""
    pages: dict[tuple[str, int], list[str]] = {}
    docs: dict[str, list[str]] = {}
    for e in elements:
        for page in e.pages:
            pages.setdefault((e.paper, page), []).append(e.text)
        docs.setdefault(e.paper, []).append(e.text)
    return (
        {key: "\n".join(texts) for key, texts in pages.items()},
        {key: "\n".join(texts) for key, texts in docs.items()},
    )


def main() -> None:
    from eval.dataset import load_dataset
    from eval.run import DATASET
    from ingest.elements import PARSED_DIR, load_elements

    items = load_dataset(DATASET)
    elements = [e for path in sorted(PARSED_DIR.glob("*.jsonl")) for e in load_elements(path)]
    page_text, doc_text = build_texts(elements)

    human = [i for i in items if i.verified]
    machine = [i for i in items if not i.verified]
    failures = 0
    for item in machine:
        if item.type == QuestionType.UNANSWERABLE:
            problems = [f"found in document: {t}" for t in present_terms(item, doc_text)]
        else:
            problems = [f"quote not on its page: {q[:70]}" for q in missing_quotes(item, page_text)]
        failures += bool(problems)
        status = "FAIL" if problems else "ok  "
        print(f"{status} {item.id}" + "".join(f"\n       {p}" for p in problems))

    print(f"\n{len(items)} questions: {len(human)} verified by a human, "
          f"{len(machine) - failures} by evidence, {failures} failed")  # fmt: skip
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
