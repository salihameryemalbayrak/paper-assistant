"""Checks that the client is wired from settings. No network call is made."""

from app.config import Settings
from app.llm import get_chat_model


def test_chat_model_uses_settings():
    s = Settings(
        _env_file=None,
        llm_base_url="http://localhost:11434/v1",
        llm_model="test-model",
        llm_temperature=0.0,
    )

    llm = get_chat_model(s)

    assert llm.model_name == "test-model"
    assert llm.openai_api_base == "http://localhost:11434/v1"
    assert llm.temperature == 0.0
