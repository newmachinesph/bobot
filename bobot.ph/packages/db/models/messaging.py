import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("participant_a_id", "participant_b_id", name="uq_conversation_pair"),
    )

    participant_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    participant_a_type: Mapped[str] = mapped_column(String(10), nullable=False)  # human|bot
    participant_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    participant_b_type: Mapped[str] = mapped_column(String(10), nullable=False)  # human|bot
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|approved|rejected|blocked
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base, UUIDMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)  # human|bot
    content: Mapped[str] = mapped_column(Text, nullable=False)
    needs_human_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
