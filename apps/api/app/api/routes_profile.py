from fastapi import APIRouter

from app.schemas.profile import MasteryResponse, ReviewResponse
from app.services.mastery_service import get_mastery, get_review_today

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/mastery", response_model=MasteryResponse)
def read_mastery() -> MasteryResponse:
    return get_mastery()


@router.get("/review/today", response_model=ReviewResponse)
def read_review_today() -> ReviewResponse:
    return get_review_today()
