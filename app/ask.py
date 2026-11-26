"""Answer a question from the papers with cited sources (retrieval-augmented generation).

Chain (LangChain Expression Language):

    question ─┬─ to query ─► {tr, en} ─► retriever ─► docs ─┐
              └─ passthrough ─────────────────────► question ─┴─► context ─► prompt ─► LLM

"to query" translates the question (TR -> EN) only for retrievers that use English
branches (app.retrieval); otherwise the query is just {"tr": question}.

The result keeps the retrieved docs next to the answer, so the sources can be shown and
the citations in the answer can be checked against them.

Usage:
    uv run python -m app.ask "Ragas bir RAG sistemini hangi boyutlarda değerlendirir?"
"""

import re
import sys
import time
from collections.abc import Sequence
from operator import itemgetter
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough

NOT_FOUND = "Dokümanda bulamadım."
CONTEXT_K = 5  # chunks given to the LLM

# English instructions: small models follow them more reliably; the answer is in Turkish.
SYSTEM_PROMPT = """You answer questions about research papers using ONLY the context below.

Rules:
1. Use only facts stated in the context. Do not add outside knowledge.
2. After every claim, cite its source: copy the label in square brackets exactly as it \
appears above the passage, for example [ragas, s.3, §3].
3. If the context does not contain the answer, reply with exactly this sentence and \
nothing else: {not_found}
4. Write the answer in Turkish. Keep direct quotes, technical terms and names in their \
original language.
5. Be concise.

Context:
{context}"""

PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "{question}")]
).partial(not_found=NOT_FOUND)

# "3.2 Training" -> "3.2", "A Appendix" -> "A"
_SECTION_NUMBER = re.compile(r"^((?:\d+|[A-Z])(?:\.\d+)*)\.?\s")
# a bracket that contains a page reference: [ragas, s.3, §3]
_CITATION = re.compile(r"\[([^\[\]]*\bs\.\s?\d[^\[\]]*)\]")


def citation_label(metadata: dict[str, Any]) -> str:
    """[short_name, s.page, §section] for a chunk, e.g. [ragas, s.2–3, §3]."""
    pages = metadata["pages"]
    parts = [metadata["paper"], f"s.{pages[0]}" if len(pages) == 1 else f"s.{pages[0]}–{pages[-1]}"]
    section = metadata["section"]
    if match := _SECTION_NUMBER.match(section):
        parts.append(f"§{match.group(1)}")
    elif section:
        parts.append(f"§{section}")
    return "[" + ", ".join(parts) + "]"


def format_docs(docs: Sequence[Document]) -> str:
    """The context block: each chunk's original text under its citation label."""
    return "\n\n".join(f"{citation_label(d.metadata)}\n{d.metadata['text']}" for d in docs)


def _normalize_label(label: str) -> str:
    """Collapse whitespace; write page ranges with an en dash (s.2-3 -> s.2–3)."""
    label = re.sub(r"(s\.\s?\d+)\s?-\s?(\d+)", r"\1–\2", label)
    return re.sub(r"\s+", " ", label).strip()


def extract_citations(answer: str) -> list[str]:
    """Citation labels in the answer; "[a, s.1; b, s.2]" counts as two labels."""
    labels = []
    for inner in _CITATION.findall(answer):
        labels += [f"[{_normalize_label(part)}]" for part in inner.split(";") if part.strip()]
    return labels


def check_citations(answer: str, docs: Sequence[Document]) -> list[str]:
    """Labels cited in the answer that were not in the context: invented sources."""
    given = {_normalize_label(citation_label(d.metadata)) for d in docs}
    return [label for label in extract_citations(answer) if label not in given]


def answer_kind(answer: str) -> str:
    """ "refusal": only the fixed sentence; "partial": content plus the sentence
    (the model answered part of the question); "answer": no refusal sentence."""
    if NOT_FOUND not in answer:
        return "answer"
    rest = answer.replace(NOT_FOUND, "").strip(" \n.")
    return "partial" if rest else "refusal"


def build_chain(
    retriever: Runnable, llm: BaseChatModel, translator: Runnable[str, str] | None = None
) -> Runnable:
    """question -> {"question", "query", "docs", "answer"}."""
    to_query = (
        RunnableParallel(tr=RunnablePassthrough(), en=translator)
        if translator
        else RunnableLambda(lambda question: {"tr": question})
    )
    to_prompt_inputs = RunnableLambda(
        lambda x: {"context": format_docs(x["docs"]), "question": x["question"]}
    )
    answer = to_prompt_inputs | PROMPT | llm | StrOutputParser()
    return (
        RunnableParallel(question=RunnablePassthrough(), query=to_query)
        .assign(docs=itemgetter("query") | retriever)
        .assign(answer=answer)
    )


def main() -> None:
    from app.config import get_settings
    from app.llm import get_chat_model
    from app.retrieval import build_retriever, needs_translation
    from app.translate import build_translator

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        sys.exit('usage: uv run python -m app.ask "soru"')

    settings = get_settings()
    llm = get_chat_model(settings)
    retriever = build_retriever(
        settings.retriever, CONTEXT_K, reranker=settings.reranker,
        candidates=settings.rerank_candidates,
    )  # fmt: skip
    translator = (
        build_translator(llm) if needs_translation(settings.retriever, settings.reranker) else None
    )
    chain = build_chain(retriever, llm, translator)

    start = time.perf_counter()
    result = chain.invoke(question)
    elapsed = time.perf_counter() - start

    if "en" in result["query"]:
        print(f"[EN query: {result['query']['en']}]\n")
    print(result["answer"].strip())
    print("\nKaynaklar (bağlama verilen chunk'lar):")
    for doc in result["docs"]:
        print(f"  {citation_label(doc.metadata)} {doc.metadata['chunk_id']}")
    if unknown := check_citations(result["answer"], result["docs"]):
        print(f"\nUYARI: bağlamda olmayan kaynak etiketi: {unknown}")
    rerank = f" + rerank {settings.reranker}" if settings.reranker else ""
    models = f"{settings.llm_model} | {settings.retriever}{rerank} | {settings.embedding_model}"
    print(f"\n[{models} | {elapsed:.1f} sn]")


if __name__ == "__main__":
    main()
