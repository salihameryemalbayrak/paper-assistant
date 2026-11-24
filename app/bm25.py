"""BM25 keyword retriever with a tokenizer tuned for technical English text.

Why our own class (see docs/DECISIONS.md, D29): LangChain's BM25Retriever lives in the
sunset langchain-community package and splits text on whitespace only ("BM25," and
"bm25" become different words). Scoring is done by rank-bm25 (BM25Okapi); this module
adds the tokenizer and the LangChain retriever interface.

BM25 score of a chunk D for a query Q (rank-bm25 defaults k1=1.5, b=0.75):

    score(D, Q) = sum over words w in Q of
                  idf(w) * f(w, D) * (k1 + 1) / (f(w, D) + k1 * (1 - b + b * |D| / avg_len))

    idf(w) = ln((N - n(w) + 0.5) / (n(w) + 0.5))   # N chunks, n(w) chunks containing w

- idf: rare words count more ("ret-chatgpt" 5.2, "self-rag" 0.9 in our corpus).
- k1: saturation; the 10th occurrence of a word adds much less than the first.
- b: length normalization; long chunks do not win just by containing more words.
"""

import re

import numpy as np
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# A word is letters/digits, optionally joined by ".", "@" or "-" so that technical
# terms stay whole: "recall@100", "55.8", "bge-m3", "ret-chatgpt".
_WORD = re.compile(r"[^\W_]+(?:[.@\-][^\W_]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase words without English stopwords.

    English lowercasing on purpose: the papers are English, and the Turkish rule
    (I -> ı, see app/text.py) would turn "IDF" into "ıdf". Only "İ" is mapped first:
    Python lowercases it to "i" + a combining dot (U+0307), which the word pattern does
    not treat as a letter, so "İstanbul" would split into "i" and "stanbul".
    """
    text = text.replace("İ", "i").lower()
    return [w for w in _WORD.findall(text) if w not in ENGLISH_STOP_WORDS]


class BM25Retriever(BaseRetriever):
    """In-memory BM25 over a fixed list of documents (built in milliseconds at startup)."""

    index: BM25Okapi
    docs: list[Document]
    k: int = 10

    @classmethod
    def from_documents(cls, docs: list[Document], k: int = 10) -> "BM25Retriever":
        return cls(index=BM25Okapi([tokenize(d.page_content) for d in docs]), docs=docs, k=k)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        scores = self.index.get_scores(tokenize(query))
        best = np.argsort(-scores, kind="stable")[: self.k]
        # Unlike dense search, a chunk sharing no word with the query scores 0: leave it out,
        # otherwise rank fusion would give rank credit to arbitrary chunks. Note: Okapi idf
        # is <= 0 for words in half or more of the chunks, so such words never match alone.
        return [self.docs[i] for i in best if scores[i] > 0]


def load_bm25_retriever(k: int = 10) -> BM25Retriever:
    """BM25 over data/chunks.jsonl, indexing the same search_text as the dense index."""
    from ingest.chunk import load_chunks
    from ingest.index import chunk_to_document

    return BM25Retriever.from_documents([chunk_to_document(c) for c in load_chunks()], k=k)
