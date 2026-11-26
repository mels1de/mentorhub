from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.core.config import Settings
from app.core.dependencies import SettingsDep
from app.core.rate_limit import rate_limit
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import (
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    OtpChallengeResponse,
    OtpResendRequest,
    OtpVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    TwoFactorToggleRequest,
)
from app.modules.auth.service import AuthServiceDep, IssuedTokens, OtpChallenge
from app.modules.users.schemas import UserRead

REFRESH_COOKIE = "refresh_token"
# The browser sends the cookie only to the auth endpoints, never to the rest of the API.
REFRESH_COOKIE_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])

MINUTE = timedelta(minutes=1)
# Per client IP. Generous enough for a shared office NAT, tight enough to stop scripted guessing.
LIMIT_REGISTER = Depends(rate_limit("register", limit=5, window=10 * MINUTE))
LIMIT_LOGIN = Depends(rate_limit("login", limit=10, window=MINUTE))
LIMIT_OTP = Depends(rate_limit("otp", limit=10, window=MINUTE))
LIMIT_REFRESH = Depends(rate_limit("refresh", limit=30, window=MINUTE))
LIMIT_EMAIL = Depends(rate_limit("email", limit=5, window=15 * MINUTE))

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


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[LIMIT_REGISTER])
async def register(data: RegisterRequest, auth: AuthServiceDep) -> UserRead:
    user = await auth.register(data)
    return UserRead.model_validate(user)


@router.post("/login", dependencies=[LIMIT_LOGIN])
async def login(
    data: LoginRequest, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> LoginResponse:
    result = await auth.login(data)
    if isinstance(result, OtpChallenge):
        return OtpChallengeResponse(challenge_id=result.challenge_id, expires_in=result.expires_in)
    return _token_response(response, result, settings)


@router.post("/2fa/verify", dependencies=[LIMIT_OTP])
async def verify_otp(
    data: OtpVerifyRequest, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> TokenResponse:
    return _token_response(response, await auth.verify_otp(data), settings)


@router.post("/2fa/resend", status_code=status.HTTP_202_ACCEPTED, dependencies=[LIMIT_OTP])
async def resend_otp(data: OtpResendRequest, auth: AuthServiceDep) -> None:
    await auth.resend_otp(data)


@router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_2fa(data: TwoFactorToggleRequest, user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.set_2fa(user, data, enabled=True)


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_2fa(
    data: TwoFactorToggleRequest, user: CurrentUser, auth: AuthServiceDep
) -> None:
    await auth.set_2fa(user, data, enabled=False)


@router.post("/refresh", dependencies=[LIMIT_REFRESH])
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


@router.post(
    "/verify-email/resend", status_code=status.HTTP_202_ACCEPTED, dependencies=[LIMIT_EMAIL]
)
async def resend_verification(user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.resend_verification(user)


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED, dependencies=[LIMIT_EMAIL])
async def request_password_reset(data: PasswordResetRequest, auth: AuthServiceDep) -> None:
    await auth.request_password_reset(data)


@router.post(
    "/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT, dependencies=[LIMIT_OTP]
)
async def confirm_password_reset(data: PasswordResetConfirm, auth: AuthServiceDep) -> None:
    await auth.reset_password(data)
