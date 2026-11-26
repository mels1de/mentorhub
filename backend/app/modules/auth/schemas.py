from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.models import UserRole

# Upper bound: Argon2 hashes any length, but a megabyte-long "password" is a cheap DoS.
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

type SelfRegistrationRole = Literal[UserRole.MENTEE, UserRole.MENTOR]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    # Admins are created from the CLI, never through the public API.
    role: SelfRegistrationRole = UserRole.MENTEE


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int = Field(description="Access token lifetime in seconds.")
