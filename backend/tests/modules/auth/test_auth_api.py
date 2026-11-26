from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.refresh_tokens import RefreshTokenStore
from app.modules.auth.service import get_refresh_token_store
from app.modules.users.models import UserRole
from tests.modules.auth.helpers import (
    PASSWORD,
    bearer,
    create_user,
    login,
    refresh_cookie,
    refresh_with,
)

pytestmark = pytest.mark.integration

AUTH = "/api/v1/auth"


# --- register ------------------------------------------------------------------------


async def test_register_creates_a_mentee_by_default(api: AsyncClient) -> None:
    response = await api.post(
        f"{AUTH}/register", json={"email": "New@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "mentee"
    assert body["is_email_verified"] is False
    assert "password" not in response.text
    assert "password_hash" not in body


async def test_register_as_mentor(api: AsyncClient) -> None:
    response = await api.post(
        f"{AUTH}/register",
        json={"email": "mentor@example.com", "password": PASSWORD, "role": "mentor"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "mentor"


async def test_register_duplicate_email_ignores_case(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "taken@example.com")

    response = await api.post(
        f"{AUTH}/register", json={"email": "TAKEN@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com", "password": "x" * 129},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "a@example.com", "password": PASSWORD, "role": "admin"},
    ],
    ids=["short-password", "long-password", "bad-email", "self-made-admin"],
)
async def test_register_rejects_invalid_input(api: AsyncClient, payload: dict[str, str]) -> None:
    response = await api.post(f"{AUTH}/register", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert PASSWORD not in response.text


# --- login ---------------------------------------------------------------------------


async def test_login_returns_access_token_and_refresh_cookie(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session)

    response = await api.post(
        f"{AUTH}/login", json={"email": "USER@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"].lower()
    for attribute in ("httponly", "secure", "samesite=strict", "path=/api/v1/auth"):
        assert attribute in cookie
    assert "refresh_token" not in body


async def test_login_records_last_login(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)

    await login(api)

    await db_session.refresh(user)
    assert user.last_login_at is not None


async def test_wrong_password_and_unknown_email_look_the_same(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session)

    wrong_password = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": "wrong-password"}
    )
    unknown_email = await api.post(
        f"{AUTH}/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]
    assert wrong_password.json()["code"] == "invalid_credentials"
    assert wrong_password.headers["www-authenticate"] == "Bearer"
    assert "set-cookie" not in wrong_password.headers


async def test_disabled_account_cannot_log_in(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    user.is_active = False
    await db_session.commit()

    response = await api.post(f"{AUTH}/login", json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["code"] == "account_disabled"


# --- refresh -------------------------------------------------------------------------


async def test_refresh_rotates_the_cookie(api: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session)
    login_response = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    first = refresh_cookie(login_response)

    response = await api.post(f"{AUTH}/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert refresh_cookie(response) != first


async def test_refresh_without_cookie_is_401(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_reused_refresh_token_revokes_the_session(
    api: AsyncClient, db_session: AsyncSession, store_without_grace: None
) -> None:
    await create_user(db_session)
    login_response = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    stolen = refresh_cookie(login_response)
    await api.post(f"{AUTH}/refresh")

    replay = await refresh_with(api, stolen)
    after = await refresh_with(api, stolen)

    assert replay.status_code == 401
    assert replay.json()["code"] == "refresh_token_reused", replay.json()
    assert after.status_code == 401


async def test_refresh_for_a_disabled_user_is_401(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session)
    await login(api)
    user.is_active = False
    await db_session.commit()

    response = await api.post(f"{AUTH}/refresh")

    assert response.status_code == 401


async def test_refreshed_access_token_carries_the_current_role(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session)
    await login(api)
    user.role = UserRole.MENTOR
    await db_session.commit()

    response = await api.post(f"{AUTH}/refresh")
    me = await api.get("/api/v1/users/me", headers=bearer(response.json()["access_token"]))

    assert me.json()["role"] == "mentor"


# --- logout --------------------------------------------------------------------------


async def test_logout_ends_the_session_and_clears_the_cookie(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session)
    login_response = await api.post(
        f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    token = refresh_cookie(login_response)

    response = await api.post(f"{AUTH}/logout")

    assert response.status_code == 204
    assert 'refresh_token=""' in response.headers["set-cookie"]
    replay = await refresh_with(api, token)
    assert replay.status_code == 401


async def test_logout_without_a_session_is_still_204(api: AsyncClient) -> None:
    assert (await api.post(f"{AUTH}/logout")).status_code == 204


async def test_logout_all_needs_an_access_token(api: AsyncClient) -> None:
    response = await api.post(f"{AUTH}/logout-all")

    assert response.status_code == 401


async def test_logout_all_ends_every_session(api: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session)
    other_device = refresh_cookie(
        await api.post(f"{AUTH}/login", json={"email": "user@example.com", "password": PASSWORD})
    )
    access = await login(api)

    response = await api.post(f"{AUTH}/logout-all", headers=bearer(access))

    assert response.status_code == 204
    replay = await refresh_with(api, other_device)
    assert replay.status_code == 401


# --- fixtures ------------------------------------------------------------------------


@pytest.fixture
def store_without_grace(app: FastAPI) -> None:
    def override() -> RefreshTokenStore:
        return RefreshTokenStore(app.state.redis, timedelta(days=7), reuse_grace=timedelta(0))

    app.dependency_overrides[get_refresh_token_store] = override
