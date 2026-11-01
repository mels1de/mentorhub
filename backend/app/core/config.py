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
