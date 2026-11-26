import uuid
from typing import Any, Protocol

import structlog
from celery import Task
from starlette.concurrency import run_in_threadpool

from app.modules.auth import tasks

logger = structlog.stdlib.get_logger(__name__)


class AuthMailer(Protocol):
    """How the auth service asks for emails; tests use a fake that records the calls."""

    async def send_verification(self, user_id: uuid.UUID) -> None: ...

    async def send_password_reset(self, user_id: uuid.UUID) -> None: ...


class CeleryAuthMailer:
    async def send_verification(self, user_id: uuid.UUID) -> None:
        await self._enqueue(tasks.send_verification, user_id)

    async def send_password_reset(self, user_id: uuid.UUID) -> None:
        await self._enqueue(tasks.send_password_reset, user_id)

    @staticmethod
    async def _enqueue(task: Task[Any, Any], user_id: uuid.UUID) -> None:
        try:
            # .delay() does blocking network I/O to RabbitMQ; keep it off the event loop.
            await run_in_threadpool(task.delay, str(user_id))
        except Exception:
            # The DB change is already committed; a lost email is recoverable (resend), a 500
            # after a successful registration is not. A transactional outbox (Phase 3) closes
            # this gap properly.
            logger.exception("email_enqueue_failed", task=task.name, user_id=str(user_id))
