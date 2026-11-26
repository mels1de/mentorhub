import uuid

import pytest

from app.core.config import Settings
from app.integrations.email.smtp import SmtpEmailSender
from app.integrations.exceptions import IntegrationUnavailableError
from app.integrations.ports import EmailMessage
from app.modules.auth import tasks
from app.modules.auth.mailer import CeleryAuthMailer
from app.worker.celery_app import celery_app


def test_email_tasks_are_registered_and_routed_to_the_emails_queue() -> None:
    for task in (tasks.send_verification, tasks.send_password_reset):
        assert task.name in celery_app.tasks
        assert celery_app.amqp.router.route({}, task.name)["queue"].name == "emails"
        assert task.max_retries == tasks.MAX_RETRIES
        assert IntegrationUnavailableError in getattr(task, "autoretry_for", ())


async def test_mailer_sends_only_the_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(tasks.send_verification, "delay", lambda *args: calls.append(args))
    user_id = uuid.uuid7()

    await CeleryAuthMailer().send_verification(user_id)

    assert calls == [(str(user_id),)]


async def test_broker_outage_does_not_fail_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    def broker_down(*_: object) -> None:
        raise ConnectionError("broker down")

    monkeypatch.setattr(tasks.send_password_reset, "delay", broker_down)

    await CeleryAuthMailer().send_password_reset(uuid.uuid7())


async def test_unreachable_smtp_is_a_retryable_error(settings: Settings) -> None:
    sender = SmtpEmailSender(settings.model_copy(update={"smtp_port": 1}))

    with pytest.raises(IntegrationUnavailableError):
        await sender.send(EmailMessage(to="a@example.com", subject="s", text="t"))
