"""Tests for the answer chain. A fake LLM and a fake retriever: no Ollama, no Qdrant."""

from langchain_core.documents import Document
from langchain_core.language_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from app.ask import (
    NOT_FOUND,
    PROMPT,
    answer_kind,
    build_chain,
    check_citations,
    citation_label,
    extract_citations,
    format_docs,
)


def doc(paper="ragas", pages=(3,), section="3 Evaluation Strategies", text="Faithfulness ..."):
    return Document(
        page_content=f"Title > {section}\n{text}",  # search_text: must not reach the LLM
        metadata={"paper": paper, "page": pages[0], "pages": list(pages), "section": section,
                  "text": text, "chunk_id": f"{paper}-0001"},
    )  # fmt: skip


def test_citation_label_formats():
    assert citation_label(doc().metadata) == "[ragas, s.3, §3]"
    assert citation_label(doc(pages=(2, 3), section="3.2 Training").metadata) == (
        "[ragas, s.2–3, §3.2]"
    )
    assert citation_label(doc(section="Abstract").metadata) == "[ragas, s.3, §Abstract]"
    assert citation_label(doc(section="").metadata) == "[ragas, s.3]"


def test_context_uses_original_text_under_its_label():
    context = format_docs([doc(text="Ağırlıklar ışığında.")])
    assert context == "[ragas, s.3, §3]\nAğırlıklar ışığında."


def test_prompt_contains_context_question_and_refusal_sentence():
    messages = PROMPT.invoke({"context": "[ragas, s.3, §3]\nX", "question": "Soru?"}).messages
    assert NOT_FOUND in messages[0].content
    assert "[ragas, s.3, §3]\nX" in messages[0].content
    assert messages[1].content == "Soru?"


def test_extract_citations_splits_combined_brackets():
    answer = "A [ragas, s.3, §3]. B [e5, s.4, §3; bge_m3, s.2-3, §2]. Not one: [1]."
    assert extract_citations(answer) == ["[ragas, s.3, §3]", "[e5, s.4, §3]", "[bge_m3, s.2–3, §2]"]


def test_check_citations_flags_labels_not_in_context():
    docs = [doc()]
    assert check_citations("Doğru [ragas, s.3, §3].", docs) == []
    assert check_citations("Uydurma [ragas, s.9, §5].", docs) == ["[ragas, s.9, §5]"]


def test_chain_returns_docs_question_and_answer():
    docs = [doc()]
    retriever = RunnableLambda(lambda question: docs)
    llm = FakeListChatModel(responses=["Cevap [ragas, s.3, §3]."])

    result = build_chain(retriever, llm).invoke("Ragas neyi ölçer?")

    assert result == {
        "docs": docs,
        "question": "Ragas neyi ölçer?",
        "query": {"tr": "Ragas neyi ölçer?"},  # no translator: no LLM call for "en"
        "answer": "Cevap [ragas, s.3, §3].",
    }


def test_chain_with_translator_passes_both_languages_to_the_retriever():
    seen = []
    retriever = RunnableLambda(lambda query: seen.append(query) or [doc()])
    translator = RunnableLambda(lambda question: "What does Ragas measure?")
    llm = FakeListChatModel(responses=["Cevap [ragas, s.3, §3]."])

    result = build_chain(retriever, llm, translator).invoke("Ragas neyi ölçer?")

    assert seen == [{"tr": "Ragas neyi ölçer?", "en": "What does Ragas measure?"}]
    assert result["query"]["en"] == "What does Ragas measure?"


def test_answer_kind_separates_refusal_partial_and_answer():
    assert answer_kind("Dokümanda bulamadım.") == "refusal"
    assert answer_kind("  Dokümanda bulamadım.\n") == "refusal"
    assert answer_kind("E5 ortalama alır [e5, s.4, §4].\n\nDokümanda bulamadım.") == "partial"
    assert answer_kind("Ragas üç boyutu ölçer [ragas, s.3, §3].") == "answer"


def test_label_normalization_only_touches_page_ranges():
    assert extract_citations("x [bge_m3, s.2-3, §2]") == ["[bge_m3, s.2–3, §2]"]
    assert extract_citations("x [bge_m-3, s.4, §3.2]") == ["[bge_m-3, s.4, §3.2]"]


def test_chain_truecases_the_question_before_search_and_prompt():
    seen = []
    retriever = RunnableLambda(lambda query: seen.append(query) or [doc()])
    llm = FakeListChatModel(responses=["Cevap [ragas, s.3, §3]."])
    chain = build_chain(retriever, llm, vocab={"qlora": "QLoRA"})
    result = chain.invoke("qlora nedir?")
    assert seen == [{"tr": "QLoRA nedir?"}]
    assert result["question"] == "QLoRA nedir?"
