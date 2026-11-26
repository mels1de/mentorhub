"""Opaque refresh tokens in Redis, rotated on every use, grouped into families (one per login).

Keys (all expire after the refresh TTL):
  auth:rt:{sha256(token)}   hash {uid, fam, used}  — kept after use, to detect reuse
  auth:fam:{family_id}      user id                — the family is alive while this key exists
  auth:user:{user_id}:fams  set of family ids      — for "log out everywhere"
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

import structlog
from redis.asyncio import Redis

from app.core.security import generate_token, hash_token
from app.modules.auth.exceptions import InvalidTokenError, RefreshTokenReusedError

logger = structlog.stdlib.get_logger(__name__)

# Two tabs refreshing at the same moment send the same token; the loser must not log the user out.
DEFAULT_REUSE_GRACE = timedelta(seconds=10)

# Check-and-mark in one atomic step: of several concurrent refreshes with one token exactly one
# sees used == 1. Returns seconds since the token was first used.
_CLAIM_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then return false end
local used = redis.call('HINCRBY', KEYS[1], 'used', 1)
local now = tonumber(redis.call('TIME')[1])
if used == 1 then redis.call('HSET', KEYS[1], 'used_at', now) end
local data = redis.call('HMGET', KEYS[1], 'uid', 'fam', 'used_at')
return {used, data[1], data[2], now - tonumber(data[3])}
"""


def _text(value: bytes | str) -> str:
    # The client uses decode_responses=True; the stubs still allow bytes.
    return value.decode() if isinstance(value, bytes) else value


def _token_key(token: str) -> str:
    return f"auth:rt:{hash_token(token)}"


def _family_key(family_id: str) -> str:
    return f"auth:fam:{family_id}"


def _user_families_key(user_id: uuid.UUID | str) -> str:
    return f"auth:user:{user_id}:fams"


@dataclass(frozen=True)
class RotatedToken:
    user_id: uuid.UUID
    token: str


class RefreshTokenStore:
    def __init__(
        self, redis: Redis, ttl: timedelta, reuse_grace: timedelta = DEFAULT_REUSE_GRACE
    ) -> None:
        self.redis = redis
        self.ttl = ttl
        self.reuse_grace = reuse_grace
        self._claim = redis.register_script(_CLAIM_SCRIPT)

    async def issue(self, user_id: uuid.UUID, family_id: str | None = None) -> str:
        """Issue a token; without `family_id` this starts a new family (a new login)."""
        token = generate_token()
        family_id = family_id or uuid.uuid7().hex
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(_token_key(token), mapping={"uid": str(user_id), "fam": family_id, "used": 0})
            pipe.expire(_token_key(token), self.ttl)
            # Sliding expiry: an active session lives on, an idle one dies after the TTL.
            pipe.set(_family_key(family_id), str(user_id), ex=self.ttl)
            pipe.sadd(_user_families_key(user_id), family_id)
            pipe.expire(_user_families_key(user_id), self.ttl)
            await pipe.execute()
        return token

    async def rotate(self, token: str) -> RotatedToken:
        claimed = await self._claim(keys=[_token_key(token)])
        if claimed is None:
            raise InvalidTokenError("The refresh token is invalid or expired.")
        used, user_id, family_id = int(claimed[0]), uuid.UUID(claimed[1]), claimed[2]
        seconds_since_first_use = int(claimed[3])

        if used > 1 and seconds_since_first_use < self.reuse_grace.total_seconds():
            # A parallel refresh already won; its response carries the new cookie.
            raise InvalidTokenError("This refresh token was just used.")
        if used > 1:
            # A token that was exchanged a while ago came back: either the client or an attacker
            # holds a stolen copy. We can't tell which, so the whole login is revoked.
            await self._revoke_family(user_id, family_id)
            logger.warning("refresh_token_reused", user_id=str(user_id))
            raise RefreshTokenReusedError("This session was revoked. Please log in again.")
        if not await self.redis.exists(_family_key(family_id)):
            raise InvalidTokenError("The session has ended. Please log in again.")

        return RotatedToken(user_id=user_id, token=await self.issue(user_id, family_id))

    async def revoke(self, token: str) -> None:
        user_id, family_id = await self.redis.hmget(_token_key(token), ["uid", "fam"])
        if user_id is not None and family_id is not None:
            await self._revoke_family(_text(user_id), _text(family_id))

    async def revoke_all(self, user_id: uuid.UUID) -> None:
        families = await self.redis.smembers(_user_families_key(user_id))
        async with self.redis.pipeline(transaction=True) as pipe:
            for family_id in families:
                pipe.delete(_family_key(_text(family_id)))
            pipe.delete(_user_families_key(user_id))
            await pipe.execute()

    async def _revoke_family(self, user_id: uuid.UUID | str, family_id: str) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(_family_key(family_id))
            pipe.srem(_user_families_key(user_id), family_id)
            await pipe.execute()
