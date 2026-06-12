from pathlib import Path
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, FieldCondition, Filter, FilterSelector,
    KeywordIndexParams, MatchAny, MatchValue, PayloadSchemaType, PointStruct, VectorParams,
)

from app.core.config import settings
from app.schemas.document import SourceChunk
from app.services import embeddings as _emb


class VectorStore:
    def __init__(self) -> None:
        self._client: QdrantClient | None = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            if settings.qdrant_url == ":memory:":
                self._client = QdrantClient(":memory:")
            elif settings.qdrant_url == ":local:":
                storage = Path(settings.qdrant_storage_path)
                storage.mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=str(storage))
            else:
                self._client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key or None,
                )
        return self._client

    def _ensure_collection(self, client: QdrantClient) -> None:
        names = {c.name for c in client.get_collections().collections}
        if settings.qdrant_collection not in names:
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload index so filtered queries work under Qdrant Cloud strict mode
            client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def upsert_chunks(self, chunks: list[SourceChunk]) -> None:
        if not chunks:
            return
        client = self._get_client()
        self._ensure_collection(client)
        vectors = _emb.embed_texts([c.content for c in chunks])
        points = [
            PointStruct(
                id=UUID(chunk.id),
                vector=vector,
                payload={
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        client.upsert(collection_name=settings.qdrant_collection, points=points)

    def search(
        self, document_id: str, query_vector: list[float], limit: int = 5
    ) -> list[SourceChunk]:
        client = self._get_client()
        self._ensure_collection(client)
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            SourceChunk(
                id=str(hit.id),
                document_id=hit.payload.get("document_id", document_id),
                chunk_index=hit.payload.get("chunk_index", 0),
                content=hit.payload.get("content", ""),
                page_number=hit.payload.get("page_number"),
                score=hit.score,
            )
            for hit in response.points
        ]

    def search_global(
        self,
        query_vector: list[float],
        limit: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        """Search across documents. Optionally restrict to a list of document_ids."""
        client = self._get_client()
        self._ensure_collection(client)
        query_filter = None
        if document_ids is not None:
            query_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))]
            )
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            SourceChunk(
                id=str(hit.id),
                document_id=hit.payload.get("document_id", ""),
                chunk_index=hit.payload.get("chunk_index", 0),
                content=hit.payload.get("content", ""),
                page_number=hit.payload.get("page_number"),
                score=hit.score,
            )
            for hit in response.points
        ]

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all vectors associated with a document."""
        client = self._get_client()
        self._ensure_collection(client)
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            ),
        )


vector_store = VectorStore()
