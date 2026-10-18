import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, UUIDMixin


class PulseSnapshot(Base, UUIDMixin):
    __tablename__ = "pulse_snapshots"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    price_index: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    sentiment: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    misinfo_heatmap: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)


class LoobScore(Base):
    __tablename__ = "loob_scores"

    human_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    katapatan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    katumpakan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    kagalingan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    kapakumbabaan: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    kalakarang_sibiko: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
