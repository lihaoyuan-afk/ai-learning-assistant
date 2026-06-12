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
        is_public=getattr(doc, "is_public", False) or False,
        forked_from=getattr(doc, "forked_from", None),
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

def create_document(
    title: str, file_type: str, file_path: str | None, user_id: str | None = None
) -> DocumentRead:
    with _db.db_session() as db:
        doc = Document(
            id=uuid4().hex,
            title=title,
            file_type=file_type,
            file_path=file_path,
            status=DocumentStatus.uploaded.value,
            user_id=user_id,
        )
        db.add(doc)
        db.flush()
        return _doc_to_read(doc)


def list_documents(user_id: str | None = None) -> list[DocumentRead]:
    with _db.db_session() as db:
        q = db.query(Document)
        if user_id is not None:
            q = q.filter(Document.user_id == user_id)
        rows = q.order_by(Document.created_at.desc()).all()
        return [_doc_to_read(r) for r in rows]


def get_document(document_id: str, user_id: str | None = None) -> DocumentRead | None:
    with _db.db_session() as db:
        q = db.query(Document).filter(Document.id == document_id)
        if user_id is not None:
            q = q.filter(Document.user_id == user_id)
        doc = q.first()
        return _doc_to_read(doc) if doc else None


def update_document_title(document_id: str, title: str) -> None:
    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.title = title


def update_document_status(document_id: str, status: DocumentStatus) -> DocumentRead:
    with _db.db_session() as db:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")
        doc.status = status.value
        db.flush()
        return _doc_to_read(doc)


def delete_document(document_id: str, user_id: str | None = None) -> None:
    """Delete document and all associated DB records, Qdrant vectors, and disk file."""
    from pathlib import Path

    from app.services.vector_store import vector_store

    with _db.db_session() as db:
        q = db.query(Document).filter(Document.id == document_id)
        if user_id is not None:
            q = q.filter(Document.user_id == user_id)
        doc = q.first()
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


# ── public library ───────────────────────────────────────────────────────────

def list_public_documents() -> list[DocumentRead]:
    """Return all documents marked as public, newest first."""
    with _db.db_session() as db:
        rows = (
            db.query(Document)
            .filter(Document.is_public.is_(True))
            .order_by(Document.created_at.desc())
            .all()
        )
        return [_doc_to_read(r) for r in rows]


def set_document_visibility(
    document_id: str, is_public: bool, user_id: str | None = None
) -> DocumentRead:
    with _db.db_session() as db:
        q = db.query(Document).filter(Document.id == document_id)
        if user_id is not None:
            q = q.filter(Document.user_id == user_id)
        doc = q.first()
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")
        doc.is_public = is_public
        db.flush()
        return _doc_to_read(doc)


def fork_document(document_id: str, user_id: str) -> DocumentRead:
    """Copy a public document (chunks + vectors) into the forking user's library."""
    new_id = uuid4().hex

    with _db.db_session() as db:
        source = (
            db.query(Document)
            .filter(Document.id == document_id, Document.is_public.is_(True))
            .first()
        )
        if source is None:
            raise ValueError("Public document not found")

        new_doc = Document(
            id=new_id,
            title=source.title + "（副本）",
            file_type=source.file_type,
            file_path=source.file_path,
            status=source.status,
            summary=source.summary,
            user_id=user_id,
            is_public=False,
            forked_from=document_id,
        )
        db.add(new_doc)
        db.flush()
        result = _doc_to_read(new_doc)

    # Copy chunks + re-upsert vectors when source is ready
    if result.status == "ready":
        source_chunks = get_chunks(document_id)
        if source_chunks:
            new_chunks = [
                SourceChunk(
                    id=uuid4().hex,
                    document_id=new_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    page_number=c.page_number,
                    section_title=c.section_title,
                )
                for c in source_chunks
            ]
            save_chunks(new_id, new_chunks)
            try:
                from app.services.vector_store import vector_store
                vector_store.upsert_chunks(new_chunks)
            except Exception:
                pass

    return result


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
    document_id: str, quiz_id: str, request: QuizAttemptRequest, user_id: str | None = None
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

    import app.services.mastery_service as _mastery  # lazy to avoid circular at load time
    _mastery.update_mastery_from_attempt(results, quiz.questions, user_id=user_id)

    return attempt


def list_quizzes(document_id: str) -> list:
    """Return summary list of all quizzes for a document (most recent first)."""
    from app.models.quiz import Quiz, QuizQuestion as QQModel
    from app.schemas.quiz import QuizSummary

    with _db.db_session() as db:
        quizzes = (
            db.query(Quiz)
            .filter(Quiz.document_id == document_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )
        result = []
        for q in quizzes:
            count = db.query(QQModel).filter(QQModel.quiz_id == q.id).count()
            result.append(QuizSummary(
                id=q.id,
                title=q.title,
                difficulty=q.difficulty,
                question_count=count,
                created_at=q.created_at.isoformat(),
            ))
        return result


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
