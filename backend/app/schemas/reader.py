from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import SchemaBase


_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ReaderCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254, pattern=_EMAIL_RE)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "phone", "email", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def require_contact(self) -> "ReaderCreate":
        if not self.phone and not self.email:
            raise ValueError("phone 或 email 至少填写一项")
        return self


class ReaderUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254, pattern=_EMAIL_RE)
    status: Literal["active", "disabled"] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "phone", "email", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def require_update(self) -> "ReaderUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个更新字段")
        if "phone" in self.model_fields_set and "email" in self.model_fields_set:
            if not self.phone and not self.email:
                raise ValueError("phone 或 email 至少填写一项")
        return self


class ReaderOut(SchemaBase):
    id: int
    name: str
    phone: str | None
    email: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ReaderBriefOut(SchemaBase):
    id: int
    name: str
    phone: str | None
    email: str | None
