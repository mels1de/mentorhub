from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.core.config import Settings
from app.core.dependencies import SettingsDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import (
    EmailVerificationRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthServiceDep, IssuedTokens
from app.modules.users.schemas import UserRead

REFRESH_COOKIE = "refresh_token"
# The browser sends the cookie only to the auth endpoints, never to the rest of the API.
REFRESH_COOKIE_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE, include_in_schema=False)]


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        # Strict: never sent on cross-site requests, which is our CSRF protection for /refresh.
        samesite="strict",
    )


def _token_response(response: Response, tokens: IssuedTokens, settings: Settings) -> TokenResponse:
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    # Token responses must not be cached by browsers or proxies (RFC 6749 §5.1).
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, auth: AuthServiceDep) -> UserRead:
    user = await auth.register(data)
    return UserRead.model_validate(user)


@router.post("/login")
async def login(
    data: LoginRequest, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> TokenResponse:
    return _token_response(response, await auth.login(data), settings)


@router.post("/refresh")
async def refresh(
    response: Response, auth: AuthServiceDep, settings: SettingsDep, token: RefreshCookie = None
) -> TokenResponse:
    return _token_response(response, await auth.refresh(token), settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, auth: AuthServiceDep, token: RefreshCookie = None) -> None:
    await auth.logout(token)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(response: Response, user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.logout_everywhere(user)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(data: EmailVerificationRequest, auth: AuthServiceDep) -> None:
    await auth.verify_email(data.token)


@router.post("/verify-email/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.resend_verification(user)


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(data: PasswordResetRequest, auth: AuthServiceDep) -> None:
    await auth.request_password_reset(data)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(data: PasswordResetConfirm, auth: AuthServiceDep) -> None:
    await auth.reset_password(data)
