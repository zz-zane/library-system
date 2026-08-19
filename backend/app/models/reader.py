from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base

if TYPE_CHECKING:
    from backend.app.models.borrow import BorrowRecord


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Reader(Base):
    __tablename__ = "readers"
    __table_args__ = (
        Index("ix_readers_name", "name"),
        Index("ix_readers_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    borrow_records: Mapped[list["BorrowRecord"]] = relationship(
        "BorrowRecord", back_populates="reader", passive_deletes=True
    )
