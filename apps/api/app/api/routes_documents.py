from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.document import DocumentIngestResponse, DocumentListResponse, DocumentRead, ImportUrlRequest
from app.services.document_parser import DocumentParseError
from app.services.document_store import delete_document, get_document, list_documents
from app.workers.ingest_document import (
    create_url_document,
    ingest_document,
    ingest_url,
    save_uploaded_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def _run_ingest(document_id: str, contents: bytes) -> None:
    try:
        ingest_document(document_id, contents=contents)
    except Exception:
        pass


def _run_ingest_url(document_id: str, url: str) -> None:
    try:
        ingest_url(document_id, url=url)
    except Exception:
        pass


@router.post("/upload", response_model=DocumentIngestResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentIngestResponse:
    try:
        document, contents = await save_uploaded_document(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    background_tasks.add_task(_run_ingest, document.id, contents)
    return DocumentIngestResponse(
        document=document,
        message="File received, processing in background.",
    )


@router.post("/import-url", response_model=DocumentIngestResponse)
def import_url_document(
    request: ImportUrlRequest,
    background_tasks: BackgroundTasks,
) -> DocumentIngestResponse:
    url = str(request.url)
    document = create_url_document(url)
    background_tasks.add_task(_run_ingest_url, document.id, url)
    return DocumentIngestResponse(
        document=document,
        message="URL received, fetching and processing in background.",
    )


@router.get("", response_model=DocumentListResponse)
def read_documents() -> DocumentListResponse:
    return DocumentListResponse(documents=list_documents())


@router.get("/{document_id}", response_model=DocumentRead)
def read_document(document_id: str) -> DocumentRead:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}")
def remove_document(document_id: str) -> JSONResponse:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc
    return JSONResponse(content={"message": "Document deleted."})


@router.post("/{document_id}/ingest", response_model=DocumentIngestResponse)
def ingest_existing_document(
    document_id: str,
    background_tasks: BackgroundTasks,
) -> DocumentIngestResponse:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    background_tasks.add_task(_run_ingest, document.id)
    return DocumentIngestResponse(document=document, message="Re-ingestion started.")


@router.get("/{document_id}/knowledge-graph")
def get_knowledge_graph(document_id: str) -> dict:
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready (status: {document.status}).",
        )
    from app.services.document_store import get_chunks
    from app.services.knowledge_graph import extract_knowledge_graph
    chunks = get_chunks(document_id)
    return extract_knowledge_graph(document_id=document_id, chunks=chunks)
