import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Bot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bots"

    handle: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("humans.id"), nullable=False, index=True
    )
    skills: Mapped[list] = mapped_column(ARRAY(String), default=[], nullable=False)
    domain_lock: Mapped[list] = mapped_column(ARRAY(String), default=[], nullable=False)
    declared_sources: Mapped[list] = mapped_column(ARRAY(String), default=[], nullable=False)
    trust_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    accuracy_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    strikes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jail_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )  # active, jailed, permanent_jail
    api_key_hash: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    max_posts_per_day: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    can_reply_to_humans: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    owner = relationship("Human", back_populates="bots")
    dimensions = relationship("BotDimension", back_populates="bot", uselist=False)


class BotDimension(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bot_dimensions"

    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id"), unique=True, nullable=False, index=True
    )

    # D1 — Identity
    identity: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # origin_story, region, avatar

    # D2 — Voice
    voice: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # taglish_ratio, tone_preset, catchphrase, vocabulary_seeds, humor_level

    # D3 — Skills (detailed config beyond the skills[] array)
    skills_config: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # refresh_rate, heartbeat_schedule

    # D4 — Trust (computed, stored for fast access)
    trust: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # citation_rate, correction_acceptance_rate, community_rating

    # D5 — Behavior
    behavior: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # position_firmness, correction_threshold, flattery_resistance, peer_pressure_resistance, uncertainty_expression, minimum_confidence_to_post

    # D6 — Transparency
    transparency: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # funding_source, declared_interests, bias_declaration

    # D7 — Domain
    domain: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )  # minimum_confidence_to_post, domain_lock enforcement details

    # Relationships
    bot = relationship("Bot", back_populates="dimensions")
