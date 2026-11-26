"""Single-use tokens for links in emails (email verification, password reset).

Keys (expire after the purpose's TTL):
  auth:{purpose}:{sha256(token)}  user id    — consumed with GETDEL, so it works exactly once
  auth:{purpose}:user:{user_id}   token hash — only the newest link per user is valid
"""

import uuid
from datetime import timedelta
from enum import StrEnum

from redis.asyncio import Redis

from app.core.security import generate_token, hash_token
from app.modules.auth.exceptions import InvalidLinkError


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify"
    RESET_PASSWORD = "reset"  # noqa: S105


class OneTimeTokenStore:
    def __init__(self, redis: Redis, purpose: TokenPurpose, ttl: timedelta) -> None:
        self.redis = redis
        self.purpose = purpose
        self.ttl = ttl

    def _token_key(self, token_hash: str) -> str:
        return f"auth:{self.purpose}:{token_hash}"

    def _user_key(self, user_id: uuid.UUID | str) -> str:
        return f"auth:{self.purpose}:user:{user_id}"

    async def issue(self, user_id: uuid.UUID) -> str:
        token = generate_token()
        token_hash = hash_token(token)
        previous = await self.redis.getdel(self._user_key(user_id))
        async with self.redis.pipeline(transaction=True) as pipe:
            if previous is not None:
                pipe.delete(self._token_key(str(previous)))
            pipe.set(self._token_key(token_hash), str(user_id), ex=self.ttl)
            pipe.set(self._user_key(user_id), token_hash, ex=self.ttl)
            await pipe.execute()
        return token

    async def consume(self, token: str) -> uuid.UUID:
        user_id = await self.redis.getdel(self._token_key(hash_token(token)))
        if user_id is None:
            raise InvalidLinkError("This link is invalid, expired or was already used.")
        await self.redis.delete(self._user_key(str(user_id)))
        return uuid.UUID(str(user_id))
