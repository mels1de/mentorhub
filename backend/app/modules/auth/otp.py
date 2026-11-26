"""Email one-time passwords for the second login step.

Keys:
  auth:otp:{challenge_id}   hash {uid, code, attempts, sends}  TTL = OTP lifetime
  auth:otp:lock:{user_id}   "1"                                TTL = lockout

The code is stored as HMAC-SHA256 with the server secret, not a plain hash: there are only
10^6 codes, so a plain SHA-256 from a leaked Redis dump would be reversed instantly.
"""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from redis.asyncio import Redis

from app.core.config import Settings
from app.modules.auth.exceptions import InvalidOtpError, OtpLockedError

CODE_DIGITS = 6
MAX_SENDS = 3


@dataclass(frozen=True)
class OtpPolicy:
    ttl: timedelta
    max_attempts: int
    lockout: timedelta


class OtpStore:
    def __init__(self, redis: Redis, secret: str, policy: OtpPolicy) -> None:
        self.redis = redis
        self.secret = secret.encode()
        self.policy = policy

    @staticmethod
    def _challenge_key(challenge_id: str) -> str:
        return f"auth:otp:{challenge_id}"

    @staticmethod
    def _lock_key(user_id: uuid.UUID | str) -> str:
        return f"auth:otp:lock:{user_id}"

    def _digest(self, code: str) -> str:
        return hmac.new(self.secret, code.encode(), hashlib.sha256).hexdigest()

    async def lockout_seconds(self, user_id: uuid.UUID) -> int:
        ttl = await self.redis.ttl(self._lock_key(user_id))
        return max(int(ttl), 0)

    async def ensure_not_locked(self, user_id: uuid.UUID) -> None:
        if seconds := await self.lockout_seconds(user_id):
            raise OtpLockedError("Too many wrong codes. Try again later.", retry_after=seconds)

    async def create_challenge(self, user_id: uuid.UUID) -> str:
        """Start a challenge without a code; the worker sets one when it sends the email."""
        await self.ensure_not_locked(user_id)
        challenge_id = uuid.uuid7().hex
        key = self._challenge_key(challenge_id)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping={"uid": str(user_id), "attempts": 0, "sends": 0})
            pipe.expire(key, self.policy.ttl)
            await pipe.execute()
        return challenge_id

    async def issue_code(self, challenge_id: str) -> tuple[uuid.UUID, str] | None:
        """Generate a fresh code for the challenge; None if it expired or was resent too often."""
        key = self._challenge_key(challenge_id)
        user_id = await self.redis.hget(key, "uid")
        if user_id is None:
            return None
        if int(await self.redis.hincrby(key, "sends", 1)) > MAX_SENDS:
            return None
        code = f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"
        # A resend replaces the code but keeps the attempt counter: resending is no bypass.
        await self.redis.hset(key, "code", self._digest(code))
        return uuid.UUID(str(user_id)), code

    async def challenge_user(self, challenge_id: str) -> uuid.UUID:
        user_id = await self.redis.hget(self._challenge_key(challenge_id), "uid")
        if user_id is None:
            raise InvalidOtpError("The code has expired. Please log in again.")
        return uuid.UUID(str(user_id))

    async def verify(self, challenge_id: str, code: str) -> uuid.UUID:
        key = self._challenge_key(challenge_id)
        user_id = await self.challenge_user(challenge_id)
        await self.ensure_not_locked(user_id)

        attempts = int(await self.redis.hincrby(key, "attempts", 1))
        stored = await self.redis.hget(key, "code")
        if stored is not None and hmac.compare_digest(str(stored), self._digest(code)):
            await self.redis.delete(key)
            return user_id

        if attempts >= self.policy.max_attempts:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.delete(key)
                pipe.set(self._lock_key(user_id), "1", ex=self.policy.lockout)
                await pipe.execute()
            raise OtpLockedError(
                "Too many wrong codes. Try again later.",
                retry_after=int(self.policy.lockout.total_seconds()),
            )
        left = self.policy.max_attempts - attempts
        raise InvalidOtpError("The code is incorrect.", extensions={"attempts_left": left})


def otp_store(redis: Redis, settings: Settings) -> OtpStore:
    policy = OtpPolicy(
        ttl=timedelta(minutes=settings.otp_ttl_minutes),
        max_attempts=settings.otp_max_attempts,
        lockout=timedelta(minutes=settings.otp_lockout_minutes),
    )
    return OtpStore(redis, settings.secret_key.get_secret_value(), policy)
