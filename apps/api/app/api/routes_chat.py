import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.document import SourceChunk
from app.services.document_store import get_document
from app.services import retrieval as _retrieval
from app.services import llm as _llm

router = APIRouter(prefix="/documents/{document_id}/chat", tags=["chat"])


class SocraticRequest(BaseModel):
    user_answer: str | None = None
    history: list[dict] = []
    topic: str | None = None


@router.post("", response_model=ChatResponse)
def chat_with_document(document_id: str, request: ChatRequest) -> ChatResponse:
    doc = get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready for querying (status: {doc.status}).",
        )

    chunks = _retrieval.retrieve_context(document_id, request.question)
    try:
        answer = _llm.answer_question(request.question, chunks, history=request.history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc
    return ChatResponse(answer=answer, sources=chunks)


@router.post("/stream")
def stream_chat_with_document(document_id: str, request: ChatRequest) -> StreamingResponse:
    doc = get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready for querying (status: {doc.status}).",
        )

    chunks: list[SourceChunk] = _retrieval.retrieve_context(document_id, request.question)

    def _events():
        sources_payload = [c.model_dump() for c in chunks]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload}, ensure_ascii=False)}\n\n"
        try:
            for token in _llm.stream_answer_question(request.question, chunks, history=request.history):
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/socratic/stream")
def socratic_stream(document_id: str, request: SocraticRequest) -> StreamingResponse:
    doc = get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready (status: {doc.status}).",
        )

    query = request.topic or request.user_answer or "主要概念"
    chunks = _retrieval.retrieve_context(document_id, query, limit=6)

    def _events():
        try:
            for token in _llm.stream_socratic(
                chunks=chunks,
                history=request.history,
                user_answer=request.user_answer,
                topic=request.topic,
            ):
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
