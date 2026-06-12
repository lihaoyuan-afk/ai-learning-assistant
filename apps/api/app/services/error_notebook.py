"""Error notebook: aggregate wrong quiz answers, grouped by knowledge point."""

import json
from dataclasses import dataclass, field
from datetime import datetime

import app.db.session as _db
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion


@dataclass
class ErrorEntry:
    question_id: str
    quiz_id: str
    document_id: str
    knowledge_point: str
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: str
    mistake_count: int
    last_wrong_at: datetime | None


@dataclass
class ErrorGroup:
    knowledge_point: str
    mistake_count: int
    mastery_score: int | None
    entries: list[ErrorEntry] = field(default_factory=list)


def get_error_notebook() -> list[ErrorGroup]:
    """Return all wrong MC answers grouped by knowledge_point, sorted by mistake count."""
    with _db.db_session() as db:
        attempts = db.query(QuizAttempt).order_by(QuizAttempt.created_at).all()
        if not attempts:
            return []

        # Collect all referenced question IDs
        all_q_ids: set[str] = set()
        attempt_data: list[tuple[dict[str, str], datetime]] = []
        for attempt in attempts:
            try:
                answers: dict[str, str] = json.loads(attempt.answers or "{}")
            except (json.JSONDecodeError, TypeError):
                answers = {}
            attempt_data.append((answers, attempt.created_at))
            all_q_ids.update(answers.keys())

        if not all_q_ids:
            return []

        questions = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.id.in_(list(all_q_ids)))
            .all()
        )
        # Snapshot question data while still in session
        q_snap: dict[str, dict] = {
            q.id: {
                "id": q.id,
                "quiz_id": q.quiz_id,
                "type": q.type,
                "question": q.question,
                "options": json.loads(q.options or "[]"),
                "answer": q.answer or "",
                "explanation": q.explanation or "",
                "knowledge_point": q.knowledge_point or "未分类",
            }
            for q in questions
        }

        # quiz_id → document_id
        quiz_ids = {snap["quiz_id"] for snap in q_snap.values()}
        quizzes = db.query(Quiz).filter(Quiz.id.in_(list(quiz_ids))).all()
        quiz_doc_map = {qz.id: qz.document_id for qz in quizzes}

    # Fetch mastery scores (separate session is fine — only reading scalar data)
    from app.models.learning_memory import LearningMemory
    mastery_map: dict[str, int] = {}
    with _db.db_session() as db:
        all_kps = {snap["knowledge_point"] for snap in q_snap.values()}
        memories = (
            db.query(LearningMemory)
            .filter(LearningMemory.knowledge_point.in_(list(all_kps)))
            .all()
        )
        mastery_map = {m.knowledge_point: m.mastery_score for m in memories}

    # Count wrong answers per question
    wrong: dict[str, dict] = {}
    for answers, created_at in attempt_data:
        for qid, user_ans in answers.items():
            snap = q_snap.get(qid)
            if snap is None or snap["type"] != "multiple_choice":
                continue
            is_correct = user_ans[:1].upper() == snap["answer"][:1].upper()
            if not is_correct:
                if qid not in wrong:
                    wrong[qid] = {"count": 0, "last_at": None}
                wrong[qid]["count"] += 1
                wrong[qid]["last_at"] = created_at

    if not wrong:
        return []

    # Build groups
    groups: dict[str, ErrorGroup] = {}
    for qid, info in sorted(wrong.items(), key=lambda x: -x[1]["count"]):
        snap = q_snap[qid]
        kp = snap["knowledge_point"]
        if kp not in groups:
            groups[kp] = ErrorGroup(
                knowledge_point=kp,
                mistake_count=0,
                mastery_score=mastery_map.get(kp),
            )
        groups[kp].entries.append(
            ErrorEntry(
                question_id=qid,
                quiz_id=snap["quiz_id"],
                document_id=quiz_doc_map.get(snap["quiz_id"], ""),
                knowledge_point=kp,
                question_text=snap["question"],
                options=snap["options"],
                correct_answer=snap["answer"],
                explanation=snap["explanation"],
                mistake_count=info["count"],
                last_wrong_at=info["last_at"],
            )
        )
        groups[kp].mistake_count += info["count"]

    return sorted(groups.values(), key=lambda g: -g.mistake_count)
