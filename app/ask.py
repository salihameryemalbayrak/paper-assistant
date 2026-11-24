"""Answer a question from the papers with cited sources (retrieval-augmented generation).

Chain (LangChain Expression Language):

    question ─┬─ retriever ──────────► docs ─┐
              └─ passthrough ────► question ─┴─► format context ─► prompt ─► LLM ─► text

The result keeps the retrieved docs next to the answer, so the sources can be shown and
the citations in the answer can be checked against them.

Usage:
    uv run python -m app.ask "Ragas bir RAG sistemini hangi boyutlarda değerlendirir?"
"""

import re
import sys
import time
from collections.abc import Sequence
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
    return re.sub(r"\s+", " ", label.replace("-", "–")).strip()


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


def is_refusal(answer: str) -> bool:
    return NOT_FOUND in answer


def build_chain(retriever: Runnable, llm: BaseChatModel) -> Runnable:
    """question -> {"question", "docs", "answer"}."""
    to_prompt_inputs = RunnableLambda(
        lambda x: {"context": format_docs(x["docs"]), "question": x["question"]}
    )
    answer = to_prompt_inputs | PROMPT | llm | StrOutputParser()
    return RunnableParallel(docs=retriever, question=RunnablePassthrough()).assign(answer=answer)


def main() -> None:
    from app.config import get_settings
    from app.llm import get_chat_model
    from app.vectorstore import get_vectorstore

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        sys.exit('usage: uv run python -m app.ask "soru"')

    settings = get_settings()
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": CONTEXT_K})
    chain = build_chain(retriever, get_chat_model(settings))

    start = time.perf_counter()
    result = chain.invoke(question)
    elapsed = time.perf_counter() - start

    print(result["answer"].strip())
    print("\nKaynaklar (bağlama verilen chunk'lar):")
    for doc in result["docs"]:
        print(f"  {citation_label(doc.metadata)} {doc.metadata['chunk_id']}")
    if unknown := check_citations(result["answer"], result["docs"]):
        print(f"\nUYARI: bağlamda olmayan kaynak etiketi: {unknown}")
    print(f"\n[{settings.llm_model} | {settings.embedding_model} | {elapsed:.1f} sn]")


if __name__ == "__main__":
    main()
