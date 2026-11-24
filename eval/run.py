"""Run the eval set against the retriever and save the results.

--fast: retrieval only (Recall@k, MRR), no LLM call. The full eval (RAGAS) comes in Phase 7.

Each run writes docs/benchmarks/fast_eval/<date>_<collection>.json with the model,
hardware, git commit and per-question results, so every reported number is traceable.

Usage:
    uv run python -m eval.run --fast                       # model from EMBEDDING_MODEL
    uv run python -m eval.run --fast --model BAAI/bge-m3
"""

import argparse
import json
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from statistics import median

from langchain_core.documents import Document

from app.config import get_settings
from app.vectorstore import collection_name, get_vectorstore
from eval.dataset import QuestionType, SourceRef, load_dataset
from eval.retrieval_metrics import Hit, evaluate, reciprocal_rank

DATASET = Path("eval/dataset.jsonl")
RESULTS_DIR = Path("docs/benchmarks/fast_eval")
TOP_K = 10  # retrieve this many chunks; Recall@k is reported for k <= TOP_K
KS = (1, 3, 5, 10)


def to_hit(doc: Document) -> Hit:
    """The (paper, page) pairs a retrieved chunk covers (see eval/retrieval_metrics.py)."""
    return {SourceRef(paper=doc.metadata["paper"], page=p) for p in doc.metadata["pages"]}


def _git_commit() -> str:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()

    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    return commit + ("-dirty" if git("status", "--porcelain") else "")


def _hardware() -> str:
    if platform.system() == "Darwin":
        cpu = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        ).stdout.strip()
        return f"{cpu or platform.machine()}, macOS {platform.mac_ver()[0]}"
    return f"{platform.processor() or platform.machine()}, {platform.system()}"


def run_fast(model: str) -> dict:
    items = load_dataset(DATASET)
    retriever = get_vectorstore(model).as_retriever(search_kwargs={"k": TOP_K})

    retriever.invoke("warm-up")  # first call loads the model; keep it out of the timings
    cache: dict[str, list[Hit]] = {}
    latencies_ms: list[float] = []

    def retrieve(question: str) -> list[Hit]:
        start = time.perf_counter()
        docs = retriever.invoke(question)
        latencies_ms.append((time.perf_counter() - start) * 1000)
        cache[question] = [to_hit(d) for d in docs]
        return cache[question]

    metrics = evaluate(items, retrieve, ks=KS)

    per_question = []
    for item in items:
        if item.type == QuestionType.UNANSWERABLE:
            continue
        rr = reciprocal_rank(cache[item.question], item.sources)
        per_question.append(
            {
                "id": item.id,
                "type": item.type.value,
                "first_relevant_rank": round(1 / rr) if rr else None,
            }
        )

    return {
        "mode": "fast",
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "embedding_model": model,
        "collection": collection_name(model),
        "retrieval": f"dense only, Turkish query (no translation), top_k={TOP_K}",
        "dataset": {"file": str(DATASET), "answerable": len(per_question), "total": len(items)},
        "latency_ms_median": round(median(latencies_ms), 1),
        "metrics": metrics,
        "per_question": per_question,
    }


def print_summary(result: dict) -> None:
    print(f"\n{result['embedding_model']} | {result['retrieval']} | {result['hardware']}")
    columns = ["n", *(f"recall@{k}" for k in KS), "mrr"]
    print(f"{'group':<12}" + "".join(f"{c:>10}" for c in columns))
    for group, values in result["metrics"].items():
        cells = "".join(f"{values[c]:>10}" if c == "n" else f"{values[c]:>10.3f}" for c in columns)
        print(f"{group:<12}{cells}")
    missed = [q["id"] for q in result["per_question"] if q["first_relevant_rank"] is None]
    print(f"median query latency: {result['latency_ms_median']} ms | not in top {TOP_K}: {missed}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fast", action="store_true", help="retrieval metrics only, no LLM")
    parser.add_argument("--model", help="embedding model id (default: EMBEDDING_MODEL)")
    args = parser.parse_args()
    if not args.fast:
        parser.error("only --fast is implemented so far (the full eval comes in Phase 7)")

    model = args.model or get_settings().embedding_model
    result = run_fast(model)
    print_summary(result)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{result['date'][:10]}_{result['collection']}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
