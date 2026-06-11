import re

from app.schemas.document import SourceChunk
from app.services import embeddings as _emb
from app.services.vector_store import vector_store

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False

_RERANK_FETCH_MULTIPLIER = 3   # fetch 3x more candidates before reranking
_BM25_WEIGHT = 0.3             # combined score = 0.7 * vector + 0.3 * bm25


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _rerank(query: str, chunks: list[SourceChunk], top_k: int) -> list[SourceChunk]:
    """BM25-based reranking of vector-retrieved candidates."""
    if not _BM25_AVAILABLE or len(chunks) <= top_k:
        return chunks[:top_k]

    corpus = [_tokenize(c.content) for c in chunks]
    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(_tokenize(query))

    # Normalize BM25 scores to [0, 1]
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    norm_bm25 = [s / max_bm25 for s in bm25_scores]

    # Combine with vector score (already in [0, 1] for cosine)
    combined = [
        (chunk, (1 - _BM25_WEIGHT) * (chunk.score or 0.0) + _BM25_WEIGHT * bm25_score)
        for chunk, bm25_score in zip(chunks, norm_bm25)
    ]
    combined.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in combined[:top_k]]


def retrieve_context(document_id: str, query: str, limit: int = 5) -> list[SourceChunk]:
    fetch_limit = limit * _RERANK_FETCH_MULTIPLIER if _BM25_AVAILABLE else limit
    query_vector = _emb.embed_text(query)
    candidates = vector_store.search(
        document_id=document_id, query_vector=query_vector, limit=fetch_limit
    )
    return _rerank(query, candidates, limit)


def retrieve_context_global(query: str, limit: int = 5) -> list[SourceChunk]:
    """Retrieve from all documents (no document_id filter)."""
    fetch_limit = limit * _RERANK_FETCH_MULTIPLIER if _BM25_AVAILABLE else limit
    query_vector = _emb.embed_text(query)
    candidates = vector_store.search_global(query_vector=query_vector, limit=fetch_limit)
    return _rerank(query, candidates, limit)
