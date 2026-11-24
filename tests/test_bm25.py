from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.bm25 import BM25Retriever, tokenize


def test_technical_terms_stay_whole():
    assert tokenize("Recall@100 of bge-m3 is 55.8") == ["recall@100", "bge-m3", "55.8"]


def test_punctuation_case_and_stopwords_are_removed():
    assert tokenize("What are the values of BM25, (Dense)?") == ["values", "bm25", "dense"]


def test_sentence_final_period_is_not_part_of_the_word():
    assert tokenize("We use BM25.") == ["use", "bm25"]


def test_english_lowercasing_not_turkish():
    # Turkish lowercasing would give "ıdf"; the papers are English.
    assert tokenize("IDF") == ["idf"]


def test_turkish_characters_survive():
    assert tokenize("Şekil ığdır İstanbul") == ["şekil", "ığdır", "istanbul"]


# Okapi idf is <= 0 for a word found in half or more of the documents, so the tests add
# unrelated filler documents to get a realistic corpus.
FILLER = ["quantization of weights", "paged optimizers", "multilingual corpora", "human judges"]


def docs(*texts: str) -> list[Document]:
    return [
        Document(page_content=t, metadata={"chunk_id": f"c{i}"})
        for i, t in enumerate([*texts, *FILLER])
    ]


def test_rare_word_ranks_first():
    retriever = BM25Retriever.from_documents(
        docs(
            "Self-RAG retrieval results on PopQA.",
            "Self-RAG outperforms Ret-ChatGPT on PopQA.",
            "Self-RAG training details.",
        )
    )
    ids = [d.metadata["chunk_id"] for d in retriever.invoke("Ret-ChatGPT accuracy")]
    assert ids[0] == "c1"


def test_no_shared_word_returns_nothing():
    retriever = BM25Retriever.from_documents(docs("dense retrieval", "sparse retrieval"))
    assert retriever.invoke("reranker latency") == []


def test_k_limits_results():
    retriever = BM25Retriever.from_documents(docs(*["bm25 text"] * 3), k=2)
    assert len(retriever.invoke("bm25")) == 2


def test_works_inside_an_lcel_chain():
    retriever = BM25Retriever.from_documents(docs("bm25 scoring", "dense vectors"))
    chain = retriever | RunnableLambda(lambda found: [d.metadata["chunk_id"] for d in found])
    assert chain.invoke("bm25") == ["c0"]
