from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.document import DocumentIngestResponse, DocumentListResponse, DocumentRead
from app.services.document_store import delete_document, get_document, list_documents
from app.workers.ingest_document import ingest_document, save_uploaded_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _run_ingest(document_id: str, contents: bytes) -> None:
    """Background wrapper — errors are swallowed because ingest_document already
    sets document status to 'failed' before re-raising."""
    try:
        ingest_document(document_id, contents=contents)
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
