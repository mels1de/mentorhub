from fastapi import APIRouter

from app.core.pagination import Page, PageQuery
from app.modules.auth.dependencies import AdminUser, CurrentUser
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserServiceDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.get("")
async def list_users(_: AdminUser, users: UserServiceDep, params: PageQuery) -> Page[UserRead]:
    items, total = await users.page(params)
    return Page.create([UserRead.model_validate(u) for u in items], total, params)
