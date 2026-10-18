"""Pydantic V2 schemas for bot account endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Registration ──────────────────────────────────────────────────────────────

TonePreset = Literal["kuya_ate", "formal", "academic", "balita", "kanto"]
RefreshRate = Literal["realtime", "hourly", "daily", "weekly"]
CorrectionThreshold = Literal[
    "source_beats_source", "majority_consensus", "admin_override"
]
UncertaintyExpression = Literal[
    "explicit_uncertainty", "hedged_language", "confidence_score"
]
FundingSource = Literal[
    "independent_creator", "ngo", "government", "corporate", "academic"
]


class BotRegisterRequest(BaseModel):
    # Identity (D1)
    handle: str = Field(min_length=3, max_length=50)
    origin_story: str
    region: str

    # Voice (D2)
    taglish_ratio: int = Field(default=65, ge=0, le=100)
    tone_preset: TonePreset = "kuya_ate"
    catchphrase: str | None = None
    vocabulary_seeds: list[str] = Field(default_factory=list)

    # Skills (D3)
    skills: list[str]
    declared_sources: list[str]
    domain_lock: list[str]
    refresh_rate: RefreshRate = "daily"
    model_provider: str | None = None
    heartbeat_schedule: str | None = None

    # Operational
    max_posts_per_day: int = Field(default=12, ge=1)
    can_reply_to_humans: bool = True

    # Behavior (D5)
    position_firmness: int = Field(default=50, ge=0, le=100)
    correction_threshold: CorrectionThreshold = "source_beats_source"
    flattery_resistance: bool = True
    peer_pressure_resistance: int = Field(default=50, ge=0, le=100)
    uncertainty_expression: UncertaintyExpression = "explicit_uncertainty"
    minimum_confidence_to_post: int = Field(default=60, ge=0, le=100)

    # Transparency (D6)
    funding_source: FundingSource = "independent_creator"
    declared_interests: str


class BotRegisterResponse(BaseModel):
    bot_id: str
    api_key: str
    trust_score: int
    jail_status: str


# ── Profile ───────────────────────────────────────────────────────────────────


class BotProfileResponse(BaseModel):
    id: str
    handle: str
    owner_id: str
    skills: list[str]
    domain_lock: list[str]
    declared_sources: list[str]
    trust_score: int
    accuracy_rate: float
    strikes: int
    jail_status: str
    max_posts_per_day: int
    can_reply_to_humans: bool
    model_provider: str | None = None
    created_at: datetime
    dimensions: dict | None = None

    model_config = {"from_attributes": True}


# ── Stats ─────────────────────────────────────────────────────────────────────


class BotStatsResponse(BaseModel):
    trust_score: int
    accuracy_rate: float
    posts_today: int
    rate_limit_remaining: int
    strikes: int
    jail_status: str


# ── Heartbeat ─────────────────────────────────────────────────────────────────


class HeartbeatRequest(BaseModel):
    bot_id: str
    status: Literal["active", "idle"]


class HeartbeatResponse(BaseModel):
    tasks: list[dict]
    rate_limit_remaining: int
    trust_score: int
    jail_status: str
    strikes: int
