from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class VerifyCitationRequest(BaseModel):
    url: str = Field(..., description="URL of the source to verify")
    claimed_content: str = Field(
        ..., min_length=10, description="The content claimed to exist at the URL"
    )


class VerifyCitationResponse(BaseModel):
    job_id: str
    status: str = "queued"
    estimated_seconds: int = 8


class CitationStatusResponse(BaseModel):
    job_id: str
    status: str
    confidence: float | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}
