import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

import app.db.session as _db
from app.models.learning_memory import LearningMemory
from app.schemas.profile import (
    MasteryItem,
    MasteryResponse,
    ReviewItem,
    ReviewQuestion,
    ReviewResponse,
)
from app.schemas.quiz import QuestionResult, QuizQuestion

_CORRECT_DELTA = 8
_WRONG_DELTA = 15
_INITIAL_SCORE = 50

_REVIEW_DAYS_WEAK = 2    # mastery < 40
_REVIEW_DAYS_MID = 5     # 40 ≤ mastery < 70
_REVIEW_DAYS_STRONG = 14  # mastery ≥ 70


def _schedule_next_review(score: int, from_dt: datetime) -> datetime:
    if score < 40:
        return from_dt + timedelta(days=_REVIEW_DAYS_WEAK)
    if score < 70:
        return from_dt + timedelta(days=_REVIEW_DAYS_MID)
    return from_dt + timedelta(days=_REVIEW_DAYS_STRONG)


def update_mastery_from_attempt(
    results: list[QuestionResult],
    questions: list[QuizQuestion],
    user_id: str | None = None,
) -> None:
    q_map = {q.id: q for q in questions}
    now = _utcnow()

    for result in results:
        if result.requires_review:
            continue
        q = q_map.get(result.question_id)
        if q is None or not q.knowledge_point:
            continue

        kp = q.knowledge_point
        with _db.db_session() as db:
            query = db.query(LearningMemory).filter(LearningMemory.knowledge_point == kp)
            if user_id is not None:
                query = query.filter(LearningMemory.user_id == user_id)
            mem = query.first()
            if mem is None:
                mem = LearningMemory(
                    id=uuid4().hex,
                    knowledge_point=kp,
                    mastery_score=_INITIAL_SCORE,
                    correct_count=0,
                    mistake_count=0,
                    user_id=user_id,
                )
                db.add(mem)

            mem.last_reviewed_at = now
            if result.is_correct:
                mem.mastery_score = min(100, mem.mastery_score + _CORRECT_DELTA)
                mem.correct_count += 1
            else:
                mem.mastery_score = max(0, mem.mastery_score - _WRONG_DELTA)
                mem.mistake_count += 1

            mem.next_review_at = _schedule_next_review(mem.mastery_score, now)


def get_mastery(user_id: str | None = None) -> MasteryResponse:
    with _db.db_session() as db:
        q = db.query(LearningMemory)
        if user_id is not None:
            q = q.filter(LearningMemory.user_id == user_id)
        rows = q.order_by(LearningMemory.mastery_score).all()
        items = [
            MasteryItem(
                knowledge_point=r.knowledge_point,
                mastery_score=r.mastery_score,
                correct_count=r.correct_count,
                mistake_count=r.mistake_count,
                last_reviewed_at=r.last_reviewed_at,
            )
            for r in rows
        ]

    total = len(items)
    avg = round(sum(i.mastery_score for i in items) / total, 1) if total > 0 else 0.0
    return MasteryResponse(items=items, total=total, average_score=avg)


def schedule_review_soon(knowledge_point: str, days: int = 3, user_id: str | None = None) -> None:
    """Schedule a knowledge point for review `days` from now."""
    now = _utcnow()
    target = now + timedelta(days=days)
    with _db.db_session() as db:
        query = db.query(LearningMemory).filter(LearningMemory.knowledge_point == knowledge_point)
        if user_id is not None:
            query = query.filter(LearningMemory.user_id == user_id)
        mem = query.first()
        if mem is None:
            mem = LearningMemory(
                id=uuid4().hex,
                knowledge_point=knowledge_point,
                mastery_score=_INITIAL_SCORE,
                correct_count=0,
                mistake_count=0,
                user_id=user_id,
            )
            db.add(mem)
        mem.next_review_at = target


def get_review_today(user_id: str | None = None) -> ReviewResponse:
    from app.models.quiz import QuizQuestion as QuizQuestionModel  # avoid circular import

    now = _utcnow()
    with _db.db_session() as db:
        q = (
            db.query(LearningMemory)
            .filter(LearningMemory.next_review_at.isnot(None))
            .filter(LearningMemory.next_review_at <= now)
        )
        if user_id is not None:
            q = q.filter(LearningMemory.user_id == user_id)
        due = q.order_by(LearningMemory.mastery_score).all()
        items: list[ReviewItem] = []
        for mem in due:
            qs = (
                db.query(QuizQuestionModel)
                .filter(QuizQuestionModel.knowledge_point == mem.knowledge_point)
                .filter(QuizQuestionModel.type == "multiple_choice")
                .limit(3)
                .all()
            )
            items.append(
                ReviewItem(
                    knowledge_point=mem.knowledge_point,
                    mastery_score=mem.mastery_score,
                    next_review_at=mem.next_review_at,
                    questions=[
                        ReviewQuestion(
                            id=q.id,
                            type=q.type,
                            question=q.question,
                            options=json.loads(q.options or "[]"),
                            answer=q.answer,
                            explanation=q.explanation or "",
                        )
                        for q in qs
                    ],
                )
            )
    return ReviewResponse(items=items, total=len(items))
