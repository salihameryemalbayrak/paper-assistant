"""Central configuration, read from environment variables and an optional .env file.

No model name, URL or secret is hard-coded anywhere else in the codebase:
every component reads its settings from here.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM server: any OpenAI-compatible API (Ollama, vLLM, a commercial provider).
    llm_base_url: str
    llm_model: str
    # Local servers ignore the key, but the OpenAI client requires a non-empty value.
    llm_api_key: SecretStr = SecretStr("not-needed")
    llm_temperature: float = 0.0
    llm_timeout_s: float = 120.0

    # Vector database (Qdrant server, see infra/docker-compose.yml).
    qdrant_url: str = "http://localhost:6333"
    # Hugging Face model id for sentence-transformers. Changing it needs a re-index:
    # each model gets its own Qdrant collection (vector sizes differ between models).
    embedding_model: str = "intfloat/multilingual-e5-small"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, loaded once and cached for the lifetime of the process."""
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment
