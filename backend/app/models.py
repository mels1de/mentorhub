# Every feature module's models must be imported here, otherwise Alembic autogenerate
# does not see their tables and proposes to drop them.
from app.db.base import Base
from app.modules.users.models import User

__all__ = ["Base", "User"]
