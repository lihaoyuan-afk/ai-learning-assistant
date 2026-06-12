import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserID
from app.services import llm as _llm
from app.services import retrieval as _retrieval

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[dict] = Field(default_factory=list)


@router.post("/stream")
def stream_global_search(request: SearchRequest, user_id: CurrentUserID) -> StreamingResponse:
    chunks = _retrieval.retrieve_context_global(request.question, user_id=user_id)

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
