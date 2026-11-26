import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.auth.access_tokens import ALGORITHM, create_access_token, decode_access_token
from app.modules.auth.exceptions import InvalidTokenError
from app.modules.users.models import UserRole

USER_ID = uuid.uuid7()


def test_roundtrip(settings: Settings) -> None:
    access = create_access_token(USER_ID, UserRole.MENTOR, settings)

    claims = decode_access_token(access.token, settings)

    assert claims.user_id == USER_ID
    assert claims.role is UserRole.MENTOR
    assert access.expires_in == settings.access_token_ttl_minutes * 60


def test_expired_token_is_rejected(settings: Settings) -> None:
    an_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    access = create_access_token(USER_ID, UserRole.MENTEE, settings, now=an_hour_ago)

    with pytest.raises(InvalidTokenError, match="expired"):
        decode_access_token(access.token, settings)


def test_token_signed_with_another_key_is_rejected(settings: Settings) -> None:
    other = settings.model_copy(
        update={"secret_key": SecretStr("another-secret-key-of-at-least-32-bytes")}
    )
    access = create_access_token(USER_ID, UserRole.MENTEE, other)

    with pytest.raises(InvalidTokenError):
        decode_access_token(access.token, settings)


def _payload(**overrides: object) -> dict[str, object]:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(USER_ID),
        "role": "admin",
        "typ": "access",
        "iss": "mentorhub",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def test_unsigned_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode(_payload(), key=None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {"typ": "refresh"},
        {"iss": "someone-else"},
        {"role": "superuser"},
        {"sub": "not-a-uuid"},
        {"exp": None},
        {"role": None},
    ],
    ids=["wrong-type", "wrong-issuer", "unknown-role", "bad-subject", "no-exp", "no-role"],
)
def test_malformed_claims_are_rejected(settings: Settings, overrides: dict[str, object]) -> None:
    secret = settings.secret_key.get_secret_value()
    token = jwt.encode(_payload(**overrides), secret, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings)
