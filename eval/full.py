"""Full eval: RAGAS faithfulness and answer relevancy on saved answers, by a judge LLM.

Reads an answers file written by `eval.run --answers` and scores every answered question;
the answers are not generated again, so the answering LLM and the judge never share the
memory of a 16 GB laptop, and the same answers can be rescored by another judge.

How RAGAS 0.4.4 computes the two metrics (ragas/metrics/collections):

- faithfulness: the judge splits the answer into atomic statements (1 LLM call), then
  decides for each statement whether the context supports it (1 NLI call). Score =
  supported statements / all statements. No statements (a refusal) -> NaN.
- answer relevancy: the judge writes the question the answer seems to reply to and flags
  evasive ("noncommittal") answers. Score = cosine similarity of that question and the
  real one (embeddings), 0 if evasive. RAGAS asks `strictness` times with the same
  prompt; at temperature 0 the questions are identical, so strictness=1.

The judge gets the context exactly as the answering LLM saw it, each chunk under its
citation label (app.ask.format_docs). With bare chunk texts, the judge turned the
answer's citation "[bge_m3, s.7, §4.2]" into a statement of its own and marked it
unsupported: every cited answer lost points (D39).

- answer accuracy (reference-based; NVIDIA's dual judge): the judge compares the answer
  with the expected answer and rates 0 / 2 / 4 (no / partial / full match), a second
  prompt does the same with answer and reference swapped; score = mean / 4. Unlike
  faithfulness this measures correctness: "faithful but wrong" answers fail (D39, D40).

Faithfulness and relevancy skip refusals (no statements). Answer accuracy scores every
answerable question: refusing one is a wrong answer, scored 0 without a judge call.
Unanswerable questions are measured by refusal rate in eval.run --answers.
Needs the "eval" dependency group (RAGAS, kept out of the app and CI).

Usage:
    uv run --group eval python -m eval.full docs/benchmarks/answers/<file>.json
    uv run --group eval python -m eval.full <file>.json --limit 3   # a quick trial
    uv run --group eval python -m eval.full <file>.json --metrics answer_accuracy
"""

import argparse
import asyncio
import json
import math
import re
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from ragas.embeddings.base import BaseRagasEmbedding

from app.ask import format_docs

FULL_DIR = Path("docs/benchmarks/full_eval")


class E5Embeddings(BaseRagasEmbedding):
    """RAGAS embedding interface over the project's embedding model (query prefix kept)."""

    def __init__(self, model_name: str) -> None:
        from app.embeddings import get_embeddings

        super().__init__()
        self.model = get_embeddings(model_name)

    def embed_text(self, text: str, **kwargs) -> list[float]:
        # both texts compared are questions: embed them the same way, as queries
        return self.model.embed_query(text)

    async def aembed_text(self, text: str, **kwargs) -> list[float]:
        return self.embed_text(text)


def build_judge(settings):
    from openai import AsyncOpenAI
    from ragas.llms.base import llm_factory

    if not settings.judge_model:
        raise SystemExit("JUDGE_MODEL is not set (see .env.example)")
    client = AsyncOpenAI(
        base_url=settings.judge_base_url or settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout=600,
    )
    return llm_factory(settings.judge_model, client=client, temperature=0.0)


def _number(value: float) -> float | None:
    return None if value is None or math.isnan(value) else round(value, 4)


METRICS = ("faithfulness", "answer_relevancy", "answer_accuracy")


def applies(metric: str, row: dict) -> bool:
    """Which rows a metric scores (see the module docstring)."""
    if metric == "answer_accuracy":
        return row["type"] != "unanswerable"
    return row["kind"] != "refusal"


async def score_rows(
    rows: list[dict], chunks: dict, judge, embeddings, metrics: tuple[str, ...]
) -> list[dict]:
    from ragas.metrics.collections import AnswerAccuracy, AnswerRelevancy, Faithfulness

    # build only the requested metrics: AnswerRelevancy rejects missing embeddings
    factories = {
        "faithfulness": lambda: Faithfulness(llm=judge),
        "answer_relevancy": lambda: AnswerRelevancy(llm=judge, embeddings=embeddings, strictness=1),
        "answer_accuracy": lambda: AnswerAccuracy(llm=judge),
    }
    scorers = {name: factories[name]() for name in metrics}
    scored = []
    for i, row in enumerate(rows, start=1):
        start = time.perf_counter()
        out = {"id": row["id"], "type": row["type"], "kind": row["kind"]}
        for name in metrics:
            if not applies(name, row):
                continue
            if name == "answer_accuracy" and row["kind"] == "refusal":
                out[name] = 0.0  # refusing an answerable question is a wrong answer
                continue
            kwargs = {}
            if name == "faithfulness":
                # one string per chunk, label + text, as in the answer prompt
                kwargs["retrieved_contexts"] = [format_docs([chunks[c]]) for c in row["context"]]
            if name == "answer_accuracy":
                kwargs["reference"] = row["expected"]
            try:
                result = await scorers[name].ascore(
                    user_input=row["question"], response=row["answer"], **kwargs
                )
                out[name] = _number(result.value)
            except Exception as e:  # a judge that breaks the JSON format must not stop the run
                out[name], out[f"{name}_error"] = None, f"{type(e).__name__}: {e}"[:300]
        out["seconds"] = round(time.perf_counter() - start, 1)
        scored.append(out)
        values = " ".join(f"{m}={out[m]}" for m in metrics if m in out)
        print(f"[{i}/{len(rows)}] {row['id']} {values} ({out['seconds']}s)", flush=True)
    return scored


def summarize(scored: list[dict], metrics: tuple[str, ...] = METRICS) -> dict:
    def stats(rows: list[dict], key: str) -> dict:
        rows = [r for r in rows if key in r]  # rows the metric applies to
        values = [r[key] for r in rows if r[key] is not None]
        return {"mean": round(mean(values), 4) if values else None, "n": len(values),
                "not_scored": len(rows) - len(values)}  # fmt: skip

    groups = {"all": scored}
    for row in scored:
        groups.setdefault(row["type"], []).append(row)
    return {group: {m: stats(rows, m) for m in metrics} for group, rows in groups.items()}


def main() -> None:
    from app.config import get_settings
    from eval.run import _git_commit, _hardware, unique_path
    from ingest.chunk import load_chunks
    from ingest.index import chunk_to_document

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("answers", type=Path, help="answers file from eval.run --answers")
    parser.add_argument("--limit", type=int, help="score only the first N questions")
    parser.add_argument(
        "--metrics", nargs="+", choices=METRICS, default=list(METRICS), help="default: all"
    )
    args = parser.parse_args()
    metrics = tuple(m for m in METRICS if m in args.metrics)

    settings = get_settings()
    source = json.loads(args.answers.read_text(encoding="utf-8"))
    rows = [r for r in source["per_question"] if any(applies(m, r) for m in metrics)]
    if args.limit:
        rows = rows[: args.limit]
    chunks = {c.id: chunk_to_document(c) for c in load_chunks()}

    start = time.perf_counter()
    embeddings = E5Embeddings(source["embedding_model"]) if "answer_relevancy" in metrics else None
    scored = asyncio.run(score_rows(rows, chunks, build_judge(settings), embeddings, metrics))
    elapsed = time.perf_counter() - start

    result = {
        "mode": "full",
        "date": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "hardware": _hardware(),
        "answers_file": str(args.answers),
        "answering_llm": source["llm"],
        "judge": f"{settings.judge_model} @ {settings.judge_base_url or settings.llm_base_url}",
        "judge_temperature": 0.0,
        "metrics": list(metrics),
        "ragas_metrics": "ragas.metrics.collections Faithfulness, AnswerRelevancy(strictness=1), "
        "AnswerAccuracy",
        "faithfulness_context": "chunks under their citation labels, as in the answer prompt",
        "answer_relevancy_embeddings": source["embedding_model"],
        "answer_accuracy_refusals": "scored 0 without a judge call",
        "scored": len(scored),
        "limit": args.limit,
        "seconds_total": round(elapsed),
        "seconds_per_question_median": median(r["seconds"] for r in scored) if scored else None,
        "summary": summarize(scored, metrics),
        "per_question": scored,
    }
    print(json.dumps(result["summary"]["all"], indent=2))

    judge_slug = re.sub(r"[^a-z0-9]+", "_", settings.judge_model.lower()).strip("_")
    limit = f"_limit{args.limit}" if args.limit else ""
    subset = "" if metrics == METRICS else "_" + "+".join(metrics)
    FULL_DIR.mkdir(parents=True, exist_ok=True)
    out = unique_path(FULL_DIR / f"{args.answers.stem}_judge_{judge_slug}{subset}{limit}.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
