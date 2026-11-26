from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, String, false, true
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    MENTEE = "mentee"
    MENTOR = "mentor"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # VARCHAR + CHECK instead of a native ENUM: adding a role is a plain constraint swap.
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="role",
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        default=UserRole.MENTEE,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_email_verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    last_login_at: Mapped[datetime | None]
