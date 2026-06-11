from datetime import datetime

from pydantic import BaseModel


class MasteryItem(BaseModel):
    knowledge_point: str
    mastery_score: int
    correct_count: int
    mistake_count: int
    last_reviewed_at: datetime | None = None


class MasteryResponse(BaseModel):
    items: list[MasteryItem]
    total: int
    average_score: float


# ── review ────────────────────────────────────────────────────────────────────

class ReviewQuestion(BaseModel):
    id: str
    type: str
    question: str
    options: list[str] = []
    answer: str
    explanation: str


class ReviewItem(BaseModel):
    knowledge_point: str
    mastery_score: int
    next_review_at: datetime | None = None
    questions: list[ReviewQuestion] = []


class ReviewResponse(BaseModel):
    items: list[ReviewItem]
    total: int
