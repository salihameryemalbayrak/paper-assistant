"""Retrieval metrics: Recall@k and MRR, written by hand (no library).

A retrieved hit is relevant if its (paper, page) matches one of the expected
sources of the question. Unanswerable questions have no expected sources and
are excluded here; they are measured by refusal rate in the full eval.
"""

from collections.abc import Callable, Sequence
from statistics import mean

from eval.dataset import EvalItem, QuestionType, SourceRef

# A retriever takes a question and returns hits ranked best-first.
Retriever = Callable[[str], Sequence[SourceRef]]


def recall_at_k(hits: Sequence[SourceRef], expected: Sequence[SourceRef], k: int) -> float:
    """Fraction of expected sources that appear among the top-k hits."""
    if not expected:
        raise ValueError("recall is undefined without expected sources")
    top_k = set(hits[:k])
    return sum(source in top_k for source in set(expected)) / len(set(expected))


def reciprocal_rank(hits: Sequence[SourceRef], expected: Sequence[SourceRef]) -> float:
    """1 / rank of the first relevant hit (rank starts at 1); 0 if none is relevant."""
    wanted = set(expected)
    for rank, hit in enumerate(hits, start=1):
        if hit in wanted:
            return 1.0 / rank
    return 0.0


def evaluate(
    items: Sequence[EvalItem], retrieve: Retriever, ks: Sequence[int] = (1, 3, 5, 10)
) -> dict[str, dict[str, float]]:
    """Run the retriever on every answerable question.

    Returns metrics overall and per question type, e.g.
    {"all": {"n": 15, "recall@5": 0.8, "mrr": 0.62, ...}, "table": {...}}.
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

    return {
        group: {"n": len(rows), **{name: mean(r[name] for r in rows) for name in rows[0]}}
        for group, rows in per_type.items()
    }
