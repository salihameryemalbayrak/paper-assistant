# Paper Assistant: Turkish Q&A over AI papers with cited sources

A retrieval-augmented generation (RAG) assistant that answers **Turkish** questions about open-access computer science / AI papers (mostly in English). Every answer cites the **paper, page and section** it came from. If the answer is not in the documents, it says so.

The focus is on retrieval rather than on model size. The goal is good answers from a small local model (3–4B) through:
- hybrid search (BM25 + dense vectors, fused with RRF),
- query translation (Turkish → English),
- reranking,
- section-aware chunking,
- a measured evaluation set.

> **Status:** work in progress, phase 0 (project skeleton). See [PLAN.md](PLAN.md) for the roadmap (in Turkish). No benchmark numbers are reported until they are measured.

## Tech stack

| Area | Tools |
|---|---|
| Language / API | Python 3.12, FastAPI, Pydantic |
| LLM orchestration | LangChain, LangGraph (agentic flow, planned) |
| LLM serving | Any OpenAI-compatible API: Ollama (local), vLLM (GPU), commercial APIs (optional) |
| Retrieval | Qdrant, BM25, Hugging Face `sentence-transformers` (embeddings, reranker) |
| Evaluation | RAGAS + custom Recall@k / MRR |
| Observability | Langfuse |
| UI / Infra | Streamlit, Docker Compose, GitHub Actions |

## Quickstart

Prerequisites: [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/) and Docker (for Qdrant).

```bash
# 1. Install dependencies into a local virtual environment (.venv)
uv sync

# 2. Create your local settings file (never committed)
cp .env.example .env

# 3. Start the model server (in a separate terminal) and download a model
ollama serve
ollama pull qwen3:4b-instruct

# 4. Check the LLM connection
uv run python -m app.llm "Merhaba, kendini tanıtır mısın?"

# 5. Download the papers listed in data/SOURCES.md (licenses are re-checked)
uv run python -m ingest.download

# 6. Parse PDFs with Docling into data/parsed/ (first run downloads layout models)
uv run python -m ingest.parse

# 7. Split parsed elements into retrieval chunks (data/chunks.jsonl)
uv run python -m ingest.chunk

# 8. Start the Qdrant vector database (dashboard: http://localhost:6333/dashboard)
docker compose -f infra/docker-compose.yml up -d qdrant

# 9. Embed the chunks and write them to Qdrant (first run downloads the embedding model)
uv run python -m ingest.index

# 10. Fast eval: retrieval metrics (Recall@k, MRR) on the eval set, no LLM call
uv run python -m eval.run --fast

# 11. Ask a question: answer in Turkish with [paper, page, section] citations
uv run python -m app.ask "Ragas bir RAG sistemini hangi boyutlarda değerlendirir?"
```

Fast-eval results are saved to `docs/benchmarks/fast_eval/` with the model, hardware and git commit.

The model server is configured only through environment variables (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`). To switch to vLLM or another provider, edit `.env`; no code changes are needed.

## Development

```bash
uv run pytest                                      # tests
uv run ruff check . && uv run ruff format --check .  # lint + format check
```

## Project layout

```
app/        # configuration, LLM client, text utilities (retrieval and API to come)
ingest/     # data pipeline: download, parse (Docling), chunk
eval/       # hand-verified eval set (dataset.jsonl) and retrieval metrics (Recall@k, MRR)
data/       # SOURCES.md only; downloaded PDFs stay local
tests/      # pytest suite
docs/       # design decisions (DECISIONS.md, in Turkish), benchmarks
```

More folders (`ui/`, `infra/`) are added as the corresponding phases start.

## Data and licensing

Only papers under open licenses (CC-BY / CC0) are used. Raw PDFs and indexes are not stored in this repository; scripts to download and process them are.
