from fastapi import APIRouter

from app.schemas.plan import StudyPlan
from app.schemas.profile import (
    ErrorEntry,
    ErrorGroup,
    ErrorNotebookResponse,
    MasteryResponse,
    ReviewResponse,
)
from app.services.mastery_service import get_mastery, get_review_today

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/mastery", response_model=MasteryResponse)
def read_mastery() -> MasteryResponse:
    return get_mastery()


@router.get("/review/today", response_model=ReviewResponse)
def read_review_today() -> ReviewResponse:
    return get_review_today()


@router.post("/study-plan", response_model=StudyPlan)
def create_study_plan() -> StudyPlan:
    from app.services.planning_service import generate_study_plan
    return generate_study_plan()


@router.get("/error-notebook", response_model=ErrorNotebookResponse)
def read_error_notebook() -> ErrorNotebookResponse:
    from app.services.error_notebook import get_error_notebook
    raw_groups = get_error_notebook()
    groups = [
        ErrorGroup(
            knowledge_point=g.knowledge_point,
            mistake_count=g.mistake_count,
            mastery_score=g.mastery_score,
            entries=[
                ErrorEntry(
                    question_id=e.question_id,
                    quiz_id=e.quiz_id,
                    document_id=e.document_id,
                    knowledge_point=e.knowledge_point,
                    question_text=e.question_text,
                    options=e.options,
                    correct_answer=e.correct_answer,
                    explanation=e.explanation,
                    mistake_count=e.mistake_count,
                    last_wrong_at=e.last_wrong_at,
                )
                for e in g.entries
            ],
        )
        for g in raw_groups
    ]
    return ErrorNotebookResponse(
        groups=groups,
        total_mistakes=sum(g.mistake_count for g in groups),
    )
