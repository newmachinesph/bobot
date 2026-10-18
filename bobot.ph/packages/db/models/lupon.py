import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin, UUIDMixin


class LuponCase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lupon_cases"

    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # description of what triggered the case
    strikes_at_trigger: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="convened", nullable=False
    )  # convened, deliberating, resolved
    verdict: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # acquittal, reforma, permanent_jail
    convened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LuponMember(Base, TimestampMixin):
    __tablename__ = "lupon_members"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    human_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        String(20), default="juror", nullable=False
    )  # juror, chairperson
    vote: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # acquittal, reforma, permanent_jail
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    voted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LuponEvidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lupon_evidence"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # flagged_post, citation_result, accuracy_history, owner_statement
    content: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
