from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base

if TYPE_CHECKING:
    from backend.app.models.book import Book
    from backend.app.models.reader import Reader
    from backend.app.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BorrowRecord(Base):
    __tablename__ = "borrow_records"
    __table_args__ = (
        Index("ix_borrow_records_book_id", "book_id"),
        Index("ix_borrow_records_reader_id", "reader_id"),
        Index("ix_borrow_records_returned_at", "returned_at"),
        Index("ix_borrow_records_due_date", "due_date"),
        Index("ix_borrow_records_reader_returned", "reader_id", "returned_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), nullable=False
    )
    reader_id: Mapped[int] = mapped_column(
        ForeignKey("readers.id", ondelete="RESTRICT"), nullable=False
    )
    borrowed_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    book: Mapped["Book"] = relationship("Book", back_populates="borrow_records")
    reader: Mapped["Reader"] = relationship("Reader", back_populates="borrow_records")
    borrowed_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[borrowed_by], back_populates="borrowed_records"
    )
    returned_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[returned_by], back_populates="returned_records"
    )
