"""API with a fake engine (fake LLM and retriever): no Ollama, no Qdrant, no .env."""

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.language_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda
from openai import APIConnectionError

from app.api import Engine, create_app
from app.ask import build_chain

DOC = Document(
    page_content="Ragas > 3 Evaluation\nFaithfulness ...",
    metadata={"paper": "ragas", "page": 3, "pages": [3], "section": "3 Evaluation Strategies",
              "text": "Faithfulness measures ...", "chunk_id": "ragas-0005"},
)  # fmt: skip


def client(answer: str = "Ragas sadakati ölçer [ragas, s.3, §3].", chain=None, health=None):
    def engine() -> Engine:
        fake_chain = build_chain(
            RunnableLambda(lambda query: [DOC]), FakeListChatModel(responses=[answer])
        )
        return Engine(
            chain=chain or fake_chain,
            llm="fake-llm",
            retriever="fake",
            health=health or (lambda: {"chunks": 1}),
            callbacks=[],
        )

    return TestClient(create_app(engine))


def test_ask_returns_answer_sources_and_checks():
    with client() as c:
        body = c.post("/ask", json={"question": "  Ragas neyi ölçer?  "}).json()
    assert body["question"] == "Ragas neyi ölçer?"  # stripped
    assert body["kind"] == "answer"
    assert body["sources"][0]["label"] == "[ragas, s.3, §3]"
    assert (
        body["sources"][0]["text"] == "Faithfulness measures ..."
    )  # original text, not search_text
    assert body["invented_citations"] == []
    assert body["query_en"] is None  # no translator in this chain


def test_invented_citation_and_refusal_are_reported():
    with client("Uydurma [ragas, s.9, §5].") as c:
        assert c.post("/ask", json={"question": "?"}).json()["invented_citations"] == [
            "[ragas, s.9, §5]"
        ]
    with client("Dokümanda bulamadım.") as c:
        assert c.post("/ask", json={"question": "Türkçe başarım?"}).json()["kind"] == "refusal"


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "   "}, {}, {"q": "x"}])
def test_invalid_question_is_rejected_with_422(payload):
    with client() as c:
        assert c.post("/ask", json=payload).status_code == 422


def test_unreachable_llm_gives_503_not_500():
    def down(_question, config=None):
        raise APIConnectionError(request=httpx.Request("POST", "http://llm/v1/chat"))

    with client(chain=RunnableLambda(down)) as c:
        response = c.post("/ask", json={"question": "Soru?"})
    assert response.status_code == 503
    assert "LLM server unreachable" in response.json()["detail"]


def test_health_reports_index_and_fails_with_503_when_unreachable():
    with client() as c:
        assert c.get("/health").json() == {"status": "ok", "chunks": 1}

    def broken() -> dict:
        raise ConnectionError("qdrant down")

    with client(health=broken) as c:
        assert c.get("/health").status_code == 503
