from uuid import uuid4

from app.schemas.document import SourceChunk
from app.services.vector_store import vector_store


def _make_chunk(document_id: str, content: str, page: int = 1) -> SourceChunk:
    return SourceChunk(
        id=uuid4().hex,
        document_id=document_id,
        chunk_index=0,
        content=content,
        page_number=page,
    )


def test_upsert_and_search_returns_chunk(mock_embeddings):
    chunk = _make_chunk("doc1", "machine learning fundamentals")
    vector_store.upsert_chunks([chunk])

    from app.core.config import settings
    results = vector_store.search(
        document_id="doc1",
        query_vector=[0.1] * settings.embedding_dimensions,
        limit=5,
    )
    assert len(results) == 1
    assert results[0].document_id == "doc1"
    assert results[0].content == "machine learning fundamentals"


def test_search_isolates_by_document_id(mock_embeddings):
    from app.core.config import settings

    chunk_a = _make_chunk("docA", "content for document A")
    chunk_b = _make_chunk("docB", "content for document B")
    vector_store.upsert_chunks([chunk_a, chunk_b])

    results = vector_store.search("docA", [0.1] * settings.embedding_dimensions)
    assert all(r.document_id == "docA" for r in results)


def test_search_returns_page_number(mock_embeddings):
    from app.core.config import settings

    chunk = _make_chunk("doc1", "neural networks", page=7)
    vector_store.upsert_chunks([chunk])

    results = vector_store.search("doc1", [0.1] * settings.embedding_dimensions)
    assert results[0].page_number == 7


def test_upsert_empty_chunks_is_safe(mock_embeddings):
    vector_store.upsert_chunks([])


def test_search_empty_collection_returns_empty(mock_embeddings):
    from app.core.config import settings

    results = vector_store.search("nonexistent", [0.1] * settings.embedding_dimensions)
    assert results == []


def test_upsert_multiple_chunks(mock_embeddings):
    from app.core.config import settings

    chunks = [_make_chunk("doc1", f"chunk content {i}", page=i + 1) for i in range(5)]
    vector_store.upsert_chunks(chunks)

    results = vector_store.search("doc1", [0.1] * settings.embedding_dimensions, limit=10)
    assert len(results) == 5
