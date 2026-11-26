import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams
from app.core.security import hash_password
from app.db.session import SessionDep
from app.modules.users.exceptions import EmailTakenError, UserNotFoundError
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError
        return user

    async def find(self, user_id: uuid.UUID) -> User | None:
        return await self.repo.get(user_id)

    async def find_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def create(self, *, email: str, password: str, role: UserRole) -> User:
        if await self.repo.get_by_email(email) is not None:
            raise EmailTakenError("This email is already registered.")
        user = User(email=email, password_hash=hash_password(password), role=role)
        self.repo.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            # Two registrations with the same email raced past the check above.
            await self.session.rollback()
            raise EmailTakenError("This email is already registered.") from exc
        return user

    async def record_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()

    async def replace_password_hash(self, user: User, password_hash: str) -> None:
        """Store a re-hash of the same password (stronger parameters), not a new password."""
        user.password_hash = password_hash
        await self.session.commit()

    async def set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        await self.session.commit()

    async def mark_email_verified(self, user: User) -> None:
        user.is_email_verified = True
        await self.session.commit()

    async def set_2fa(self, user: User, *, enabled: bool) -> None:
        user.is_2fa_enabled = enabled
        await self.session.commit()

    async def page(self, params: PageParams) -> tuple[list[User], int]:
        return await self.repo.page(params)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
