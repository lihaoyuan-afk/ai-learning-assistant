from datetime import datetime
from enum import Enum

from pydantic import BaseModel, HttpUrl


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class SourceChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    page_number: int | None = None
    section_title: str | None = None
    score: float | None = None


class DocumentRead(BaseModel):
    id: str
    title: str
    file_type: str
    status: DocumentStatus
    file_path: str | None = None
    summary: str | None = None
    is_public: bool = False
    forked_from: str | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentRead]


class DocumentIngestResponse(BaseModel):
    document: DocumentRead
    message: str


class ImportUrlRequest(BaseModel):
    url: HttpUrl

