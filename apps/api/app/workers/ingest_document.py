from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.document import DocumentRead, DocumentStatus
from app.services.chunker import chunk_document
from app.services.document_parser import parse_pdf_bytes
from app.services.document_store import create_document, get_document, save_chunks, update_document_status
from app.services.vector_store import vector_store

_MAX_FILENAME_STEM = 40


async def save_uploaded_document(file: UploadFile) -> tuple[DocumentRead, bytes]:
    """Validate, read bytes, create DB record. Returns (document, raw_bytes)."""
    filename = file.filename or "uploaded.pdf"
    suffix = Path(filename).suffix.lower()

    if suffix != ".pdf":
        raise ValueError("Only PDF files are accepted.")

    contents = await file.read()

    if len(contents) == 0:
        raise ValueError("The uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise ValueError(
            f"File size exceeds the {settings.max_upload_size_mb} MB limit "
            f"({len(contents) // (1024 * 1024)} MB received)."
        )

    # Best-effort disk save (works in local dev; silently skipped on ephemeral hosts)
    file_path: str | None = None
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem[:_MAX_FILENAME_STEM]
        safe_name = f"{stem}-{uuid4().hex[:8]}.pdf"
        destination = settings.upload_dir / safe_name
        destination.write_bytes(contents)
        file_path = str(destination)
    except Exception:
        pass

    document = create_document(title=filename, file_type="pdf", file_path=file_path)
    return document, contents


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
        parsed = parse_pdf_bytes(title=document.title, contents=contents)
        chunks = chunk_document(document_id=document_id, parsed=parsed)
        save_chunks(document_id, chunks)
        vector_store.upsert_chunks(chunks)
        return update_document_status(document_id, DocumentStatus.ready)
    except Exception:
        update_document_status(document_id, DocumentStatus.failed)
        raise
