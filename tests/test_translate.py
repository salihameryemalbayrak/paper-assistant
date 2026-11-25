"""Tests for the TR -> EN query translation chain. A fake LLM: no Ollama."""

from langchain_core.language_models import FakeListChatModel

from app.translate import PROMPT, build_translator, clean_translation

QUESTION = "M3-Embedding'in seyrek (sparse) arama yöntemi neden zayıf kalıyor?"


def test_plain_translation_is_kept():
    assert clean_translation("Why is sparse retrieval weak?", QUESTION) == (
        "Why is sparse retrieval weak?"
    )


def test_label_quotes_and_explanation_are_removed():
    raw = 'Translation: "Why is sparse retrieval weak?"\n\nNote: I kept the term sparse.'
    assert clean_translation(raw, QUESTION) == "Why is sparse retrieval weak?"


def test_english_question_label_is_removed():
    assert clean_translation("English question: What is QLoRA?", "QLoRA nedir?") == (
        "What is QLoRA?"
    )


def test_empty_output_falls_back_to_the_original():
    assert clean_translation("  \n ", QUESTION) == QUESTION
    assert clean_translation('""', QUESTION) == QUESTION


def test_turkish_characters_survive_cleaning():
    # A question the model left untranslated must come back byte for byte.
    assert clean_translation("Şekil 1'de ığdır İstanbul?", QUESTION) == "Şekil 1'de ığdır İstanbul?"


def test_prompt_accepts_a_plain_string():
    # A template with one variable maps a str input to that variable.
    messages = PROMPT.invoke(QUESTION).messages
    assert messages[1].content == QUESTION


def test_chain_translates_and_cleans():
    llm = FakeListChatModel(responses=["Translation: Why is sparse retrieval weak?"])
    assert build_translator(llm).invoke(QUESTION) == "Why is sparse retrieval weak?"
