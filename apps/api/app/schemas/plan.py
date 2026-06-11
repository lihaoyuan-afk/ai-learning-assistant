from datetime import datetime

from pydantic import BaseModel


class StudyPlanItem(BaseModel):
    document_id: str
    document_title: str
    reason: str
    priority: int  # 1 = highest priority


class StudyPlan(BaseModel):
    items: list[StudyPlanItem]
    generated_at: str
