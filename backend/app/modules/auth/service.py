from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings
from app.core.dependencies import SettingsDep
from app.core.security import verify_password
from app.db.redis import RedisDep
from app.modules.auth.access_tokens import create_access_token
from app.modules.auth.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.modules.auth.refresh_tokens import RefreshTokenStore
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.users.models import User
from app.modules.users.service import UserService, UserServiceDep

logger = structlog.stdlib.get_logger(__name__)


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str


class AuthService:
    def __init__(self, users: UserService, refresh_tokens: RefreshTokenStore, settings: Settings):
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.settings = settings

    async def register(self, data: RegisterRequest) -> User:
        user = await self.users.create(email=data.email, password=data.password, role=data.role)
        logger.info("user_registered", user_id=str(user.id), role=user.role.value)
        return user

    async def login(self, data: LoginRequest) -> IssuedTokens:
        user = await self.users.find_by_email(data.email)
        valid, new_hash = verify_password(data.password, user.password_hash if user else None)
        if user is None or not valid:
            # Same error for "no such user" and "wrong password": no account enumeration.
            raise InvalidCredentialsError("Incorrect email or password.")
        if not user.is_active:
            raise AccountDisabledError("This account is disabled.")
        await self.users.record_login(user, new_password_hash=new_hash)
        logger.info("user_logged_in", user_id=str(user.id))
        return await self._issue(user, family_id=None)

    async def refresh(self, refresh_token: str | None) -> IssuedTokens:
        if not refresh_token:
            raise InvalidTokenError("No refresh token.")
        rotated = await self.refresh_tokens.rotate(refresh_token)
        user = await self.users.find(rotated.user_id)
        if user is None or not user.is_active:
            await self.refresh_tokens.revoke(rotated.token)
            raise InvalidTokenError("The session has ended. Please log in again.")
        access = create_access_token(user.id, user.role, self.settings)
        return IssuedTokens(access.token, access.expires_in, rotated.token)

    async def logout(self, refresh_token: str | None) -> None:
        # Idempotent: logging out without (or with a dead) cookie still succeeds.
        if refresh_token:
            await self.refresh_tokens.revoke(refresh_token)

    async def logout_everywhere(self, user: User) -> None:
        await self.refresh_tokens.revoke_all(user.id)
        logger.info("user_logged_out_everywhere", user_id=str(user.id))

    async def _issue(self, user: User, family_id: str | None) -> IssuedTokens:
        access = create_access_token(user.id, user.role, self.settings)
        refresh = await self.refresh_tokens.issue(user.id, family_id)
        return IssuedTokens(access.token, access.expires_in, refresh)


def get_refresh_token_store(redis: RedisDep, settings: SettingsDep) -> RefreshTokenStore:
    return RefreshTokenStore(redis, timedelta(days=settings.refresh_token_ttl_days))


def get_auth_service(
    users: UserServiceDep,
    refresh_tokens: Annotated[RefreshTokenStore, Depends(get_refresh_token_store)],
    settings: SettingsDep,
) -> AuthService:
    return AuthService(users, refresh_tokens, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
