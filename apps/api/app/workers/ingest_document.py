from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.document import DocumentRead, DocumentStatus
from app.services.chunker import chunk_document
from app.services.document_parser import (
    DocumentParseError,
    parse_pdf_bytes,
    parse_text_bytes,
    parse_url,
    parse_youtube_url,
)
from app.services.document_store import create_document, get_document, save_chunks, update_document_status
from app.services.vector_store import vector_store

_MAX_FILENAME_STEM = 40
_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
_YOUTUBE_HOSTS = {"youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com",
                  "bilibili.com", "www.bilibili.com", "m.bilibili.com"}


def _is_video_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        return urlparse(url).hostname in _YOUTUBE_HOSTS
    except Exception:
        return False


async def save_uploaded_document(
    file: UploadFile, user_id: str | None = None
) -> tuple[DocumentRead, bytes]:
    """Validate, read bytes, create DB record. Returns (document, raw_bytes)."""
    filename = file.filename or "uploaded.pdf"
    suffix = Path(filename).suffix.lower()

    allowed = {".pdf"} | _TEXT_SUFFIXES
    if suffix not in allowed:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Accepted: PDF, TXT, MD."
        )

    contents = await file.read()

    if len(contents) == 0:
        raise ValueError("The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise ValueError(
            f"File size exceeds the {settings.max_upload_size_mb} MB limit "
            f"({len(contents) // (1024 * 1024)} MB received)."
        )

    # Best-effort disk save
    file_path: str | None = None
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem[:_MAX_FILENAME_STEM]
        safe_name = f"{stem}-{uuid4().hex[:8]}{suffix}"
        destination = settings.upload_dir / safe_name
        destination.write_bytes(contents)
        file_path = str(destination)
    except Exception:
        pass

    file_type = "pdf" if suffix == ".pdf" else "text"
    document = create_document(title=filename, file_type=file_type, file_path=file_path, user_id=user_id)
    return document, contents


def create_url_document(url: str, user_id: str | None = None) -> DocumentRead:
    """Create a document record for a URL import (title resolved later)."""
    return create_document(title=url[:120], file_type="url", file_path=None, user_id=user_id)


def ingest_document(document_id: str, contents: bytes | None = None) -> DocumentRead:
    """Parse and vectorize a document.

    Pass `contents` to process from memory (production).
    If omitted, falls back to reading from `document.file_path` (local dev).
    """
    document = get_document(document_id)
    if document is None:
        raise ValueError(f"Unknown document: {document_id}")

    if contents is None:
        if not document.file_path:
            raise ValueError("No file contents available for ingestion.")
        contents = Path(document.file_path).read_bytes()

    update_document_status(document_id, DocumentStatus.processing)
    try:
        if document.file_type == "text":
            parsed = parse_text_bytes(title=document.title, contents=contents)
        else:
            parsed = parse_pdf_bytes(title=document.title, contents=contents)
        chunks = chunk_document(document_id=document_id, parsed=parsed)
        save_chunks(document_id, chunks)
        vector_store.upsert_chunks(chunks)
        return update_document_status(document_id, DocumentStatus.ready)
    except Exception:
        update_document_status(document_id, DocumentStatus.failed)
        raise


def ingest_url(document_id: str, url: str) -> DocumentRead:
    """Fetch a URL (or video), parse content, and vectorize."""
    document = get_document(document_id)
    if document is None:
        raise ValueError(f"Unknown document: {document_id}")

    update_document_status(document_id, DocumentStatus.processing)
    try:
        if _is_video_url(url):
            parsed = parse_youtube_url(url)
        else:
            parsed = parse_url(url)

        # Update title from actual page title
        from app.services.document_store import update_document_title
        update_document_title(document_id, parsed.title)

        chunks = chunk_document(document_id=document_id, parsed=parsed)
        save_chunks(document_id, chunks)
        vector_store.upsert_chunks(chunks)
        return update_document_status(document_id, DocumentStatus.ready)
    except DocumentParseError:
        update_document_status(document_id, DocumentStatus.failed)
        raise
    except Exception:
        update_document_status(document_id, DocumentStatus.failed)
        raise
