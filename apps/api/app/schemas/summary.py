from pydantic import BaseModel


class SummaryResponse(BaseModel):
    document_id: str
    summary: str

