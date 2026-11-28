# syntax=docker/dockerfile:1
# Images for the API and the web UI (one Dockerfile, two targets). Build context: repo root.
#   docker compose -f infra/docker-compose.yml build        (see docker-compose.yml)
# Follows uv's Docker guide: pinned uv binary, dependencies in their own cached layer
# (rebuilt only when uv.lock changes), bytecode compiled at build time. Multi-arch:
# python:3.12-slim and the locked wheels exist for linux/arm64 and linux/amd64.

FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    HF_HOME=/cache/huggingface
WORKDIR /app
# no root at runtime; the model cache is a volume this user can write to
RUN useradd --create-home --uid 1000 app && mkdir -p /cache/huggingface && chown -R app /cache

# --- API: FastAPI + LangChain + sentence-transformers (PyTorch CPU build on Linux) ---
FROM base AS api
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-default-groups
COPY app/ app/
COPY ingest/ ingest/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]

# --- UI: Streamlit only, no PyTorch (talks to the API over HTTP) ---
FROM base AS ui
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --only-group ui
COPY ui/ ui/
COPY .streamlit/ .streamlit/
USER app
EXPOSE 8501
CMD ["streamlit", "run", "ui/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
