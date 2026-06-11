from fastapi import APIRouter

from app.schemas.plan import StudyPlan
from app.schemas.profile import MasteryResponse, ReviewResponse
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
