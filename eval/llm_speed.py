"""Answer-generation speed on the real prompts, for comparing models and servers.

Only the LLM call that writes the answer is timed (no translation, no search): the 49 eval
prompts exactly as the answer chain built them (system rules + 5 chunks under their
citation labels + the question), taken from a recorded answer-eval run.

    build  answers file -> dist/llm-prompts.jsonl (contains paper text: not for git)
    run    send the prompts one by one to the configured server (LLM_BASE_URL, LLM_MODEL)
           and record latency and output tokens per second -> docs/benchmarks/llm_speed/

Usage:
    uv run python -m eval.llm_speed build docs/benchmarks/answers/<file>.json
    uv run python -m eval.llm_speed run
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from statistics import median

PROMPTS = Path("dist/llm-prompts.jsonl")
OUT_DIR = Path("docs/benchmarks/llm_speed")
MAX_TOKENS = 512  # same cap on both servers


def build(answers_file: Path) -> None:
    from app.ask import PROMPT, format_docs
    from ingest.chunk import load_chunks
    from ingest.index import chunk_to_document

    docs = {c.id: chunk_to_document(c) for c in load_chunks()}
    rows = json.loads(answers_file.read_text(encoding="utf-8"))["per_question"]
    PROMPTS.parent.mkdir(parents=True, exist_ok=True)
    with PROMPTS.open("w", encoding="utf-8") as f:
        for row in rows:
            context = format_docs([docs[c] for c in row["context"]])
            messages = PROMPT.format_messages(context=context, question=row["question"])
            roles = {"system": "system", "human": "user"}
            f.write(json.dumps({"id": row["id"], "messages": [
                {"role": roles[m.type], "content": m.content} for m in messages
            ]}, ensure_ascii=False) + "\n")  # fmt: skip
    print(f"{len(rows)} prompts from {answers_file} -> {PROMPTS}")


def swap_counters() -> dict[str, int] | None:
    """macOS swap-in/out page counters (vm_stat); None elsewhere.

    A speed measurement is only valid without active swapping: the difference of these
    counters over the run is recorded with the result (a swapping run measured 8.1 s per
    answer for qwen3:4b, D48).
    """
    import platform
    import re
    import subprocess

    if platform.system() != "Darwin":
        return None
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    return {
        k.lower(): int(re.search(rf"{k}:\s+(\d+)", out).group(1)) for k in ("Swapins", "Swapouts")
    }


def run() -> None:
    from openai import OpenAI

    from app.config import get_settings
    from eval.run import _hardware, percentile, unique_path

    s = get_settings()
    client = OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key.get_secret_value())
    prompts = [json.loads(line) for line in PROMPTS.read_text(encoding="utf-8").splitlines()]

    def call(messages: list[dict]) -> tuple[float, int]:
        start = time.perf_counter()
        r = client.chat.completions.create(
            model=s.llm_model, messages=messages, temperature=0, max_tokens=MAX_TOKENS
        )
        return time.perf_counter() - start, r.usage.completion_tokens

    call(prompts[0]["messages"])  # warm-up: loads the model, not timed
    swap_before = swap_counters()
    rows = []
    for p in prompts:
        seconds, tokens = call(p["messages"])
        rows.append({"id": p["id"], "seconds": round(seconds, 3), "output_tokens": tokens})
        print(f"{p['id']} {seconds:.2f}s {tokens} tok", flush=True)
    swap_after = swap_counters()
    seconds = [r["seconds"] for r in rows]
    tokens = sum(r["output_tokens"] for r in rows)
    result = {
        "mode": "llm_speed",
        "server": f"OpenAI-compatible @ {s.llm_base_url}",
        "model": s.llm_model,
        "hardware": _hardware(),
        "date": datetime.now().isoformat(timespec="seconds"),
        "requests": "one at a time (batch 1), as in the app",
        "max_tokens": MAX_TOKENS,
        "prompts": len(rows),
        "latency_s": {"p50": round(median(seconds), 2), "p95": round(percentile(seconds, 95), 2)},
        # end to end: includes reading the ~1.5k-token prompt (prefill), not only decoding
        "output_tokens_per_s": round(tokens / sum(seconds), 1),
        "swap_pages_during_run": (
            {k: swap_after[k] - swap_before[k] for k in swap_after} if swap_before else None
        ),
        "per_prompt": rows,
    }
    print(json.dumps({k: result[k] for k in ("model", "latency_s", "output_tokens_per_s",
                                             "swap_pages_during_run")}))  # fmt: skip
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in s.llm_model.lower()).strip("_")
    out = unique_path(OUT_DIR / f"{result['date'][:10]}_ollama_{slug}.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build").add_argument("answers", type=Path)
    sub.add_parser("run")
    args = parser.parse_args()
    build(args.answers) if args.command == "build" else run()


if __name__ == "__main__":
    main()
