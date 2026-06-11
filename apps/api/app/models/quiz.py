from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    difficulty: Mapped[str] = mapped_column(String, default="mixed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"), index=True)
    type: Mapped[str] = mapped_column(String)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_point: Mapped[str | None] = mapped_column(String, nullable=True)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    answers: Mapped[str] = mapped_column(Text, default="{}")  # JSON dict
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
