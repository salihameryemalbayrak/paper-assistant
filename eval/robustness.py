"""Robustness of retrieval to how a question is typed: all-lowercase vs original (D47).

Users do not always write names the way the papers do ("qlora", "ares"). For every
answerable eval question, four variants are translated (LLM) and searched with the default
retriever, and page recall@5 / evidence recall@5 are compared:

    original | original + truecase | lowercase | lowercase + truecase

Lowercase follows Turkish rules (I -> ı, İ -> i), as typed on a Turkish keyboard. Needs the
LLM for translation (~2 min on an M4), so it runs locally, not in CI.

Usage:
    uv run python -m eval.robustness
"""

import json
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

from app.config import get_settings
from app.llm import get_chat_model
from app.retrieval import build_retriever
from app.text import turkish_lower
from app.translate import build_translator
from app.truecase import load_vocabulary, truecase
from eval.dataset import QuestionType, load_dataset
from eval.retrieval_metrics import evidence_found, recall_at_k
from eval.run import DATASET, _git_commit, _hardware, corpus_info, to_hit, unique_path

OUT_DIR = Path("docs/benchmarks/robustness")


def main() -> None:
    settings = get_settings()
    items = [i for i in load_dataset(DATASET) if i.type != QuestionType.UNANSWERABLE]
    vocab = load_vocabulary()
    translate = build_translator(get_chat_model(settings))
    retriever = build_retriever(settings.retriever, 5, depth=settings.retrieval_depth)
    variants = {
        "original": lambda q: q,
        "original+truecase": lambda q: truecase(q, vocab),
        "lowercase": turkish_lower,
        "lowercase+truecase": lambda q: truecase(turkish_lower(q), vocab),
    }
    translations: dict[str, str] = {}
    start = time.perf_counter()
    results, per_question = {}, {i.id: {} for i in items}
    for name, variant in variants.items():
        recall, evidence = [], []
        for item in items:
            question = variant(item.question)
            if question not in translations:  # translation is deterministic: reuse it
                translations[question] = translate.invoke(question)
            docs = retriever.invoke({"tr": question, "en": translations[question]})
            recall.append(recall_at_k([to_hit(d) for d in docs], item.sources, 5))
            if item.evidence:
                found = evidence_found([e.quote for e in item.evidence],
                                       [d.metadata["text"] for d in docs], 5)  # fmt: skip
                evidence.append(mean(found))
                per_question[item.id][name] = round(mean(found), 3)
        results[name] = {"recall@5": round(mean(recall), 4),
                         "evidence_recall@5": round(mean(evidence), 4)}  # fmt: skip
        print(f"{name:<20} recall@5 {mean(recall):.3f} | evidence recall@5 {mean(evidence):.3f}")

    result = {
        "mode": "robustness",
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "corpus": corpus_info(),
        "retriever": settings.retriever,
        "retrieval_depth": settings.retrieval_depth,
        "translation_llm": settings.llm_model,
        "questions": len(items),
        "vocabulary_size": len(vocab),
        "seconds": round(time.perf_counter() - start),
        "results": results,
        "per_question_evidence_recall@5": per_question,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = unique_path(OUT_DIR / f"{result['date'][:10]}_{result['corpus']['docs']}docs_"
                      f"{settings.retriever}_lowercase.json")  # fmt: skip
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
