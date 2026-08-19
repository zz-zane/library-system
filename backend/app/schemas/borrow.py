from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator

from backend.app.schemas.book import BookBriefOut
from backend.app.schemas.common import SchemaBase
from backend.app.schemas.reader import ReaderBriefOut
from backend.app.schemas.user import UserBriefOut


class BorrowCreate(SchemaBase):
    book_id: int = Field(gt=0)
    reader_id: int = Field(gt=0)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, value):
        return value.strip() if isinstance(value, str) else value


class BorrowOut(SchemaBase):
    id: int
    book: BookBriefOut
    reader: ReaderBriefOut
    borrowed_by: UserBriefOut
    borrowed_at: datetime
    due_date: date
    returned_at: datetime | None
    returned_by: UserBriefOut | None
    status: Literal["borrowed", "overdue", "returned"]
    notes: str | None
