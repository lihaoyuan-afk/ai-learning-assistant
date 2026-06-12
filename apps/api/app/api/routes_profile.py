from fastapi import APIRouter, Body, HTTPException

from app.api.deps import CurrentUserID
from app.schemas.plan import StudyPlan
from app.schemas.profile import (
    ErrorEntry,
    ErrorGroup,
    ErrorNotebookResponse,
    MasteryResponse,
    ReviewResponse,
)
from app.schemas.report import WeeklyReport
from app.services.mastery_service import get_mastery, get_review_today, schedule_review_soon

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/mastery", response_model=MasteryResponse)
def read_mastery(user_id: CurrentUserID) -> MasteryResponse:
    return get_mastery(user_id=user_id)


@router.get("/review/today", response_model=ReviewResponse)
def read_review_today(user_id: CurrentUserID) -> ReviewResponse:
    return get_review_today(user_id=user_id)


@router.post("/study-plan", response_model=StudyPlan)
def create_study_plan() -> StudyPlan:
    from app.services.planning_service import generate_study_plan
    return generate_study_plan()


@router.get("/error-notebook", response_model=ErrorNotebookResponse)
def read_error_notebook(user_id: CurrentUserID) -> ErrorNotebookResponse:
    from app.services.error_notebook import get_error_notebook
    raw_groups = get_error_notebook(user_id=user_id)
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


@router.post("/mastery/schedule-review")
def schedule_review(knowledge_point: str = Body(..., embed=True), user_id: CurrentUserID = None) -> dict:
    schedule_review_soon(knowledge_point, user_id=user_id)
    return {"message": "已安排", "knowledge_point": knowledge_point}


@router.get("/weekly-report", response_model=WeeklyReport)
def get_weekly_report(days: int = 7, user_id: CurrentUserID = None) -> WeeklyReport:
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days 必须在 1-90 之间")
    from app.services.report_service import generate_weekly_report
    return generate_weekly_report(period_days=days, user_id=user_id)
