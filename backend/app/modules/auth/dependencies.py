from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.dependencies import SettingsDep
from app.core.exceptions import PermissionDeniedError
from app.modules.auth.access_tokens import decode_access_token
from app.modules.auth.exceptions import InvalidTokenError
from app.modules.users.models import User, UserRole
from app.modules.users.service import UserServiceDep

# auto_error=False: a missing header becomes our 401 Problem Details, not FastAPI's default.
bearer_scheme = HTTPBearer(auto_error=False, description="Access token from /auth/login")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: UserServiceDep,
    settings: SettingsDep,
) -> User:
    if credentials is None:
        raise InvalidTokenError("Not authenticated.")
    claims = decode_access_token(credentials.credentials, settings)
    # One PK lookup per request: a disabled account or changed role takes effect immediately
    # instead of after the access token expires.
    user = await users.find(claims.user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError("Not authenticated.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    allowed = frozenset(roles)

    async def check_role(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError("You don't have permission to do this.")
        return user

    return check_role


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
