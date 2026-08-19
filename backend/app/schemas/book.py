from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import SchemaBase


def normalize_isbn(value: str | None) -> str | None:
    if value is None:
        return None
    compact = value.replace("-", "").replace(" ", "").upper()
    if len(compact) == 10:
        if not (compact[:9].isdigit() and (compact[9].isdigit() or compact[9] == "X")):
            raise ValueError("ISBN-10 格式无效")
        total = sum((10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(compact))
        if total % 11:
            raise ValueError("ISBN-10 校验位无效")
    elif len(compact) == 13:
        if not compact.isdigit():
            raise ValueError("ISBN-13 格式无效")
        total = sum((1 if index % 2 == 0 else 3) * int(char) for index, char in enumerate(compact))
        if total % 10:
            raise ValueError("ISBN-13 校验位无效")
    else:
        raise ValueError("ISBN 必须为 ISBN-10 或 ISBN-13")
    return compact


class BookCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=200)
    publish_year: int | None = Field(default=None, ge=1000)
    category: str | None = Field(default=None, max_length=50)
    total_copies: int = Field(default=1, ge=1, le=999)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "author", "isbn", "publisher", "category", "description", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value):
        return normalize_isbn(value)

    @field_validator("publish_year")
    @classmethod
    def validate_year(cls, value):
        if value is not None and value > date.today().year:
            raise ValueError("出版年份不能晚于当前年份")
        return value


class BookUpdate(SchemaBase):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=100)
    isbn: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=200)
    publish_year: int | None = Field(default=None, ge=1000)
    category: str | None = Field(default=None, max_length=50)
    total_copies: int | None = Field(default=None, ge=1, le=999)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "author", "isbn", "publisher", "category", "description", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value):
        return normalize_isbn(value)

    @field_validator("publish_year")
    @classmethod
    def validate_year(cls, value):
        if value is not None and value > date.today().year:
            raise ValueError("出版年份不能晚于当前年份")
        return value

    @model_validator(mode="after")
    def require_update(self) -> "BookUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个更新字段")
        return self


class BookOut(SchemaBase):
    id: int
    title: str
    author: str
    isbn: str | None
    publisher: str | None
    publish_year: int | None
    category: str | None
    total_copies: int
    available_copies: int
    description: str | None
    created_at: datetime
    updated_at: datetime


class BookBriefOut(SchemaBase):
    id: int
    title: str
    author: str
    isbn: str | None
