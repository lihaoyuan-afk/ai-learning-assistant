import json
from uuid import uuid4

import app.db.session as _db
from app.models.document import Chunk as ChunkModel
from app.models.document import Document
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion as QuizQuestionModel
from app.schemas.document import DocumentRead, DocumentStatus, SourceChunk
from app.schemas.quiz import (
    QuestionResult,
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizQuestion,
    QuizResponse,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _doc_to_read(doc: Document) -> DocumentRead:
    return DocumentRead(
        id=doc.id,
        title=doc.title,
        file_type=doc.file_type,
        status=DocumentStatus(doc.status),
        file_path=doc.file_path,
        summary=doc.summary,
        created_at=doc.created_at,
    )


def _row_to_question(q: QuizQuestionModel) -> QuizQuestion:
    return QuizQuestion(
        id=q.id,
        type=q.type,
        question=q.question,
        options=json.loads(q.options or "[]"),
        answer=q.answer,
        explanation=q.explanation or "",
        knowledge_point=q.knowledge_point,
    )


# ── documents ─────────────────────────────────────────────────────────────────

def create_document(title: str, file_type: str, file_path: str) -> DocumentRead:
    with _db.db_session() as db:
        doc = Document(
            id=uuid4().hex,
            title=title,
            file_type=file_type,
            file_path=file_path,
            status=DocumentStatus.uploaded.value,
        )
        db.add(doc)
        db.flush()
        return _doc_to_read(doc)


def list_documents() -> list[DocumentRead]:
    with _db.db_session() as db:
        rows = db.query(Document).order_by(Document.created_at.desc()).all()
        return [_doc_to_read(r) for r in rows]


def get_document(document_id: str) -> DocumentRead | None:
    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        return _doc_to_read(doc) if doc else None


def update_document_status(document_id: str, status: DocumentStatus) -> DocumentRead:
    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")
        doc.status = status.value
        db.flush()
        return _doc_to_read(doc)


def delete_document(document_id: str) -> None:
    """Delete document and all associated DB records, Qdrant vectors, and disk file."""
    from pathlib import Path

    from app.services.vector_store import vector_store

    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")
        file_path = doc.file_path

        # Cascade delete: quizzes, questions, chunks
        from app.models.quiz import Quiz, QuizQuestion as QuizQuestionModel, QuizAttempt
        quiz_ids = [q.id for q in db.query(Quiz.id).filter(Quiz.document_id == document_id)]
        if quiz_ids:
            db.query(QuizAttempt).filter(QuizAttempt.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
            db.query(QuizQuestionModel).filter(QuizQuestionModel.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
            db.query(Quiz).filter(Quiz.document_id == document_id).delete(synchronize_session=False)
        db.query(ChunkModel).filter(ChunkModel.document_id == document_id).delete(synchronize_session=False)
        db.delete(doc)

    # Delete vectors from Qdrant (best-effort)
    try:
        vector_store.delete_by_document_id(document_id)
    except Exception:
        pass

    # Delete file from disk (best-effort)
    if file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass


# ── chunks ────────────────────────────────────────────────────────────────────

def save_chunks(document_id: str, chunks: list[SourceChunk]) -> None:
    with _db.db_session() as db:
        db.query(ChunkModel).filter(ChunkModel.document_id == document_id).delete()
        for chunk in chunks:
            db.add(ChunkModel(
                id=chunk.id,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            ))


def get_chunks(document_id: str) -> list[SourceChunk]:
    with _db.db_session() as db:
        rows = (
            db.query(ChunkModel)
            .filter(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index)
            .all()
        )
        return [
            SourceChunk(
                id=r.id,
                document_id=r.document_id,
                chunk_index=r.chunk_index,
                content=r.content,
                page_number=r.page_number,
                section_title=r.section_title,
            )
            for r in rows
        ]


# ── summary ───────────────────────────────────────────────────────────────────

def save_summary(document_id: str, summary: str) -> None:
    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.summary = summary


# ── quizzes ───────────────────────────────────────────────────────────────────

def save_quiz(document_id: str, quiz: QuizResponse) -> None:
    with _db.db_session() as db:
        db.add(Quiz(
            id=quiz.id,
            document_id=document_id,
            title=quiz.title,
            difficulty=quiz.difficulty,
        ))
        for q in quiz.questions:
            db.add(QuizQuestionModel(
                id=q.id,
                quiz_id=quiz.id,
                type=q.type,
                question=q.question,
                options=json.dumps(q.options, ensure_ascii=False),
                answer=q.answer,
                explanation=q.explanation,
                knowledge_point=q.knowledge_point,
            ))


# ── quiz attempts ─────────────────────────────────────────────────────────────

def score_and_save_attempt(
    document_id: str, quiz_id: str, request: QuizAttemptRequest
) -> QuizAttemptResponse:
    quiz = get_quiz(document_id, quiz_id)
    if quiz is None:
        raise ValueError("Quiz not found")

    results: list[QuestionResult] = []
    correct_count = 0

    for q in quiz.questions:
        user_answer = request.answers.get(q.id, "").strip()
        is_mc = q.type == "multiple_choice"

        if is_mc:
            # Answers are letters like "A" — compare first char, case-insensitive
            is_correct = user_answer[:1].upper() == q.answer[:1].upper()
            requires_review = False
            correct_count += 1 if is_correct else 0
        else:
            # Short answer: can't auto-grade; show correct answer for self-check
            is_correct = False
            requires_review = True

        results.append(QuestionResult(
            question_id=q.id,
            is_correct=is_correct,
            requires_review=requires_review,
            user_answer=user_answer,
            correct_answer=q.answer,
            explanation=q.explanation,
        ))

    mc_total = sum(1 for q in quiz.questions if q.type == "multiple_choice")

    attempt = QuizAttemptResponse(
        attempt_id=uuid4().hex,
        quiz_id=quiz_id,
        score=correct_count,
        total=mc_total,
        results=results,
    )

    with _db.db_session() as db:
        db.add(QuizAttempt(
            id=attempt.attempt_id,
            quiz_id=quiz_id,
            score=attempt.score,
            total=attempt.total,
            answers=json.dumps(request.answers, ensure_ascii=False),
        ))

    # Update knowledge-point mastery scores based on this attempt
    import app.services.mastery_service as _mastery  # lazy to avoid circular at load time
    _mastery.update_mastery_from_attempt(results, quiz.questions)

    return attempt


def get_quiz(document_id: str, quiz_id: str) -> QuizResponse | None:
    with _db.db_session() as db:
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.document_id == document_id,
        ).first()
        if quiz is None:
            return None
        questions = (
            db.query(QuizQuestionModel)
            .filter(QuizQuestionModel.quiz_id == quiz_id)
            .all()
        )
        return QuizResponse(
            id=quiz.id,
            document_id=document_id,
            title=quiz.title,
            difficulty=quiz.difficulty,
            questions=[_row_to_question(q) for q in questions],
        )
