import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams
from app.db.pagination import paginate_offset
from app.modules.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # citext column: the comparison is case-insensitive in the database.
        return await self.session.scalar(select(User).where(User.email == email))

    def add(self, user: User) -> None:
        self.session.add(user)

    async def page(self, params: PageParams) -> tuple[list[User], int]:
        stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
        return await paginate_offset(self.session, stmt, params)
