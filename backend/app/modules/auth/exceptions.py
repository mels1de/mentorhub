from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    PermissionDeniedError,
    TooManyRequestsError,
)


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"


class InvalidTokenError(AuthenticationError):
    code = "invalid_token"


class RefreshTokenReusedError(AuthenticationError):
    code = "refresh_token_reused"


class AccountDisabledError(PermissionDeniedError):
    code = "account_disabled"


class InvalidLinkError(BusinessRuleError):
    code = "invalid_link"


class InvalidOtpError(AuthenticationError):
    code = "invalid_otp"


class OtpLockedError(TooManyRequestsError):
    code = "otp_locked"


class EmailNotVerifiedError(BusinessRuleError):
    code = "email_not_verified"
