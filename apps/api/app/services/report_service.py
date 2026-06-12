"""Generate a learning summary report from DB stats + LLM recommendations."""

from datetime import datetime, timedelta, timezone

import app.db.session as _db
from app.models.document import Document
from app.models.learning_memory import LearningMemory
from app.models.quiz import Quiz, QuizAttempt
from app.schemas.report import WeeklyReport


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_weekly_report(period_days: int = 7, user_id: str | None = None) -> WeeklyReport:
    now = _utcnow()
    since = now - timedelta(days=period_days)
    generated_at = now.isoformat()

    with _db.db_session() as db:
        doc_q = db.query(Document).filter(Document.created_at >= since)
        if user_id is not None:
            doc_q = doc_q.filter(Document.user_id == user_id)
        docs_added = doc_q.count()

        quiz_q = db.query(Quiz.id)
        if user_id is not None:
            doc_ids = [r.id for r in db.query(Document.id).filter(Document.user_id == user_id).all()]
            quiz_q = quiz_q.filter(Quiz.document_id.in_(doc_ids))
        quiz_q = quiz_q.filter(Quiz.created_at >= since)
        quiz_ids_recent = [r[0] for r in quiz_q.all()]
        quizzes_taken = len(quiz_ids_recent)

        attempt_q = db.query(QuizAttempt).filter(QuizAttempt.created_at >= since)
        if quiz_ids_recent:
            attempt_q = attempt_q.filter(QuizAttempt.quiz_id.in_(quiz_ids_recent))
        elif user_id is not None:
            attempt_q = attempt_q.filter(False)  # no quizzes → no attempts
        attempts = attempt_q.all()
        questions_answered = sum(a.total for a in attempts)
        correct_answers = sum(a.score for a in attempts)

        mastery_q = db.query(LearningMemory)
        if user_id is not None:
            mastery_q = mastery_q.filter(LearningMemory.user_id == user_id)
        mastery_rows = mastery_q.order_by(LearningMemory.mastery_score).all()
        mastery_data = [
            (r.knowledge_point, r.mastery_score) for r in mastery_rows
        ]

    correct_rate = round(correct_answers / questions_answered * 100, 1) if questions_answered else 0.0
    average_mastery = (
        round(sum(s for _, s in mastery_data) / len(mastery_data), 1)
        if mastery_data else 0.0
    )

    weakest = [kp for kp, _ in mastery_data[:5]]
    strongest = [kp for kp, _ in reversed(mastery_data[-5:])]

    recommendations = _generate_recommendations(
        period_days=period_days,
        docs_added=docs_added,
        quizzes_taken=quizzes_taken,
        questions_answered=questions_answered,
        correct_rate=correct_rate,
        average_mastery=average_mastery,
        weakest=weakest,
        strongest=strongest,
    )

    return WeeklyReport(
        period_days=period_days,
        documents_added=docs_added,
        quizzes_taken=quizzes_taken,
        questions_answered=questions_answered,
        correct_rate=correct_rate,
        average_mastery=average_mastery,
        weakest_points=weakest,
        strongest_points=strongest,
        recommendations=recommendations,
        generated_at=generated_at,
    )


def _generate_recommendations(
    *,
    period_days: int,
    docs_added: int,
    quizzes_taken: int,
    questions_answered: int,
    correct_rate: float,
    average_mastery: float,
    weakest: list[str],
    strongest: list[str],
) -> str:
    weak_str = "、".join(weakest[:3]) if weakest else "暂无"
    strong_str = "、".join(strongest[:3]) if strongest else "暂无"

    prompt = (
        f"你是一个学习助手，根据以下学习数据为用户写一段简短的学习建议（150字以内，直接给建议，不需要标题）。\n\n"
        f"过去{period_days}天数据：\n"
        f"- 新增资料：{docs_added} 份\n"
        f"- 完成测验：{quizzes_taken} 次，共答题 {questions_answered} 道，正确率 {correct_rate}%\n"
        f"- 平均掌握度：{average_mastery}%\n"
        f"- 最薄弱知识点：{weak_str}\n"
        f"- 掌握最好知识点：{strong_str}\n\n"
        "请给出2-3条具体可操作的学习建议。"
    )

    try:
        from app.services.llm import call_chat
        return call_chat([{"role": "user", "content": prompt}], max_tokens=300)
    except Exception:
        if weakest:
            return f"建议重点复习以下薄弱知识点：{weak_str}。保持每天练习的习惯，平均掌握度可以稳步提升。"
        return "继续上传学习资料，完成 Quiz 练习，掌握度将自动追踪并给出个性化建议。"
