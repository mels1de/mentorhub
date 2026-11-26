from app.core.exceptions import AuthenticationError, PermissionDeniedError


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"


class InvalidTokenError(AuthenticationError):
    code = "invalid_token"


class RefreshTokenReusedError(AuthenticationError):
    code = "refresh_token_reused"


class AccountDisabledError(PermissionDeniedError):
    code = "account_disabled"
