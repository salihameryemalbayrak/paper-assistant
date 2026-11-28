"""Talks to the HTTP API (app/api.py) for the Streamlit page; no Streamlit in here.

Kept separate from ui/app.py so it can be tested without a browser or Streamlit.
The UI only needs the API address: API_URL (default http://localhost:8000).
"""

from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class UiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8000"
    api_timeout_s: float = 180.0  # translation + answer on a laptop: ~3-15 s, cold start more


class ApiError(Exception):
    """A message to show to the user instead of a stack trace."""


EXAMPLES = [
    "QLoRA hangi üç yenilikle bellek tasarrufu sağlıyor?",
    "vLLM makalesine göre, mevcut sunucu sistemleri ayırdıkları belleğin ne kadarını "
    "gerçekten token'ları saklamak için kullanabiliyor?",
    "Ragas ve ARES bir RAG sistemini nasıl değerlendiriyor, farkları ne?",
    "vLLM, Apple'ın M serisi işlemcilerinde ne kadar hızlı çalışıyor?",  # not in the papers
]

# answer kind (app.ask.answer_kind) -> (label, Streamlit badge color)
KINDS = {
    "answer": ("Kaynaklı cevap", "green"),
    "partial": ("Kısmi cevap", "orange"),
    "refusal": ("Dokümanda bulamadım", "gray"),
}


def ask(question: str, settings: UiSettings, client: httpx.Client | None = None) -> dict[str, Any]:
    """POST /ask; ApiError with a readable reason on any failure."""
    http = client or httpx.Client(timeout=settings.api_timeout_s)
    try:
        response = http.post(f"{settings.api_url}/ask", json={"question": question})
    except httpx.ConnectError as e:
        raise ApiError(f"API'ye bağlanılamadı ({settings.api_url}). API çalışıyor mu?") from e
    except httpx.TimeoutException as e:
        raise ApiError(f"API {settings.api_timeout_s:.0f} sn içinde cevap vermedi.") from e
    if response.status_code == 422:
        raise ApiError("Soru geçersiz (boş ya da 1000 karakterden uzun).")
    if response.status_code == 503:
        raise ApiError(f"Bir servis kapalı: {response.json().get('detail', '')}")
    if response.status_code != 200:
        raise ApiError(f"API hatası {response.status_code}.")
    return response.json()


def health(settings: UiSettings, client: httpx.Client | None = None) -> dict[str, Any] | None:
    """GET /health, or None if the API or the index is not reachable."""
    http = client or httpx.Client(timeout=5)
    try:
        response = http.get(f"{settings.api_url}/health")
    except httpx.HTTPError:
        return None
    return response.json() if response.status_code == 200 else None


def source_title(source: dict[str, Any]) -> str:
    """Expander title: the citation label, then the section in words."""
    return f"{source['label']}  {source['section']}".strip()
