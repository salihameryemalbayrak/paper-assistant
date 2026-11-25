"""Translate a Turkish question into English for keyword search (TR -> EN).

Why: BM25 matches words, and the papers are English. "seyrek arama" shares no word with
"sparse retrieval", so BM25 needs the English question. Dense search can use both.

Chain (LCEL):

    question ─┬─ prompt ─► LLM ─► text ─┐
              └─ original question ─────┴─► clean ─► English question

Temperature is 0 (app/config.py): the most likely token is picked at every step, so the
same question always gets the same translation and eval runs are reproducible.

Usage:
    uv run python -m app.translate "M3-Embedding'in seyrek arama yöntemi neden zayıf?"
"""

import re
import sys
import time

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough

SYSTEM_PROMPT = """You translate questions about research papers from Turkish into \
English for a keyword search engine.

Rules:
1. Keep technical terms, model names, dataset names, metric names and numbers exactly \
as written (for example: Recall@100, PopQA, Ret-ChatGPT, bge-m3, 13B).
2. Translate references to paper parts: "Tablo 6" -> "Table 6", "Şekil 1" -> "Figure 1".
3. If a Turkish word is followed by its English term in parentheses, keep only the \
English term: "seyrek (sparse)" -> "sparse".
4. If the question is already in English, return it unchanged.
5. Reply with the translated question only: no quotes, no explanation."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{question}")])

# Labels small models sometimes put before the answer: "Translation:", "English question:"
_LABEL = re.compile(r"^(?:english\s+)?(?:translation|question|english)\s*:\s*", re.IGNORECASE)
_QUOTES = "\"'“”‘’«»"


def clean_translation(raw: str, original: str) -> str:
    """The first non-empty line, without a leading label or surrounding quotes.

    Falls back to the original question when nothing is left, so a failed translation
    degrades to the untranslated search instead of an empty query.
    """
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    text = _LABEL.sub("", lines[0]).strip().strip(_QUOTES).strip() if lines else ""
    return text or original


def build_translator(llm: BaseChatModel) -> Runnable[str, str]:
    """question -> English question."""
    raw = PROMPT | llm | StrOutputParser()
    return RunnableParallel(raw=raw, original=RunnablePassthrough()) | RunnableLambda(
        lambda x: clean_translation(x["raw"], x["original"])
    )


def main() -> None:
    from app.config import get_settings
    from app.llm import get_chat_model

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        sys.exit('usage: uv run python -m app.translate "soru"')

    settings = get_settings()
    translator = build_translator(get_chat_model(settings))
    start = time.perf_counter()
    english = translator.invoke(question)
    print(english)
    print(f"\n[{settings.llm_model} | {time.perf_counter() - start:.1f} sn]")


if __name__ == "__main__":
    main()
