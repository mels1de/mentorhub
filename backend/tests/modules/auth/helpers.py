from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, UserRole
from app.modules.users.service import UserService

PASSWORD = "correct horse battery"


async def create_user(
    session: AsyncSession,
    email: str = "user@example.com",
    *,
    role: UserRole = UserRole.MENTEE,
    password: str = PASSWORD,
) -> User:
    return await UserService(session).create(email=email, password=password, role=role)


async def login(api: AsyncClient, email: str = "user@example.com", password: str = PASSWORD) -> str:
    response = await api.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def refresh_cookie(response: Response) -> str:
    token = response.cookies.get("refresh_token")
    assert token, "no refresh_token cookie in the response"
    return token


async def refresh_with(api: AsyncClient, token: str) -> Response:
    """Call /refresh presenting exactly `token`, like a client holding an old or stolen copy."""
    api.cookies.clear()
    # http.cookiejar files cookies of a dotless host like "test" under "test.local".
    api.cookies.set("refresh_token", token, domain="test.local", path="/api/v1/auth")
    return await api.post("/api/v1/auth/refresh")
