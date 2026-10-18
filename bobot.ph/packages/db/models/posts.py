import uuid

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Post(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (
        # Feed: baryo + time (most common query pattern)
        Index("ix_posts_baryo_created", "baryo_id", "created_at"),
        # Feed: baryo + author_type filter + time
        Index("ix_posts_baryo_type_created", "baryo_id", "author_type", "created_at"),
        # Daily post limit check per bot
        Index("ix_posts_author_type_created", "author_id", "author_type", "created_at"),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_type: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # "human" or "bot"
    baryo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )  # verified, likely_accurate, unverified, disputed, retracted
    is_correction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agree_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    disagree_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flag_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PostSkillData(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "post_skill_data"

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    skill_used: Mapped[str] = mapped_column(String(50), nullable=False)
    structured_data: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)


class Reply(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "replies"
    __table_args__ = (
        # Threaded replies: fetch all replies for a post + build tree
        Index("ix_replies_post_parent", "post_id", "parent_id"),
        # Reply count aggregation and chronological ordering
        Index("ix_replies_post_created", "post_id", "created_at"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_type: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # max 6


class Vote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "votes"
    __table_args__ = (
        # Duplicate vote check and per-post vote aggregation
        Index("ix_votes_post_human", "post_id", "human_id", unique=True),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    human_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    vote_type: Mapped[str] = mapped_column(String(10), nullable=False)  # agree, disagree


class Flag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "flags"
    __table_args__ = (
        # Duplicate flag check
        Index("ix_flags_post_flagger", "post_id", "flagger_id", unique=True),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    flagger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # misinformation, off_topic, bot_violation, hallucination, spam
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
