from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Contract(Base):
    """SQLAlchemy model representing a successfully processed and validated contract."""
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    lessor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    lessee: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    commencement_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_rent: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    termination_notice_period: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
