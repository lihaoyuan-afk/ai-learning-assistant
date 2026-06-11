from pydantic import BaseModel, Field

from app.schemas.document import SourceChunk


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]

