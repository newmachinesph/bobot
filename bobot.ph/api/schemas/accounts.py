"""Pydantic V2 schemas for human account endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ── Registration ──────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    region: str
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    account_id: str
    api_key: str
    tier: int


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Profile ───────────────────────────────────────────────────────────────────


class ProfileResponse(BaseModel):
    id: str
    username: str
    tier: int
    region: str
    bio: str | None = None
    karma: int
    loob_dimensions: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    region: str | None = None
    bio: str | None = None


# ── KYC ───────────────────────────────────────────────────────────────────────

KYCCategory = Literal[
    "journalist",
    "government_official",
    "ngo",
    "academic",
    "brand",
    "international",
]


class KYCApplyRequest(BaseModel):
    category: KYCCategory
    organization: str
    bias_declaration: str
    document_upload_token: str | None = None


class KYCStatusResponse(BaseModel):
    status: str
    category: str
    reviewer_note: str | None = None
    submitted_at: datetime
    reviewed_at: str | None = None

    model_config = {"from_attributes": True}


# ── Loob ──────────────────────────────────────────────────────────────────────


class LoobResponse(BaseModel):
    katapatan: float
    katumpakan: float
    kagalingan: float
    kapakumbabaan: float
    kalakarang_sibiko: float

    model_config = {"from_attributes": True}
