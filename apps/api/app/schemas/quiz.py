from pydantic import BaseModel, Field


class QuizRequest(BaseModel):
    num_questions: int = Field(default=6, ge=1, le=12)


class QuizQuestion(BaseModel):
    id: str
    type: str
    question: str
    options: list[str] = []
    answer: str
    explanation: str
    knowledge_point: str | None = None


class QuizResponse(BaseModel):
    id: str
    document_id: str
    title: str
    difficulty: str
    questions: list[QuizQuestion]


# ── attempt (answer submission & grading) ─────────────────────────────────────

class QuizAttemptRequest(BaseModel):
    answers: dict[str, str]  # question_id -> user_answer


class QuestionResult(BaseModel):
    question_id: str
    is_correct: bool
    requires_review: bool = False   # True for short_answer (can't auto-grade)
    user_answer: str
    correct_answer: str
    explanation: str


class QuizAttemptResponse(BaseModel):
    attempt_id: str
    quiz_id: str
    score: int       # number of definitively correct answers
    total: int       # total questions
    results: list[QuestionResult]
