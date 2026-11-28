import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://example:8000/v1")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.3")

    s = Settings(_env_file=None)  # ignore any local .env so the test is deterministic

    assert s.llm_base_url == "http://example:8000/v1"
    assert s.llm_model == "some-model"
    assert s.llm_temperature == 0.3


def test_missing_required_setting_fails_fast(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_api_key_is_not_leaked_when_printed():
    s = Settings(_env_file=None, llm_base_url="x", llm_model="y", llm_api_key="secret-123")

    assert "secret-123" not in repr(s)
    assert s.llm_api_key.get_secret_value() == "secret-123"


def test_retrieval_settings_have_defaults_and_can_be_overridden(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    s = Settings(_env_file=None, llm_base_url="x", llm_model="y")

    assert s.qdrant_url == "http://localhost:6333"
    assert s.embedding_model == "BAAI/bge-m3"


def test_default_retriever_is_a_known_variant(monkeypatch):
    from app.retrieval import RETRIEVERS

    monkeypatch.delenv("RETRIEVER", raising=False)
    assert Settings(_env_file=None, llm_base_url="x", llm_model="y").retriever in RETRIEVERS


def test_translate_model_defaults_to_the_answer_model():
    from app.llm import get_chat_model

    s = Settings(_env_file=None, llm_base_url="http://x/v1", llm_model="big")
    assert get_chat_model(s).model_name == "big"
    assert get_chat_model(s, "small").model_name == "small"
