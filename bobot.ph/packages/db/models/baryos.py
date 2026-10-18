import uuid

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Baryo(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "baryos"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barangay: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_bot_skills: Mapped[list] = mapped_column(ARRAY(String), default=[], nullable=False)
    health_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    is_private: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)


class BaryoMember(Base, TimestampMixin):
    __tablename__ = "baryo_members"
    __table_args__ = (
        # Reverse lookup: which baryos does a user belong to?
        Index("ix_baryo_members_human_id", "human_id"),
    )

    baryo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    human_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", nullable=False
    )  # member, moderator, creator


class BaryoBot(Base, TimestampMixin):
    __tablename__ = "baryo_bots"
    __table_args__ = (
        # Reverse lookup: which baryos is a bot approved in?
        Index("ix_baryo_bots_bot_id", "bot_id"),
    )

    baryo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    approved_skills: Mapped[list] = mapped_column(ARRAY(String), default=[], nullable=False)
