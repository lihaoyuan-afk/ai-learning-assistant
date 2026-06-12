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


# ── error notebook ────────────────────────────────────────────────────────────

class ErrorEntry(BaseModel):
    question_id: str
    quiz_id: str
    document_id: str
    knowledge_point: str
    question_text: str
    options: list[str] = []
    correct_answer: str
    explanation: str
    mistake_count: int
    last_wrong_at: datetime | None = None


class ErrorGroup(BaseModel):
    knowledge_point: str
    mistake_count: int
    mastery_score: int | None = None
    entries: list[ErrorEntry] = []


class ErrorNotebookResponse(BaseModel):
    groups: list[ErrorGroup]
    total_mistakes: int
