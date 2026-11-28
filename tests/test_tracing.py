"""Tracing is optional: without keys nothing is imported or sent."""

from langchain_core.language_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from app.ask import build_chain
from app.config import Settings
from app.tracing import get_callbacks, trace_config, tracing_enabled


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, llm_base_url="x", llm_model="y", **overrides)


def test_no_keys_means_no_tracing():
    s = settings()
    assert not tracing_enabled(s)
    assert get_callbacks(s) == []


def test_one_key_alone_is_not_enough():
    assert not tracing_enabled(settings(langfuse_public_key="pk-lf-x"))


def test_handler_is_built_with_keys_without_contacting_the_server():
    s = settings(
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        langfuse_base_url="http://127.0.0.1:9",
    )  # fmt: skip  nothing listens there
    (handler,) = get_callbacks(s)
    assert type(handler).__name__ in {"CallbackHandler", "LangchainCallbackHandler"}


def test_chain_runs_unchanged_with_an_empty_trace_config():
    config = trace_config([], name="ask", tags=["dense"], session="s1")
    assert config["metadata"] == {"langfuse_tags": ["dense"], "langfuse_session_id": "s1"}
    chain = build_chain(RunnableLambda(lambda q: []), FakeListChatModel(responses=["Cevap."]))
    assert chain.invoke("Soru?", config=config)["answer"] == "Cevap."
