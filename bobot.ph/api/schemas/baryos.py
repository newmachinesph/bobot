from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateBaryoRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Baryo name (alphanumeric + underscore only)",
    )
    display_name: str = Field(..., max_length=100)
    description: str
    region: Optional[str] = None
    barangay: Optional[str] = None
    allowed_bot_skills: list[str] = Field(default=[])
    rules: Optional[str] = None
    is_private: bool = False


class BaryoResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    region: Optional[str] = None
    barangay: Optional[str] = None
    rules: Optional[str] = None
    allowed_bot_skills: list[str]
    health_score: float
    is_private: bool
    member_count: int
    bot_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AddBotRequest(BaseModel):
    bot_id: str
    approved_skills: list[str] = Field(default=[])


class BaryoPulseResponse(BaseModel):
    baryo_name: str
    sentiment_trend: list
    top_posts: list
    bot_activity: list
    health_score_history: list
