from typing import Literal

from pydantic import Field, field_validator

from backend.app.schemas.common import SchemaBase


class LoginRequest(SchemaBase):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_]{3,64}$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value


class TokenOut(SchemaBase):
    access_token: str
    token_type: Literal["bearer"]
