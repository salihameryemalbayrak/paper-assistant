"""Optional tracing with Langfuse (self-hosted, infra/docker-compose.obs.yml).

LangChain calls its callback handlers at the start and end of every step of a chain
(translation, each retriever branch, the fusion, the prompt, the LLM call). Langfuse's
CallbackHandler turns these events into one nested trace per question, with inputs,
outputs, timings and token counts, and sends it in the background.

Without LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY nothing is imported or sent: the code
runs exactly as before (CLAUDE.md). The keys come from app.config, not the environment:
pydantic-settings reads .env without exporting it, so the Langfuse client is built here
with explicit arguments (it would otherwise look only at os.environ).
"""

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from app.config import Settings, get_settings


def tracing_enabled(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(s.langfuse_public_key and s.langfuse_secret_key.get_secret_value())


def get_callbacks(settings: Settings | None = None) -> list[BaseCallbackHandler]:
    """[Langfuse handler] when keys are configured, else [] (pass as config["callbacks"])."""
    s = settings or get_settings()
    if not tracing_enabled(s):
        return []
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    # One client per public key (singleton); the handler looks it up by that key.
    Langfuse(
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key.get_secret_value(),
        base_url=s.langfuse_base_url or None,
    )
    return [CallbackHandler(public_key=s.langfuse_public_key)]


def trace_config(
    callbacks: list[BaseCallbackHandler], *, name: str, tags: list[str], session: str = ""
) -> dict[str, Any]:
    """LangChain run config: trace name, tags (filterable in the UI), optional session."""
    metadata: dict[str, Any] = {"langfuse_tags": tags}
    if session:
        metadata["langfuse_session_id"] = session  # groups e.g. all questions of one eval run
    return {"callbacks": callbacks, "run_name": name, "tags": tags, "metadata": metadata}


def flush(settings: Settings | None = None) -> None:
    """Send buffered traces now (short CLI runs; atexit would also do it)."""
    s = settings or get_settings()
    if tracing_enabled(s):
        from langfuse import get_client

        get_client(public_key=s.langfuse_public_key).flush()
