import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractionJob(Base):
    """SQLAlchemy model representing an asynchronous extraction job."""
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.PENDING.value, index=True, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    contract = relationship("Contract", lazy="selectin")
