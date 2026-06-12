from pydantic import BaseModel


class WeeklyReport(BaseModel):
    period_days: int = 7
    documents_added: int
    quizzes_taken: int
    questions_answered: int
    correct_rate: float
    average_mastery: float
    weakest_points: list[str]
    strongest_points: list[str]
    recommendations: str
    generated_at: str
