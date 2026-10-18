import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.db.base import Base, TimestampMixin, UUIDMixin


class Human(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "humans"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=Standard, 2=Established, 3=KYC
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    karma: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    loob_dimensions: Mapped[dict] = mapped_column(
        JSONB,
        default={
            "katapatan": 0,
            "katumpakan": 0,
            "kagalingan": 0,
            "kapakumbabaan": 0,
            "kalakarang_sibiko": 0,
        },
        nullable=False,
    )

    # Relationships
    kyc_applications = relationship("KYCApplication", back_populates="human")
    bots = relationship("Bot", back_populates="owner")


class KYCApplication(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "kyc_applications"

    human_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("humans.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # journalist, government_official, ngo, academic, brand, international
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    bias_declaration: Mapped[str] = mapped_column(Text, nullable=False)
    document_upload_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, approved, rejected, more_info_required
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    human = relationship("Human", back_populates="kyc_applications")
