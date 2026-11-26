from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import quote

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path: pydantic-settings resolves a relative env_file against the CWD.
REPO_ROOT = Path(__file__).resolve().parents[3]

INSECURE_SECRET_KEY = "insecure-local-dev-key-change-me"  # noqa: S105
MIN_SECRET_KEY_LENGTH = 32

type Environment = Literal["local", "test", "production"]
type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
type LogFormat = Literal["console", "json"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        # The root .env is shared with Docker Compose and has keys the API doesn't use.
        extra="ignore",
    )

    app_name: str = "MentorHub API"
    environment: Environment = "local"
    debug: bool = False
    secret_key: SecretStr = SecretStr(INSECURE_SECRET_KEY)

    log_level: LogLevel = "INFO"
    log_format: LogFormat = "console"

    postgres_host: str = "localhost"
    postgres_port: int = Field(default=15432, ge=1, le=65535)
    postgres_user: str = "mentorhub"
    postgres_password: SecretStr = SecretStr("mentorhub")
    postgres_db: str = "mentorhub"

    # @property, not @computed_field: computed fields end up in repr() and model_dump().
    @property
    def database_url(self) -> str:
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    redis_host: str = "localhost"
    redis_port: int = Field(default=16379, ge=1, le=65535)
    # Cache, tokens and rate limits. Tests use 15 and flush it; 1 is the Celery result backend.
    redis_db: int = Field(default=0, ge=0, le=15)

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_result_backend_url(self) -> str:
        # Separate logical DB, so FLUSHDB on the cache never wipes task results (and vice versa).
        return f"redis://{self.redis_host}:{self.redis_port}/1"

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = Field(default=15672, ge=1, le=65535)
    rabbitmq_user: str = "mentorhub"
    rabbitmq_password: SecretStr = SecretStr("mentorhub")

    @property
    def celery_broker_url(self) -> str:
        user = quote(self.rabbitmq_user, safe="")
        password = quote(self.rabbitmq_password.get_secret_value(), safe="")
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}//"

    smtp_host: str = "localhost"
    smtp_port: int = Field(default=11025, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_start_tls: bool = False
    email_from: str = "MentorHub <no-reply@mentorhub.local>"
    # Links in emails point here (the SPA), not at the API.
    frontend_url: str = "http://localhost:5173"

    email_verification_ttl_hours: int = Field(default=24, ge=1, le=168)
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=1440)

    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=7, ge=1, le=30)
    # Browsers treat http://localhost as a secure context, so Secure cookies work locally too.
    cookie_secure: bool = True

    @model_validator(mode="after")
    def _refuse_insecure_production_config(self) -> Self:
        if self.environment != "production":
            return self
        secret = self.secret_key.get_secret_value()
        if secret == INSECURE_SECRET_KEY or len(secret) < MIN_SECRET_KEY_LENGTH:
            msg = f"SECRET_KEY must be a random value of >= {MIN_SECRET_KEY_LENGTH} chars"
            raise ValueError(msg)
        if self.debug:
            msg = "DEBUG must be false in production"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
