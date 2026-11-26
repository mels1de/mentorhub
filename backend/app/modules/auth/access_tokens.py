import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings
from app.modules.auth.exceptions import InvalidTokenError
from app.modules.users.models import UserRole

ALGORITHM = "HS256"
ISSUER = "mentorhub"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_in: int


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    role: UserRole


def create_access_token(
    user_id: uuid.UUID, role: UserRole, settings: Settings, *, now: datetime | None = None
) -> AccessToken:
    now = now or datetime.now(UTC)
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "typ": ACCESS_TOKEN_TYPE,
        "iss": ISSUER,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)
    return AccessToken(token=token, expires_in=int(ttl.total_seconds()))


def decode_access_token(token: str, settings: Settings) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            # Pinned list: never let the token header choose the algorithm (e.g. "none").
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["sub", "role", "typ", "iat", "exp"]},
        )
        if payload["typ"] != ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("Wrong token type.")
        return AccessClaims(user_id=uuid.UUID(payload["sub"]), role=UserRole(payload["role"]))
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("The access token has expired.") from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise InvalidTokenError("The access token is invalid.") from exc
