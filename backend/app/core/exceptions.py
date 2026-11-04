from collections.abc import Mapping
from typing import ClassVar


class AppError(Exception):
    """Base domain error. Services raise these; the API layer renders them as
    RFC 9457 Problem Details. Feature modules subclass the generic errors below
    and set their own `code`."""

    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "internal_error"
    title: ClassVar[str] = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        extensions: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.extensions = dict(extensions or {})
        self.headers = dict(headers or {})


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    title = "Not Found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    title = "Conflict"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    title = "Forbidden"


class AuthenticationError(AppError):
    status_code = 401
    code = "not_authenticated"
    title = "Unauthorized"

    def __init__(
        self,
        detail: str | None = None,
        *,
        extensions: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        # RFC 9110 §15.5.2: a 401 response must carry WWW-Authenticate.
        super().__init__(
            detail,
            extensions=extensions,
            headers={"WWW-Authenticate": "Bearer", **(headers or {})},
        )


class BusinessRuleError(AppError):
    """Valid input that breaks a domain rule (e.g. reviewing a booking that isn't completed)."""

    status_code = 422
    code = "business_rule_violation"
    title = "Unprocessable Content"
