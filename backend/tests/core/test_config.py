import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings

STRONG_SECRET = "x" * 32


def make_settings(**kwargs: object) -> Settings:
    # _env_file=None: tests must not depend on a developer's local .env.
    return Settings(_env_file=None, **kwargs)  # type: ignore[arg-type]


def test_defaults_are_usable_locally() -> None:
    settings = make_settings()

    assert settings.environment == "local"
    assert settings.postgres_port == 15432


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    settings = make_settings()

    assert settings.postgres_host == "db"
    assert settings.postgres_port == 5432


def test_invalid_port_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PORT", "70000")

    with pytest.raises(ValidationError, match="postgres_port"):
        make_settings()


def test_secrets_are_hidden_in_repr_and_dump() -> None:
    settings = make_settings(postgres_password=SecretStr("p4ss-w0rd"))

    assert "p4ss-w0rd" not in repr(settings)
    assert "p4ss-w0rd" not in str(settings.model_dump())


def test_database_url_escapes_special_characters() -> None:
    settings = make_settings(postgres_password=SecretStr("p@ss:w/rd"))

    assert settings.database_url == (
        "postgresql+asyncpg://mentorhub:p%40ss%3Aw%2Frd@localhost:15432/mentorhub"
    )


def test_production_refuses_default_secret_key() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make_settings(environment="production")


def test_production_refuses_debug() -> None:
    with pytest.raises(ValidationError, match="DEBUG"):
        make_settings(environment="production", secret_key=SecretStr(STRONG_SECRET), debug=True)


def test_production_accepts_secure_config() -> None:
    settings = make_settings(environment="production", secret_key=SecretStr(STRONG_SECRET))

    assert settings.environment == "production"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()

    assert get_settings() is get_settings()
