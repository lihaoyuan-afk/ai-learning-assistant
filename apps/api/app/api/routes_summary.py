import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.graph import summary_graph
from app.api.deps import CurrentUserID
from app.schemas.summary import SummaryResponse
from app.services.document_store import get_chunks, get_document, save_summary

router = APIRouter(prefix="/documents/{document_id}/summary", tags=["summary"])


@router.post("", response_model=SummaryResponse)
def summarize_document(document_id: str, user_id: CurrentUserID) -> SummaryResponse:
    doc = get_document(document_id, user_id=user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready (status: {doc.status}).",
        )

    # Return cached summary if available
    if doc.summary:
        return SummaryResponse(document_id=document_id, summary=doc.summary)

    try:
        final = summary_graph.invoke(
            {"document_id": document_id, "task": "generate_summary"}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    summary = final.get("result", "")
    if final.get("error") and not summary:
        raise HTTPException(status_code=500, detail=final["error"])

    save_summary(document_id, summary)
    return SummaryResponse(document_id=document_id, summary=summary)


@router.post("/stream")
def stream_summary_document(document_id: str, user_id: CurrentUserID) -> StreamingResponse:
    doc = get_document(document_id, user_id=user_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready (status: {doc.status}).",
        )

    # Stream cached summary quickly without calling LLM again
    if doc.summary:
        cached_text = doc.summary

        def _stream_cached():
            chunk_size = 30
            for i in range(0, len(cached_text), chunk_size):
                token = cached_text[i : i + chunk_size]
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            yield 'data: {"type":"cached"}\n\n'
            yield 'data: {"type":"done"}\n\n'

        return StreamingResponse(
            _stream_cached(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    chunks = get_chunks(document_id)

    def _events():
        from app.services.summary_generator import stream_summary_text

        accumulated: list[str] = []
        try:
            for token in stream_summary_text(doc, chunks):
                accumulated.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"
        else:
            full_summary = "".join(accumulated)
            if full_summary:
                save_summary(document_id, full_summary)
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
