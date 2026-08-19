from datetime import datetime

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import SchemaBase


_USERNAME = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_]{3,64}$")
_PASSWORD_REQUIRED = Field(min_length=8, max_length=128)
_PASSWORD_OPTIONAL = Field(default=None, min_length=8, max_length=128)


class UserCreate(SchemaBase):
    username: str = _USERNAME
    password: str = _PASSWORD_REQUIRED
    display_name: str | None = Field(default=None, max_length=64)

    @field_validator("username", "display_name", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserUpdate(SchemaBase):
    display_name: str | None = Field(default=None, max_length=64)
    password: str | None = _PASSWORD_OPTIONAL
    is_active: bool | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_update(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个更新字段")
        return self


class UserOut(SchemaBase):
    id: int
    username: str
    display_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBriefOut(SchemaBase):
    id: int
    username: str
    display_name: str | None
