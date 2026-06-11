from fastapi import APIRouter, HTTPException

from app.agents.graph import quiz_graph
from app.schemas.quiz import (
    QuizAttemptRequest, QuizAttemptResponse, QuizListResponse,
    QuizRequest, QuizResponse,
)
from app.services.document_store import (
    get_document,
    get_quiz,
    list_quizzes,
    save_quiz,
    score_and_save_attempt,
)

router = APIRouter(prefix="/documents/{document_id}/quiz", tags=["quiz"])


@router.post("", response_model=QuizResponse)
def create_quiz(document_id: str, request: QuizRequest) -> QuizResponse:
    doc = get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Document is not ready (status: {doc.status}).",
        )

    try:
        final = quiz_graph.invoke(
            {
                "document_id": document_id,
                "task": "generate_quiz",
                "num_questions": request.num_questions,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    quiz: QuizResponse = final["quiz_result"]

    if final.get("error") and not quiz.questions:
        raise HTTPException(status_code=500, detail=final["error"])

    save_quiz(document_id, quiz)
    return quiz


@router.get("", response_model=QuizListResponse)
def list_document_quizzes(document_id: str) -> QuizListResponse:
    if get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return QuizListResponse(quizzes=list_quizzes(document_id))


@router.get("/{quiz_id}", response_model=QuizResponse)
def read_quiz(document_id: str, quiz_id: str) -> QuizResponse:
    quiz = get_quiz(document_id=document_id, quiz_id=quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResponse)
def submit_attempt(
    document_id: str, quiz_id: str, request: QuizAttemptRequest
) -> QuizAttemptResponse:
    if get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return score_and_save_attempt(document_id, quiz_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
