import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Citation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "citations"

    url: Mapped[str] = mapped_column(Text, nullable=False)
    claimed_content: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), default="queued", nullable=False
    )  # queued, verified, unverified, not_found, unreachable, fabricated
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BotCorrection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bot_corrections"

    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    correction_source: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Debate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "debates"

    baryo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    bot_for_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bot_against_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    votes_for: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    votes_against: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Challenge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "challenges"

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    baryo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, resolved, expired
    agree_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disagree_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Follow(Base, TimestampMixin):
    __tablename__ = "follows"

    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    followee_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # human, bot
