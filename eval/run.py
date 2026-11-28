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
    uv run python -m eval.run --fast --retriever hybrid_en   # English from translations.jsonl
    uv run python -m eval.run --fast --retriever dense_tr_bm25_en --reranker bge_m3
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
from langchain_core.runnables import RunnableLambda

from app.ask import CONTEXT_K, answer_kind, build_chain, check_citations, extract_citations
from app.config import get_settings
from app.llm import get_chat_model
from app.rerank import RERANKERS
from app.retrieval import (
    BRANCHES,
    RETRIEVERS,
    Query,
    build_retriever,
    get_cross_encoder,
    needs_translation,
    uses_dense,
)
from app.tracing import flush, get_callbacks, trace_config
from app.translate import build_translator
from app.truecase import load_vocabulary, truecase
from app.vectorstore import collection_name
from eval.dataset import QuestionType, SourceRef, load_dataset
from eval.retrieval_metrics import Hit, evaluate, evidence_found, evidence_metrics, reciprocal_rank
from eval.translations import TRANSLATIONS, load_translations

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


def describe_query(retriever_name: str, translation: str, reranker: str = "") -> str:
    if not needs_translation(retriever_name, reranker):
        return "Turkish query (no translation)"
    return f"Turkish + English query ({translation})"


def describe_reranker(reranker: str, candidates: int) -> str:
    if not reranker:
        return ""
    model, lang = RERANKERS[reranker]
    return f", reranked by {model} ({lang} query) from {candidates} candidates"


def reranker_counts(reranker: str) -> dict | None:
    if not reranker:
        return None
    ce = get_cross_encoder(reranker)
    return {"pairs_scored": ce.pairs_scored, "pairs_over_max_length": ce.pairs_truncated}


def run_fast(
    model: str,
    retriever_name: str = "dense",
    reranker: str = "",
    candidates: int = 20,
    depth: int = 20,
) -> dict:
    items = load_dataset(DATASET)
    depth = max(depth, TOP_K)  # what build_retriever really uses; record that, not the request
    retriever = build_retriever(retriever_name, TOP_K, model, reranker, candidates, depth)
    multi = len(BRANCHES[retriever_name]) > 1  # depth only changes fused variants

    # Translated variants read the reviewed, stored translations: no LLM call, so the
    # timings below exclude translation (measured separately by eval.translations).
    english: dict[str, str] = {}
    translation_model = None
    if needs_translation(retriever_name, reranker):
        stored = load_translations(TRANSLATIONS, items)
        english = {item.question: stored[item.id].en for item in items}
        translation_model = stored[items[0].id].model

    vocab = load_vocabulary()  # same truecasing as the answer chain (a no-op on the eval set)

    def to_query(question: str) -> Query:
        tr = truecase(question, vocab)
        return {"tr": tr, "en": english[question]} if english else {"tr": tr}

    retriever.invoke({"tr": "warm-up", "en": "warm-up"})  # loads the model; not timed
    cache: dict[str, list[Hit]] = {}
    texts: dict[str, list[str]] = {}  # retrieved chunk texts, for evidence recall
    latencies_ms: list[float] = []

    def retrieve(question: str) -> list[Hit]:
        start = time.perf_counter()
        docs = retriever.invoke(to_query(question))
        latencies_ms.append((time.perf_counter() - start) * 1000)
        cache[question] = [to_hit(d) for d in docs]
        texts[question] = [d.metadata["text"] for d in docs]
        return cache[question]

    metrics = evaluate(items, retrieve, ks=KS)
    evidence = evidence_metrics(items, lambda question: texts[question], ks=KS)

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
                "evidence_found@5": _found(item, texts[item.question], 5),
            }
        )

    return {
        "mode": "fast",
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "run_name": (
            f"{retriever_name}_{collection_name(model)}"
            if uses_dense(retriever_name)
            else retriever_name
        )
        + (f"_depth{depth}" if multi else "")
        + (f"_rerank_{reranker}" if reranker else ""),
        "retriever": retriever_name,
        "retrieval_depth": depth if multi else None,
        "reranker": RERANKERS[reranker][0] if reranker else None,
        "rerank_candidates": candidates if reranker else None,
        "reranker_counts": reranker_counts(reranker),  # incl. the warm-up query
        "embedding_model": model if uses_dense(retriever_name) else None,
        "retrieval": f"{retriever_name}, "
        f"{describe_query(retriever_name, f'stored, {TRANSLATIONS}', reranker)}"
        f"{describe_reranker(reranker, candidates)}, top_k={TOP_K}",
        "translation_model": translation_model,
        "latency_excludes_translation": needs_translation(retriever_name, reranker),
        "dataset": {
            "file": str(DATASET),
            "answerable": len(per_question),
            "total": len(items),
            # how the expected answers were checked (D35)
            "verified_by_human": sum(i.verified for i in items),
            "verified_by_evidence": sum(not i.verified for i in items),
        },
        "corpus": corpus_info(),
        "latency_ms_median": round(median(latencies_ms), 1),
        "metrics": metrics,
        "evidence": evidence,  # chunk level, questions with evidence quotes only
        "per_question": per_question,
    }


def _found(item, texts: list[str], k: int) -> str | None:
    """ "2/3": evidence quotes of the question found in the top-k texts; None without any."""
    if not item.evidence:
        return None
    found = evidence_found([e.quote for e in item.evidence], texts, k)
    return f"{sum(found)}/{len(found)}"


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: the smallest value with at least p% of the values <= it."""
    ordered = sorted(values)
    return ordered[max(0, -(-len(ordered) * p // 100) - 1)]


def summarize_answers(rows: list[dict]) -> dict:
    """Automatic checks over the answers (no judge LLM; RAGAS comes in Phase 7)."""
    answerable = [r for r in rows if r["type"] != QuestionType.UNANSWERABLE]
    unanswerable = [r for r in rows if r["type"] == QuestionType.UNANSWERABLE]

    def ids(rows_: list[dict], kind: str) -> list[str]:
        return [r["id"] for r in rows_ if r["kind"] == kind]

    refused = ids(answerable, "refusal")
    return {
        "correct_refusals": f"{len(ids(unanswerable, 'refusal'))}/{len(unanswerable)}",
        "answerable_answered": f"{len(ids(answerable, 'answer'))}/{len(answerable)}",
        "answerable_partial": ids(answerable, "partial"),
        "answerable_refused": refused,
        "refused_although_source_page_in_context": [
            r["id"] for r in answerable if r["id"] in refused and r["context_has_source"]
        ],
        "answers_without_citation": [
            r["id"] for r in rows if r["kind"] != "refusal" and not r["citations"]
        ],
        "answers_with_invented_citation": [r["id"] for r in rows if r["invented_citations"]],
        "seconds_median": round(median(r["seconds"] for r in rows), 1),
        "seconds_p95": round(percentile([r["seconds"] for r in rows], 95), 1),
    }


def run_answers(model: str, stored_translations: bool = False) -> dict:
    """The full chain on every question.

    stored_translations: use eval/translations.jsonl instead of translating live. Same
    English queries as the translation model gives (deterministic, 41/41 identical, D47),
    but only the answering LLM has to be in memory: comparing a 14B model, live
    translation made Ollama swap the two models on every question (D48).
    """
    settings = get_settings()
    items = load_dataset(DATASET)
    llm = get_chat_model(settings)
    reranker, candidates = settings.reranker, settings.rerank_candidates
    depth = settings.retrieval_depth
    retriever = build_retriever(settings.retriever, CONTEXT_K, model, reranker, candidates, depth)
    multi = len(BRANCHES[settings.retriever]) > 1
    # Live translation here: the answer eval measures the whole system, translation included.
    translator = None
    if needs_translation(settings.retriever, reranker) and stored_translations:
        stored = load_translations(TRANSLATIONS, items)
        english = {item.question: stored[item.id].en for item in items}
        translator = RunnableLambda(lambda question: english[question])
    elif needs_translation(settings.retriever, reranker):
        translator = build_translator(get_chat_model(settings, settings.translate_model or None))
    chain = build_chain(retriever, llm, translator, load_vocabulary())
    chain.invoke("warm-up")  # loads the embedding model and the LLM (not traced)

    # One Langfuse trace per question, all in one session for this run (if keys are set).
    callbacks = get_callbacks(settings)
    session = f"eval-answers-{datetime.now().isoformat(timespec='minutes')}"
    tags = ["eval", settings.retriever, settings.llm_model]

    rows = []
    for item in items:
        config = trace_config(callbacks, name=f"eval {item.id}", tags=tags, session=session)
        start = time.perf_counter()
        out = chain.invoke(item.question, config=config)
        seconds = time.perf_counter() - start
        answer = out["answer"].strip()
        answerable = item.type != QuestionType.UNANSWERABLE
        hits = [to_hit(d) for d in out["docs"]]
        rows.append(
            {
                "id": item.id,
                "type": item.type.value,
                "question": item.question,
                "query_en": out["query"].get("en"),
                "expected": item.answer,
                "answer": answer,
                "kind": answer_kind(answer),  # answer | partial | refusal
                # did the context contain an expected page? (retrieval succeeded)
                "context_has_source": answerable and reciprocal_rank(hits, item.sources) > 0,
                # chunk level: did the quotes the answer needs reach the LLM? (D36)
                "evidence_in_context": _found(
                    item, [d.metadata["text"] for d in out["docs"]], CONTEXT_K
                ),
                "citations": extract_citations(answer),
                "invented_citations": check_citations(answer, out["docs"]),
                "context": [d.metadata["chunk_id"] for d in out["docs"]],
                "seconds": round(seconds, 1),
            }
        )

    flush(settings)
    return {
        "mode": "answers",
        "langfuse_session": session if callbacks else None,
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "llm": f"{settings.llm_model} @ {settings.llm_base_url}",
        "translation_llm": (
            load_translations(TRANSLATIONS, items)[items[0].id].model
            if stored_translations
            else settings.translate_model or settings.llm_model
        ),
        "translation": f"stored, {TRANSLATIONS}" if stored_translations else "live",
        "llm_temperature": settings.llm_temperature,
        "corpus": corpus_info(),
        "embedding_model": model,
        "retriever": settings.retriever,
        "reranker": RERANKERS[reranker][0] if reranker else None,
        "reranker_counts": reranker_counts(reranker),
        "retrieval_depth": depth if multi else None,
        "retrieval": f"{settings.retriever}, "
        f"{describe_query(settings.retriever, 'live, same LLM', reranker)}"
        f"{describe_reranker(reranker, candidates)}, context_k={CONTEXT_K}",
        "summary": summarize_answers(rows),
        "per_question": rows,
    }


def corpus_info() -> dict:
    """Documents and chunks in data/chunks.jsonl: results depend on the corpus size."""
    from ingest.chunk import load_chunks

    chunks = load_chunks()
    return {"docs": len({c.paper for c in chunks}), "chunks": len(chunks)}


def quality_gate(result: dict, min_recall5: float | None, min_evidence5: float | None) -> list[str]:
    """Failed thresholds of a fast-eval result, e.g. ["recall@5 0.700 < 0.740"]."""
    checks = [
        ("recall@5", result["metrics"]["all"]["recall@5"], min_recall5),
        ("evidence_recall@5", result["evidence"]["all"]["evidence_recall@5"], min_evidence5),
    ]
    return [f"{name} {value:.3f} < {limit}" for name, value, limit in checks
            if limit is not None and value < limit]  # fmt: skip


def unique_path(path: Path) -> Path:
    """path, or path_2, path_3, ... if it exists: a rerun never overwrites a result."""
    candidate, n = path, 2
    while candidate.exists():
        candidate = path.with_stem(f"{path.stem}_{n}")
        n += 1
    return candidate


def print_summary(result: dict) -> None:
    print(f"\n{result['run_name']} | {result['retrieval']} | {result['hardware']}")
    columns = ["n", *(f"recall@{k}" for k in KS), "mrr"]
    print(f"{'group':<12}" + "".join(f"{c:>10}" for c in columns))
    for group, values in result["metrics"].items():
        cells = "".join(f"{values[c]:>10}" if c == "n" else f"{values[c]:>10.3f}" for c in columns)
        print(f"{group:<12}{cells}")
    if evidence := result.get("evidence"):
        print("\nchunk level (questions with evidence quotes)")
        ecols = [
            "n",
            *(f"evidence_recall@{k}" for k in KS),
            *(f"evidence_complete@{k}" for k in KS),
        ]
        print(f"{'group':<12}" + "".join(f"{c.replace('evidence_', 'ev_'):>15}" for c in ecols))
        for group, values in evidence.items():
            cells = "".join(
                f"{values[c]:>15}" if c == "n" else f"{values[c]:>15.3f}" for c in ecols
            )
            print(f"{group:<12}{cells}")
    missed = [q["id"] for q in result["per_question"] if q["first_relevant_rank"] is None]
    print(f"median query latency: {result['latency_ms_median']} ms | not in top {TOP_K}: {missed}")
    if counts := result.get("reranker_counts"):
        print(f"reranker pairs: {counts['pairs_scored']}, over max_length: "
              f"{counts['pairs_over_max_length']}")  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fast", action="store_true", help="retrieval metrics only, no LLM")
    mode.add_argument("--answers", action="store_true", help="answer every question with the LLM")
    parser.add_argument("--model", help="embedding model id (default: EMBEDDING_MODEL)")
    parser.add_argument(
        "--retriever", choices=RETRIEVERS, help="for --fast (default: RETRIEVER from .env)"
    )
    parser.add_argument("--reranker", choices=tuple(RERANKERS), default="", help="for --fast")
    parser.add_argument("--candidates", type=int, default=20, help="chunks given to the reranker")
    parser.add_argument(
        "--depth", type=int, default=None, help="results per branch before fusion (RETRIEVAL_DEPTH)"
    )
    # Quality gate for CI (--fast): exit with an error if the run falls below these.
    parser.add_argument(
        "--stored-translations", action="store_true",
        help="--answers: English queries from eval/translations.jsonl, no live translation",
    )  # fmt: skip
    parser.add_argument("--min-recall5", type=float, help="fail if page-level recall@5 is lower")
    parser.add_argument("--min-evidence5", type=float, help="fail if evidence recall@5 is lower")
    args = parser.parse_args()

    model = args.model or get_settings().embedding_model
    if args.answers:
        result = run_answers(model, args.stored_translations)
        for row in result["per_question"]:
            flags = f" {row['kind'].upper()}" + " INVENTED" * bool(row["invented_citations"])
            print(f"\n{row['id']} ({row['type']}, {row['seconds']}s){flags}\n{row['answer']}")
        print("\n" + json.dumps(result["summary"], indent=2, ensure_ascii=False))
        ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", get_settings().llm_model.lower()).strip("_")
        rerank = f"_rerank_{get_settings().reranker}" if get_settings().reranker else ""
        depth = f"_depth{result['retrieval_depth']}" if result["retrieval_depth"] else ""
        docs = f"{result['corpus']['docs']}docs"
        name = f"{result['date'][:10]}_{docs}_{result['retriever']}{depth}{rerank}_{slug}.json"
        out = unique_path(ANSWERS_DIR / name)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"saved -> {out}")
        return

    depth = args.depth or get_settings().retrieval_depth
    # default: the retriever the system uses, so `--fast` measures what the answers get
    retriever = args.retriever or get_settings().retriever
    result = run_fast(model, retriever, args.reranker, args.candidates, depth)
    print_summary(result)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    docs = f"{result['corpus']['docs']}docs"
    out = unique_path(RESULTS_DIR / f"{result['date'][:10]}_{docs}_{result['run_name']}.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")
    if failures := quality_gate(result, args.min_recall5, args.min_evidence5):
        raise SystemExit("quality gate failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
