from app.core.exceptions import ConflictError, NotFoundError


class EmailTakenError(ConflictError):
    code = "email_taken"


class UserNotFoundError(NotFoundError):
    code = "user_not_found"
