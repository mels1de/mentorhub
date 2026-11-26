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
from app.modules.auth.email_jobs import reset_tokens, verification_tokens
from app.modules.auth.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    InvalidLinkError,
    InvalidTokenError,
)
from app.modules.auth.mailer import AuthMailer, CeleryAuthMailer
from app.modules.auth.one_time_tokens import OneTimeTokenStore
from app.modules.auth.refresh_tokens import RefreshTokenStore
from app.modules.auth.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
)
from app.modules.users.models import User
from app.modules.users.service import UserService, UserServiceDep

logger = structlog.stdlib.get_logger(__name__)


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str


@dataclass(frozen=True)
class EmailTokenStores:
    verification: OneTimeTokenStore
    reset: OneTimeTokenStore


class AuthService:
    def __init__(
        self,
        users: UserService,
        refresh_tokens: RefreshTokenStore,
        email_tokens: EmailTokenStores,
        mailer: AuthMailer,
        settings: Settings,
    ) -> None:
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.email_tokens = email_tokens
        self.mailer = mailer
        self.settings = settings

    async def register(self, data: RegisterRequest) -> User:
        user = await self.users.create(email=data.email, password=data.password, role=data.role)
        logger.info("user_registered", user_id=str(user.id), role=user.role.value)
        await self.mailer.send_verification(user.id)
        return user

    async def verify_email(self, token: str) -> None:
        user = await self.users.find(await self.email_tokens.verification.consume(token))
        if user is None:
            raise InvalidLinkError("This link is invalid, expired or was already used.")
        await self.users.mark_email_verified(user)
        logger.info("email_verified", user_id=str(user.id))

    async def resend_verification(self, user: User) -> None:
        if not user.is_email_verified:
            await self.mailer.send_verification(user.id)

    async def request_password_reset(self, data: PasswordResetRequest) -> None:
        # The response is the same whether or not the email is registered.
        user = await self.users.find_by_email(data.email)
        if user is not None and user.is_active:
            await self.mailer.send_password_reset(user.id)

    async def reset_password(self, data: PasswordResetConfirm) -> None:
        user = await self.users.find(await self.email_tokens.reset.consume(data.token))
        if user is None or not user.is_active:
            raise InvalidLinkError("This link is invalid, expired or was already used.")
        await self.users.set_password(user, data.new_password)
        # Opening the link proved the user owns the mailbox.
        if not user.is_email_verified:
            await self.users.mark_email_verified(user)
        # Whoever knew the old password may hold a session: end all of them.
        await self.refresh_tokens.revoke_all(user.id)
        logger.info("password_reset", user_id=str(user.id))

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


def get_email_token_stores(redis: RedisDep, settings: SettingsDep) -> EmailTokenStores:
    return EmailTokenStores(
        verification=verification_tokens(redis, settings), reset=reset_tokens(redis, settings)
    )


def get_auth_mailer() -> AuthMailer:
    return CeleryAuthMailer()


def get_auth_service(
    users: UserServiceDep,
    refresh_tokens: Annotated[RefreshTokenStore, Depends(get_refresh_token_store)],
    email_tokens: Annotated[EmailTokenStores, Depends(get_email_token_stores)],
    mailer: Annotated[AuthMailer, Depends(get_auth_mailer)],
    settings: SettingsDep,
) -> AuthService:
    return AuthService(users, refresh_tokens, email_tokens, mailer, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
