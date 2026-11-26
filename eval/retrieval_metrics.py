"""Retrieval metrics: Recall@k and MRR, written by hand (no library).

Each retrieved hit is the set of (paper, page) pairs one retrieved chunk covers
(a chunk can span two pages when a paragraph continues on the next page). A hit is
relevant if it covers one of the expected sources of the question.

Unanswerable questions have no expected sources and are excluded here; they are
measured by refusal rate in the full eval.

Page-level hits are optimistic: the right page with the wrong chunk counts (D28, D36).
Evidence recall is the chunk-level check: for questions with evidence quotes, does the
retrieved text itself contain the sentences (or table rows) the answer needs?
"""

from collections.abc import Callable, Collection, Sequence
from statistics import mean

from eval.check_evidence import normalize
from eval.dataset import EvalItem, QuestionType, SourceRef

Hit = Collection[SourceRef]  # the (paper, page) pairs one retrieved chunk covers
# A retriever takes a question and returns hits ranked best-first.
Retriever = Callable[[str], Sequence[Hit]]


def recall_at_k(hits: Sequence[Hit], expected: Sequence[SourceRef], k: int) -> float:
    """Fraction of expected sources covered by the top-k hits."""
    if not expected:
        raise ValueError("recall is undefined without expected sources")
    covered = set().union(*hits[:k])
    return sum(source in covered for source in set(expected)) / len(set(expected))


def evidence_found(quotes: Sequence[str], texts: Sequence[str], k: int) -> list[bool]:
    """For each quote: is it inside one of the top-k retrieved chunk texts?"""
    top = [normalize(t) for t in texts[:k]]
    return [any(normalize(q) in t for t in top) for q in quotes]


def evidence_metrics(
    items: Sequence[EvalItem], texts: Callable[[str], Sequence[str]], ks: Sequence[int]
) -> dict[str, dict[str, float]]:
    """Chunk-level metrics over answerable questions that carry evidence quotes.

    evidence_recall@k: fraction of a question's quotes found in the top-k chunks.
    evidence_complete@k: 1 if all of them are found (a comparison or a table question
    can need two rows: one alone is not enough to answer).
    """
    groups: dict[str, list[dict[str, float]]] = {}
    for item in items:
        if item.type == QuestionType.UNANSWERABLE or not item.evidence:
            continue
        quotes = [e.quote for e in item.evidence]
        found = {k: evidence_found(quotes, texts(item.question), k) for k in ks}
        scores = {f"evidence_recall@{k}": mean(found[k]) for k in ks}
        scores |= {f"evidence_complete@{k}": float(all(found[k])) for k in ks}
        groups.setdefault("all", []).append(scores)
        groups.setdefault(item.type.value, []).append(scores)
    return {
        group: {"n": len(rows), **{name: mean(r[name] for r in rows) for name in rows[0]}}
        for group, rows in groups.items()
    }


def reciprocal_rank(hits: Sequence[Hit], expected: Sequence[SourceRef]) -> float:
    """1 / rank of the first relevant hit (rank starts at 1); 0 if none is relevant."""
    wanted = set(expected)
    for rank, hit in enumerate(hits, start=1):
        if wanted & set(hit):
            return 1.0 / rank
    return 0.0


def evaluate(
    items: Sequence[EvalItem], retrieve: Retriever, ks: Sequence[int] = (1, 3, 5, 10)
) -> dict[str, dict[str, float]]:
    """Run the retriever on every answerable question.

    Returns metrics overall, per question type and per phrasing ("~" prefix), e.g.
    {"all": {"n": 15, "recall@5": 0.8, "mrr": 0.62, ...}, "table": {...}, "~term": {...}}.
    """
    per_type: dict[str, list[dict[str, float]]] = {}
    for item in items:
        if item.type == QuestionType.UNANSWERABLE:
            continue
        hits = list(retrieve(item.question))
        scores = {f"recall@{k}": recall_at_k(hits, item.sources, k) for k in ks}
        scores["mrr"] = reciprocal_rank(hits, item.sources)
        per_type.setdefault("all", []).append(scores)
        per_type.setdefault(item.type.value, []).append(scores)
        per_type.setdefault(f"~{item.phrasing.value}", []).append(scores)

    return {
        group: {"n": len(rows), **{name: mean(r[name] for r in rows) for name in rows[0]}}
        for group, rows in per_type.items()
    }
