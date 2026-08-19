from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_SECRET_KEY = "development-only-secret-key-change-me"


class Settings(BaseSettings):
    app_name: str = "Library System"
    environment: str = "development"
    database_url: str = "sqlite:///./database/library.db"
    # No default is intentional: application startup must fail without an explicit key.
    secret_key: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    borrow_days_default: int = 30
    max_concurrent_borrows: int = 5
    page_size_default: int = 20
    page_size_max: int = 100
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_username: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized == INSECURE_SECRET_KEY:
            raise ValueError("必须显式配置安全的 SECRET_KEY，不能使用开发占位值")
        return normalized

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.jwt_algorithm != "HS256":
            raise ValueError("MVP 仅支持 HS256 JWT")
        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES 必须大于 0")
        if self.borrow_days_default <= 0 or self.max_concurrent_borrows <= 0:
            raise ValueError("借阅配置必须大于 0")
        if self.page_size_default <= 0 or self.page_size_max <= 0:
            raise ValueError("分页配置必须大于 0")
        if self.page_size_default > self.page_size_max:
            raise ValueError("PAGE_SIZE_DEFAULT 不能大于 PAGE_SIZE_MAX")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
