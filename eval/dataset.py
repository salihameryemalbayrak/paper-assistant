"""Eval set schema and loader.

Relevance is defined by (paper, page), not by chunk ids, so the eval set stays
valid when the chunking strategy changes. Pages are physical PDF pages (1-based),
as shown by a PDF viewer, not the numbers printed on the page.
"""

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class QuestionType(StrEnum):
    SINGLE_PAGE = "single_page"
    TABLE = "table"
    FIGURE = "figure"
    COMPARISON = "comparison"
    UNANSWERABLE = "unanswerable"  # "dokümanda yok": the system should refuse


class Phrasing(StrEnum):
    """How the question is worded relative to its source (reported separately)."""

    TERM = "term"  # uses the source's own distinctive terms ("QLoRA's three innovations")
    PARAPHRASE = "paraphrase"  # same meaning in other words; only the document is named
    INFERENCE = "inference"  # the answer is not stated verbatim; derived from 2+ facts


class SourceRef(BaseModel, frozen=True):
    paper: str  # short_name from data/SOURCES.md
    page: int = Field(ge=1)


class Evidence(BaseModel):
    """A sentence copied verbatim from the parsed text of a source page."""

    paper: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=20)  # long enough to be specific


class EvalItem(BaseModel):
    id: str
    type: QuestionType
    phrasing: Phrasing  # required: an unlabeled question must not count as "term"
    question: str
    answer: str
    sources: list[SourceRef] = []
    notes: str = ""
    # Set to true only after a human has checked the answer against the PDF page.
    verified: bool = False
    # Machine verification for questions no human checked (eval/check_evidence.py):
    # quotes that must appear on the source pages, and for unanswerable questions,
    # words that must not appear anywhere in the named document.
    evidence: list[Evidence] = []
    absent_terms: dict[str, list[str]] = {}

    @model_validator(mode="after")
    def _check_sources(self) -> "EvalItem":
        if self.type == QuestionType.UNANSWERABLE and self.sources:
            raise ValueError(f"{self.id}: unanswerable questions must not have sources")
        if self.type != QuestionType.UNANSWERABLE and not self.sources:
            raise ValueError(f"{self.id}: answerable questions need at least one source")
        if self.type == QuestionType.COMPARISON and len({s.paper for s in self.sources}) < 2:
            raise ValueError(f"{self.id}: comparison questions need sources from 2+ papers")
        if not self.verified:
            self._check_machine_verifiable()
        return self

    def _check_machine_verifiable(self) -> None:
        """An unverified question needs evidence for every source (or absent terms)."""
        if self.type == QuestionType.UNANSWERABLE:
            if not any(self.absent_terms.values()):
                raise ValueError(f"{self.id}: unverified unanswerable question needs absent_terms")
            return
        quoted = {SourceRef(paper=e.paper, page=e.page) for e in self.evidence}
        if missing := [s for s in self.sources if s not in quoted]:
            raise ValueError(f"{self.id}: unverified question has no evidence for {missing}")


def load_dataset(path: Path) -> list[EvalItem]:
    items = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(EvalItem.model_validate(json.loads(line)))
        except ValueError as e:
            raise ValueError(f"{path}:{line_no}: {e}") from e
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate question ids")
    return items
