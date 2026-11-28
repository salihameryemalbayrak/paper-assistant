"""UI client against a fake API (httpx.MockTransport): no server, no Streamlit."""

import httpx
import pytest

from ui.client import ApiError, UiSettings, ask, health, source_title

SETTINGS = UiSettings(_env_file=None, api_url="http://api")


def fake(status: int, body: dict | None = None, error: Exception | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if error:
            raise error
        return httpx.Response(status, json=body or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ask_returns_the_api_body():
    body = {"answer": "Cevap [ragas, s.3, §3].", "kind": "answer", "sources": []}
    assert ask("Ragas neyi ölçer?", SETTINGS, fake(200, body)) == body


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (fake(0, error=httpx.ConnectError("refused")), "bağlanılamadı"),
        (fake(0, error=httpx.ReadTimeout("slow")), "cevap vermedi"),
        (fake(422), "geçersiz"),
        (fake(503, {"detail": "LLM server unreachable"}), "LLM server unreachable"),
        (fake(500), "500"),
    ],
)
def test_failures_become_readable_turkish_messages(client, message):
    with pytest.raises(ApiError, match=message):
        ask("Soru?", SETTINGS, client)


def test_health_is_none_when_unreachable():
    assert health(SETTINGS, fake(200, {"status": "ok", "chunks": 1734})) == {
        "status": "ok", "chunks": 1734,
    }  # fmt: skip
    assert health(SETTINGS, fake(0, error=httpx.ConnectError("refused"))) is None
    assert health(SETTINGS, fake(503)) is None


def test_source_title_shows_label_and_section():
    source = {"label": "[qlora, s.2, §1]", "section": "1 Introduction"}
    assert source_title(source) == "[qlora, s.2, §1]  1 Introduction"
