"""Run the eval set and save the results.

--fast:    retrieval only (Recall@k, MRR), no LLM call.
--answers: the full chain (retriever -> prompt -> LLM) on every question, with simple
           automatic checks: correct refusals, false refusals, missing or invented citations.
The full eval with RAGAS (faithfulness, answer relevancy) comes in Phase 7.

Each run writes a JSON file under docs/benchmarks/ with the models, hardware, git commit
and per-question results, so every reported number is traceable.

Usage:
    uv run python -m eval.run --fast                       # model from EMBEDDING_MODEL
    uv run python -m eval.run --fast --model BAAI/bge-m3
    uv run python -m eval.run --answers
"""

import argparse
import json
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from statistics import median

from langchain_core.documents import Document

from app.ask import CONTEXT_K, build_chain, check_citations, extract_citations, is_refusal
from app.bm25 import load_bm25_retriever
from app.config import get_settings
from app.llm import get_chat_model
from app.vectorstore import collection_name, get_vectorstore
from eval.dataset import QuestionType, SourceRef, load_dataset
from eval.retrieval_metrics import Hit, evaluate, reciprocal_rank

DATASET = Path("eval/dataset.jsonl")
RESULTS_DIR = Path("docs/benchmarks/fast_eval")
ANSWERS_DIR = Path("docs/benchmarks/answers")
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


RETRIEVERS = ("dense", "bm25")


def build_retriever(name: str, model: str):
    """Every retriever has the same LangChain interface: invoke(question) -> list[Document]."""
    if name == "dense":
        return get_vectorstore(model).as_retriever(search_kwargs={"k": TOP_K})
    if name == "bm25":
        return load_bm25_retriever(k=TOP_K)
    raise ValueError(f"unknown retriever: {name}")


def run_fast(model: str, retriever_name: str = "dense") -> dict:
    items = load_dataset(DATASET)
    retriever = build_retriever(retriever_name, model)

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
        "run_name": f"dense_{collection_name(model)}" if retriever_name == "dense" else "bm25",
        "retriever": retriever_name,
        "embedding_model": model if retriever_name == "dense" else None,
        "retrieval": f"{retriever_name} only, Turkish query (no translation), top_k={TOP_K}",
        "dataset": {"file": str(DATASET), "answerable": len(per_question), "total": len(items)},
        "latency_ms_median": round(median(latencies_ms), 1),
        "metrics": metrics,
        "per_question": per_question,
    }


def run_answers(model: str) -> dict:
    settings = get_settings()
    items = load_dataset(DATASET)
    retriever = get_vectorstore(model).as_retriever(search_kwargs={"k": CONTEXT_K})
    chain = build_chain(retriever, get_chat_model(settings))
    chain.invoke("warm-up")  # loads the embedding model and the LLM

    rows = []
    for item in items:
        start = time.perf_counter()
        out = chain.invoke(item.question)
        seconds = time.perf_counter() - start
        answer = out["answer"].strip()
        answerable = item.type != QuestionType.UNANSWERABLE
        hits = [to_hit(d) for d in out["docs"]]
        rows.append(
            {
                "id": item.id,
                "type": item.type.value,
                "question": item.question,
                "expected": item.answer,
                "answer": answer,
                "refused": is_refusal(answer),
                # did the context contain an expected page? (retrieval succeeded)
                "context_has_source": answerable and reciprocal_rank(hits, item.sources) > 0,
                "citations": extract_citations(answer),
                "invented_citations": check_citations(answer, out["docs"]),
                "context": [d.metadata["chunk_id"] for d in out["docs"]],
                "seconds": round(seconds, 1),
            }
        )

    answerable = [r for r in rows if r["type"] != QuestionType.UNANSWERABLE]
    unanswerable = [r for r in rows if r["type"] == QuestionType.UNANSWERABLE]
    answered = [r for r in answerable if not r["refused"]]
    summary = {
        "correct_refusals": f"{sum(r['refused'] for r in unanswerable)}/{len(unanswerable)}",
        "false_refusals": f"{len(answerable) - len(answered)}/{len(answerable)}",
        "false_refusals_with_source_in_context": [
            r["id"] for r in answerable if r["refused"] and r["context_has_source"]
        ],
        "answers_without_citation": [r["id"] for r in answered if not r["citations"]],
        "answers_with_invented_citation": [r["id"] for r in rows if r["invented_citations"]],
        "seconds_median": round(median(r["seconds"] for r in rows), 1),
    }
    return {
        "mode": "answers",
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "llm": f"{settings.llm_model} @ {settings.llm_base_url}",
        "llm_temperature": settings.llm_temperature,
        "embedding_model": model,
        "retrieval": f"dense only, Turkish query (no translation), context_k={CONTEXT_K}",
        "summary": summary,
        "per_question": rows,
    }


def print_summary(result: dict) -> None:
    print(f"\n{result['run_name']} | {result['retrieval']} | {result['hardware']}")
    columns = ["n", *(f"recall@{k}" for k in KS), "mrr"]
    print(f"{'group':<12}" + "".join(f"{c:>10}" for c in columns))
    for group, values in result["metrics"].items():
        cells = "".join(f"{values[c]:>10}" if c == "n" else f"{values[c]:>10.3f}" for c in columns)
        print(f"{group:<12}{cells}")
    missed = [q["id"] for q in result["per_question"] if q["first_relevant_rank"] is None]
    print(f"median query latency: {result['latency_ms_median']} ms | not in top {TOP_K}: {missed}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fast", action="store_true", help="retrieval metrics only, no LLM")
    mode.add_argument("--answers", action="store_true", help="answer every question with the LLM")
    parser.add_argument("--model", help="embedding model id (default: EMBEDDING_MODEL)")
    parser.add_argument(
        "--retriever", choices=RETRIEVERS, default="dense", help="for --fast (default: dense)"
    )
    args = parser.parse_args()

    model = args.model or get_settings().embedding_model
    if args.answers:
        result = run_answers(model)
        for row in result["per_question"]:
            flags = " REFUSED" * row["refused"] + " INVENTED" * bool(row["invented_citations"])
            print(f"\n{row['id']} ({row['type']}, {row['seconds']}s){flags}\n{row['answer']}")
        print("\n" + json.dumps(result["summary"], indent=2, ensure_ascii=False))
        ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", get_settings().llm_model.lower()).strip("_")
        out = ANSWERS_DIR / f"{result['date'][:10]}_{slug}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"saved -> {out}")
        return

    result = run_fast(model, args.retriever)
    print_summary(result)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{result['date'][:10]}_{result['run_name']}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
