from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.auth.access_tokens import create_access_token
from app.modules.users.models import UserRole
from tests.modules.auth.helpers import bearer, create_user, login

pytestmark = pytest.mark.integration

ME = "/api/v1/users/me"
USERS = "/api/v1/users"


async def test_me_returns_the_current_user(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)

    response = await api.get(ME, headers=bearer(await login(api)))

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert "password_hash" not in response.json()


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer garbage"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
    ids=["no-header", "garbage-token", "wrong-scheme"],
)
async def test_me_without_a_valid_token_is_401(api: AsyncClient, headers: dict[str, str]) -> None:
    response = await api.get(ME, headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_expired_token_is_401(
    api: AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    expired = create_access_token(
        user.id, user.role, settings, now=datetime.now(UTC) - timedelta(hours=1)
    )

    response = await api.get(ME, headers=bearer(expired.token))

    assert response.status_code == 401
    assert response.json()["detail"] == "The access token has expired."


async def test_token_of_a_disabled_user_stops_working(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session)
    token = await login(api)
    user.is_active = False
    await db_session.commit()

    assert (await api.get(ME, headers=bearer(token))).status_code == 401


async def test_token_of_a_deleted_user_is_401(api: AsyncClient, db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    token = await login(api)
    await db_session.delete(user)
    await db_session.commit()

    assert (await api.get(ME, headers=bearer(token))).status_code == 401


async def test_admin_lists_users_paginated(api: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, "admin@example.com", role=UserRole.ADMIN)
    for i in range(3):
        await create_user(db_session, f"user{i}@example.com")
    token = await login(api, "admin@example.com")

    response = await api.get(USERS, params={"size": 2}, headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["pages"] == 2
    assert len(body["items"]) == 2


@pytest.mark.parametrize("role", [UserRole.MENTEE, UserRole.MENTOR])
async def test_non_admins_cannot_list_users(
    api: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    await create_user(db_session, role=role)

    response = await api.get(USERS, headers=bearer(await login(api)))

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


async def test_listing_users_needs_authentication(api: AsyncClient) -> None:
    assert (await api.get(USERS)).status_code == 401


async def test_page_size_is_capped(api: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, role=UserRole.ADMIN)

    response = await api.get(USERS, params={"size": 101}, headers=bearer(await login(api)))

    assert response.status_code == 422
