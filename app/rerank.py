"""Second-stage reranking with a cross-encoder.

Two-stage retrieval:

    query {tr, en} ─┬─ retriever (e.g. 20 candidates) ─► docs ─┐
                    └─ passthrough ─────────────► query ───────┴─► cross-encoder ─► top k

Bi-encoder (dense search): question and chunk are embedded separately; chunk vectors are
computed once at indexing time, so search is fast, but the two texts never "see" each
other. Cross-encoder: question and chunk go through the transformer together
("[question] [SEP] [chunk]"), attention compares every word of one with every word of
the other, and the model outputs one relevance score. Much more precise, but nothing can
be precomputed: one model run per (question, chunk) pair. Hence only on the candidates.

LangChain's CrossEncoderReranker (langchain-classic) builds the (question, page_content)
pairs, calls model.score(pairs), sorts by score and keeps top_n. Its HuggingFace model
wrapper lives in the sunset langchain-community package, so SentenceTransformerCrossEncoder
below implements the langchain_core BaseCrossEncoder interface itself.
"""

import re
from collections.abc import Sequence

from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_core.cross_encoders import BaseCrossEncoder
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough

# reranker -> (Hugging Face model, query language it reads). See docs/DECISIONS.md, D33.
RERANKERS: dict[str, tuple[str, str]] = {
    "bge_m3": ("BAAI/bge-reranker-v2-m3", "tr"),  # multilingual, 568M parameters
    "minilm_en": ("cross-encoder/ms-marco-MiniLM-L6-v2", "en"),  # English only, 23M
}


def compact(text: str) -> str:
    """Collapse Markdown table padding: "|--------|" -> "|---|", runs of spaces -> one.

    BERT-style tokenizers count every "-" as a token; without this, 94 of 142 table chunks
    exceeded MiniLM's 512-token limit and lost their last rows to silent truncation.
    """
    return re.sub(r"-{3,}", "---", re.sub(r"[ \t]{2,}", " ", text))


class SentenceTransformerCrossEncoder(BaseCrossEncoder):
    """langchain_core cross-encoder interface over sentence-transformers' CrossEncoder.

    Counts pairs longer than the model's max_length (they would be truncated silently).
    """

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import CrossEncoder
        from transformers import AutoTokenizer

        self.model_name = model_name
        self.model = CrossEncoder(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.pairs_scored = 0
        self.pairs_truncated = 0

    def score(self, text_pairs: list[tuple[str, str]]) -> list[float]:
        pairs = [(query, compact(passage)) for query, passage in text_pairs]
        for query, passage in pairs:
            if len(self.tokenizer(query, passage)["input_ids"]) > self.model.max_length:
                self.pairs_truncated += 1
        self.pairs_scored += len(pairs)
        # Only the order matters: sigmoid or raw logits rank the same (monotonic).
        return [float(s) for s in self.model.predict(pairs, show_progress_bar=False)]


def with_reranker(
    retriever: Runnable, cross_encoder: BaseCrossEncoder, lang: str, top_n: int
) -> Runnable:
    """Rerank the retriever's candidates with the question in `lang` ("tr" or "en")."""
    reranker = CrossEncoderReranker(model=cross_encoder, top_n=top_n)

    def rerank(x: dict) -> list[Document]:
        docs: Sequence[Document] = reranker.compress_documents(x["docs"], x["query"][lang])
        return list(docs)

    return RunnableParallel(query=RunnablePassthrough(), docs=retriever) | RunnableLambda(rerank)
