import re
import uuid

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.ports import EmailMessage
from app.modules.auth import email_jobs
from app.modules.users.service import UserService
from tests.fakes import FakeAuthMailer, FakeEmailSender
from tests.modules.auth.helpers import PASSWORD, bearer, create_user, login

pytestmark = pytest.mark.integration

AUTH = "/api/v1/auth"
NEW_PASSWORD = "a brand new password"


def token_from(message: EmailMessage) -> str:
    match = re.search(r"#token=([\w-]+)", message.text)
    assert match, message.text
    return match.group(1)


async def deliver(
    job: email_jobs.EmailJob,
    user_id: uuid.UUID,
    session: AsyncSession,
    redis: Redis,
    settings: Settings,
) -> EmailMessage:
    """Run what the Celery task would run and return the email it sent."""
    sender = FakeEmailSender()
    sent = await job(
        user_id, users=UserService(session), redis=redis, sender=sender, settings=settings
    )
    assert sent
    [message] = sender.outbox
    return message


# --- email verification --------------------------------------------------------------


async def test_register_queues_a_verification_email(
    api: AsyncClient, mailer: FakeAuthMailer
) -> None:
    response = await api.post(
        f"{AUTH}/register", json={"email": "new@example.com", "password": PASSWORD}
    )

    assert mailer.verification == [uuid.UUID(response.json()["id"])]


async def test_verification_link_verifies_the_email_once(
    api: AsyncClient, db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    user = await create_user(db_session)
    message = await deliver(email_jobs.send_verification, user.id, db_session, redis, settings)

    assert message.to == "user@example.com"
    assert message.text.count(settings.frontend_url + "/verify-email#token=") == 1
    first = await api.post(f"{AUTH}/verify-email", json={"token": token_from(message)})
    second = await api.post(f"{AUTH}/verify-email", json={"token": token_from(message)})

    assert first.status_code == 204
    await db_session.refresh(user)
    assert user.is_email_verified
    assert second.status_code == 422
    assert second.json()["code"] == "invalid_link"


async def test_no_email_for_an_already_verified_user(
    db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    user = await create_user(db_session)
    user.is_email_verified = True
    await db_session.commit()
    sender = FakeEmailSender()

    sent = await email_jobs.send_verification(
        user.id, users=UserService(db_session), redis=redis, sender=sender, settings=settings
    )

    assert not sent
    assert sender.outbox == []


async def test_no_email_for_a_deleted_user(
    db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    sender = FakeEmailSender()

    sent = await email_jobs.send_verification(
        uuid.uuid7(), users=UserService(db_session), redis=redis, sender=sender, settings=settings
    )

    assert not sent


async def test_garbage_verification_token_is_422(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/verify-email", json={"token": "garbage"})

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_link"


async def test_resend_verification_needs_login(api: AsyncClient) -> None:
    assert (await api.post(f"{AUTH}/verify-email/resend")).status_code == 401


async def test_resend_verification_queues_only_for_unverified_users(
    api: AsyncClient, db_session: AsyncSession, mailer: FakeAuthMailer
) -> None:
    user = await create_user(db_session)
    token = await login(api)

    first = await api.post(f"{AUTH}/verify-email/resend", headers=bearer(token))
    user.is_email_verified = True
    await db_session.commit()
    second = await api.post(f"{AUTH}/verify-email/resend", headers=bearer(token))

    assert first.status_code == second.status_code == 202
    assert mailer.verification == [user.id]


# --- password reset ------------------------------------------------------------------


async def test_reset_request_looks_the_same_for_unknown_emails(
    api: AsyncClient, db_session: AsyncSession, mailer: FakeAuthMailer
) -> None:
    user = await create_user(db_session)

    known = await api.post(f"{AUTH}/password-reset", json={"email": "USER@example.com"})
    unknown = await api.post(f"{AUTH}/password-reset", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.content == unknown.content
    assert mailer.password_reset == [user.id]


async def test_disabled_users_get_no_reset_email(
    api: AsyncClient, db_session: AsyncSession, mailer: FakeAuthMailer
) -> None:
    user = await create_user(db_session)
    user.is_active = False
    await db_session.commit()

    await api.post(f"{AUTH}/password-reset", json={"email": user.email})

    assert mailer.password_reset == []


async def test_password_reset_changes_password_and_ends_all_sessions(
    api: AsyncClient, db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    user = await create_user(db_session)
    await login(api)
    message = await deliver(email_jobs.send_password_reset, user.id, db_session, redis, settings)

    response = await api.post(
        f"{AUTH}/password-reset/confirm",
        json={"token": token_from(message), "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 204
    assert (await api.post(f"{AUTH}/refresh")).status_code == 401
    old = await api.post(f"{AUTH}/login", json={"email": user.email, "password": PASSWORD})
    assert old.status_code == 401
    await login(api, password=NEW_PASSWORD)
    await db_session.refresh(user)
    assert user.is_email_verified


async def test_reset_link_works_once(
    api: AsyncClient, db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    user = await create_user(db_session)
    message = await deliver(email_jobs.send_password_reset, user.id, db_session, redis, settings)
    payload = {"token": token_from(message), "new_password": NEW_PASSWORD}

    await api.post(f"{AUTH}/password-reset/confirm", json=payload)
    again = await api.post(f"{AUTH}/password-reset/confirm", json=payload)

    assert again.status_code == 422
    assert again.json()["code"] == "invalid_link"


async def test_reset_rejects_a_weak_new_password(api: AsyncClient) -> None:
    response = await api.post(
        f"{AUTH}/password-reset/confirm", json={"token": "anything", "new_password": "short"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
