import re

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.auth import email_jobs
from app.modules.users.models import User
from app.modules.users.service import UserService
from tests.fakes import FakeAuthMailer, FakeEmailSender
from tests.modules.auth.helpers import PASSWORD, bearer, create_user, login

pytestmark = pytest.mark.integration

AUTH = "/api/v1/auth"


async def user_with_2fa(session: AsyncSession) -> User:
    user = await create_user(session)
    user.is_email_verified = True
    user.is_2fa_enabled = True
    await session.commit()
    return user


async def start_login(api: AsyncClient) -> str:
    response = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "otp_required"
    assert body["expires_in"] == 600
    assert "access_token" not in body
    assert "set-cookie" not in response.headers
    challenge_id: str = body["challenge_id"]
    return challenge_id


async def emailed_code(
    challenge_id: str, session: AsyncSession, redis: Redis, settings: Settings
) -> str:
    sender = FakeEmailSender()
    sent = await email_jobs.send_login_code(
        challenge_id, users=UserService(session), redis=redis, sender=sender, settings=settings
    )
    assert sent
    match = re.search(r"\b(\d{6})\b", sender.outbox[-1].text)
    assert match
    return match.group(1)


async def test_login_without_2fa_returns_tokens(api: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session)

    response = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )

    assert response.json()["status"] == "authenticated"


async def test_login_with_2fa_needs_the_emailed_code(
    api: AsyncClient,
    db_session: AsyncSession,
    redis: Redis,
    settings: Settings,
    mailer: FakeAuthMailer,
) -> None:
    await user_with_2fa(db_session)
    challenge_id = await start_login(api)
    assert mailer.login_codes == [challenge_id]
    code = await emailed_code(challenge_id, db_session, redis, settings)

    response = await api.post(
        f"{AUTH}/2fa/verify", json={"challenge_id": challenge_id, "code": code}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "authenticated"
    assert "refresh_token" in response.headers["set-cookie"]
    me = await api.get("/api/v1/users/me", headers=bearer(response.json()["access_token"]))
    assert me.json()["is_2fa_enabled"] is True


async def test_wrong_code_then_lockout(
    api: AsyncClient, db_session: AsyncSession, redis: Redis, settings: Settings
) -> None:
    await user_with_2fa(db_session)
    challenge_id = await start_login(api)
    code = await emailed_code(challenge_id, db_session, redis, settings)
    bad = f"{(int(code) + 1) % 10**6:06d}"

    statuses = []
    for _ in range(settings.otp_max_attempts):
        response = await api.post(
            f"{AUTH}/2fa/verify", json={"challenge_id": challenge_id, "code": bad}
        )
        statuses.append(response.status_code)

    assert statuses == [401] * (settings.otp_max_attempts - 1) + [429]
    assert response.json()["code"] == "otp_locked"
    assert response.headers["retry-after"] == str(settings.otp_lockout_minutes * 60)
    blocked = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    assert blocked.status_code == 429


async def test_code_format_is_validated(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/2fa/verify", json={"challenge_id": "x", "code": "12ab56"})

    assert response.status_code == 422


async def test_resend_queues_another_code(
    api: AsyncClient, db_session: AsyncSession, mailer: FakeAuthMailer
) -> None:
    await user_with_2fa(db_session)
    challenge_id = await start_login(api)

    response = await api.post(f"{AUTH}/2fa/resend", json={"challenge_id": challenge_id})

    assert response.status_code == 202
    assert mailer.login_codes == [challenge_id, challenge_id]


async def test_resend_for_an_unknown_challenge_is_401(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/2fa/resend", json={"challenge_id": "missing"})

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_otp"


# --- enable / disable ----------------------------------------------------------------


async def test_enable_and_disable_2fa(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    user.is_email_verified = True
    await db_session.commit()
    token = await login(api)

    enabled = await api.post(
        f"{AUTH}/2fa/enable", json={"password": PASSWORD}, headers=bearer(token)
    )
    await db_session.refresh(user)
    assert enabled.status_code == 204
    assert user.is_2fa_enabled

    disabled = await api.post(
        f"{AUTH}/2fa/disable", json={"password": PASSWORD}, headers=bearer(token)
    )
    await db_session.refresh(user)
    assert disabled.status_code == 204
    assert not user.is_2fa_enabled


async def test_enabling_2fa_needs_a_verified_email(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session)
    token = await login(api)

    response = await api.post(
        f"{AUTH}/2fa/enable", json={"password": PASSWORD}, headers=bearer(token)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "email_not_verified"


async def test_toggling_2fa_needs_the_password(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    user.is_email_verified = True
    await db_session.commit()
    token = await login(api)

    response = await api.post(
        f"{AUTH}/2fa/enable", json={"password": "wrong-password"}, headers=bearer(token)
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_toggling_2fa_needs_login(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/2fa/enable", json={"password": PASSWORD})

    assert response.status_code == 401
