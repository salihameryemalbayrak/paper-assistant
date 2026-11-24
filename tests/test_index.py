"""Indexing tests that need neither Docker nor a model download.

Qdrant runs in-process (location=":memory:") and a fake embedding replaces the real model.
"""

import uuid

from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_qdrant import QdrantVectorStore

from app.embeddings import encode_kwargs
from app.vectorstore import collection_name
from ingest.chunk import Chunk, ChunkType
from ingest.index import chunk_to_document, point_id


def make_chunk(chunk_id: str = "e5-0007", text: str = "We set k = 2.") -> Chunk:
    return Chunk(
        id=chunk_id,
        paper="e5",
        page=3,
        pages=[3, 4],
        section="3 CCPairs",
        type=ChunkType.TEXT,
        text=text,
        search_text=f"Text Embeddings > 3 CCPairs\n{text}",
    )


def test_point_id_is_a_stable_uuid():
    assert point_id("e5-0007") == point_id("e5-0007")
    assert point_id("e5-0007") != point_id("e5-0008")
    uuid.UUID(point_id("e5-0007"))  # raises if not a valid UUID


def test_document_embeds_search_text_and_keeps_original_text_as_metadata():
    doc = chunk_to_document(make_chunk())

    assert doc.page_content.startswith("Text Embeddings > 3 CCPairs\n")
    assert doc.metadata == {
        "chunk_id": "e5-0007",
        "paper": "e5",
        "page": 3,
        "pages": [3, 4],
        "section": "3 CCPairs",
        "type": "text",
        "text": "We set k = 2.",
    }


def test_collection_name_per_model():
    assert collection_name("BAAI/bge-m3") == "chunks_bge_m3"
    assert collection_name("intfloat/multilingual-e5-small") == "chunks_multilingual_e5_small"


def test_e5_gets_query_and_passage_prefixes():
    passage, query = encode_kwargs("intfloat/multilingual-e5-small")
    assert passage["prompt"] == "passage: "
    assert query["prompt"] == "query: "


def test_model_without_prefix_still_has_non_empty_query_kwargs():
    passage, query = encode_kwargs("BAAI/bge-m3")
    assert "prompt" not in passage and "prompt" not in query
    assert query, "empty query kwargs would make LangChain reuse the passage kwargs"


def test_documents_round_trip_through_qdrant():
    chunks = [make_chunk("e5-0001", "alpha"), make_chunk("e5-0002", "Türkçe şekil açıklaması")]
    store = QdrantVectorStore.from_documents(
        [chunk_to_document(c) for c in chunks],
        DeterministicFakeEmbedding(size=16),
        location=":memory:",
        collection_name="test",
    )

    hits = store.similarity_search(chunks[1].search_text, k=1)

    assert hits[0].metadata["chunk_id"] == "e5-0002"
    assert hits[0].metadata["text"] == "Türkçe şekil açıklaması"
