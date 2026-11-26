"""What the email tasks do, written against ports so tests run it without Celery or SMTP.

The token is generated here, in the worker, not in the API: only the user id travels through
RabbitMQ, so no secret ends up in the broker, in Flower or in task results.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta

import structlog
from redis.asyncio import Redis

from app.core.config import Settings
from app.integrations.ports import EmailSender
from app.modules.auth.emails import password_reset_email, verification_email
from app.modules.auth.one_time_tokens import OneTimeTokenStore, TokenPurpose
from app.modules.users.service import UserService

logger = structlog.stdlib.get_logger(__name__)

type EmailJob = Callable[..., Awaitable[bool]]


def verification_tokens(redis: Redis, settings: Settings) -> OneTimeTokenStore:
    ttl = timedelta(hours=settings.email_verification_ttl_hours)
    return OneTimeTokenStore(redis, TokenPurpose.VERIFY_EMAIL, ttl)


def reset_tokens(redis: Redis, settings: Settings) -> OneTimeTokenStore:
    ttl = timedelta(minutes=settings.password_reset_ttl_minutes)
    return OneTimeTokenStore(redis, TokenPurpose.RESET_PASSWORD, ttl)


async def send_verification(
    user_id: uuid.UUID, *, users: UserService, redis: Redis, sender: EmailSender, settings: Settings
) -> bool:
    """Return False when there is nothing to do (user gone or already verified)."""
    user = await users.find(user_id)
    if user is None or user.is_email_verified:
        return False
    token = await verification_tokens(redis, settings).issue(user.id)
    await sender.send(verification_email(user.email, token, settings))
    logger.info("verification_email_sent", user_id=str(user.id))
    return True


async def send_password_reset(
    user_id: uuid.UUID, *, users: UserService, redis: Redis, sender: EmailSender, settings: Settings
) -> bool:
    user = await users.find(user_id)
    if user is None or not user.is_active:
        return False
    token = await reset_tokens(redis, settings).issue(user.id)
    await sender.send(password_reset_email(user.email, token, settings))
    logger.info("password_reset_email_sent", user_id=str(user.id))
    return True
