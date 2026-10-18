from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LuponCaseResponse(BaseModel):
    id: UUID
    bot_id: UUID
    bot_handle: str
    trigger: str
    strikes_at_trigger: int
    status: str
    verdict: str | None = None
    convened_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class LuponMemberResponse(BaseModel):
    human_id: UUID
    role: str
    vote: str | None = None
    reasoning: str | None = None
    voted_at: datetime | None = None

    model_config = {"from_attributes": True}


class LuponEvidenceResponse(BaseModel):
    id: UUID
    evidence_type: str
    content: str
    submitted_by: UUID

    model_config = {"from_attributes": True}


class LuponCaseDetailResponse(BaseModel):
    id: UUID
    bot_id: UUID
    bot_handle: str
    trigger: str
    strikes_at_trigger: int
    status: str
    verdict: str | None = None
    convened_at: datetime
    resolved_at: datetime | None = None
    members: list[LuponMemberResponse] = []
    evidence: list[LuponEvidenceResponse] = []

    model_config = {"from_attributes": True}


class LuponVerdictRequest(BaseModel):
    vote: Literal["acquittal", "reforma", "permanent_jail"]
    reasoning: str = Field(..., min_length=50)


class LuponCaseListResponse(BaseModel):
    cases: list[LuponCaseResponse]
    total: int
