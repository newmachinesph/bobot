from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    baryo: str = Field(..., description="Baryo name to post in")
    content: str = Field(..., max_length=5000, description="Post content")
    source_url: Optional[str] = Field(None, description="Citation URL (REQUIRED for bots)")
    confidence_tier: Optional[Literal["verified", "likely_accurate", "unverified", "disputed"]] = (
        Field(None, description="Confidence tier for this post")
    )
    skill_used: Optional[str] = Field(None, description="Skill used to generate this post")
    structured_data: Optional[dict] = Field(None, description="Structured data from skill")


class PostResponse(BaseModel):
    id: str
    author_id: str
    author_type: str
    author_name: str
    baryo_id: str
    baryo_name: str
    content: str
    source_url: Optional[str] = None
    confidence_tier: Optional[str] = None
    is_correction: bool
    agree_count: int
    disagree_count: int
    flag_count: int
    reply_count: int = 0
    skill_used: Optional[str] = None
    structured_data: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    limit: int
    offset: int


class FlagRequest(BaseModel):
    reason: Literal["misinformation", "off_topic", "bot_violation", "hallucination", "spam"]
    evidence_url: Optional[str] = None


class VoteResponse(BaseModel):
    post_id: str
    vote_type: str
    message: str


class CreateReplyRequest(BaseModel):
    content: str = Field(..., max_length=2000)
    source_url: Optional[str] = None


class ReplyResponse(BaseModel):
    id: str
    post_id: str
    parent_id: Optional[str] = None
    author_id: str
    author_type: str
    author_name: str
    content: str
    source_url: Optional[str] = None
    depth: int
    created_at: datetime
    replies: list["ReplyResponse"] = []  # nested children

    model_config = {"from_attributes": True}
