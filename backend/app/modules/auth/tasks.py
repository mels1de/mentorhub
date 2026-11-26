import asyncio
import uuid

from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.integrations.email.smtp import SmtpEmailSender
from app.integrations.exceptions import IntegrationUnavailableError
from app.integrations.ports import EmailSender
from app.modules.auth import email_jobs
from app.modules.users.service import UserService
from app.worker.celery_app import celery_app
from app.worker.runtime import task_resources

# Transient SMTP failures: exponential backoff with full jitter, waits of up to 1, 2, 4, 8, 16 min.
RETRY_ON = (IntegrationUnavailableError,)
BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 1800
MAX_RETRIES = 5


async def _run(job: email_jobs.EmailJob, user_id: str, settings: Settings) -> bool:
    async with task_resources(settings) as resources:
        redis: Redis = resources.redis
        sender: EmailSender = SmtpEmailSender(settings)
        return await job(
            uuid.UUID(user_id),
            users=UserService(resources.session),
            redis=redis,
            sender=sender,
            settings=settings,
        )


@celery_app.task(
    name="emails.send_verification",
    autoretry_for=RETRY_ON,
    retry_backoff=BACKOFF_SECONDS,
    retry_backoff_max=MAX_BACKOFF_SECONDS,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def send_verification(user_id: str) -> bool:
    return asyncio.run(_run(email_jobs.send_verification, user_id, get_settings()))


@celery_app.task(
    name="emails.send_password_reset",
    autoretry_for=RETRY_ON,
    retry_backoff=BACKOFF_SECONDS,
    retry_backoff_max=MAX_BACKOFF_SECONDS,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def send_password_reset(user_id: str) -> bool:
    return asyncio.run(_run(email_jobs.send_password_reset, user_id, get_settings()))
