# Every feature module's models must be imported here, otherwise Alembic autogenerate
# does not see their tables and proposes to drop them.
from app.db.base import Base

__all__ = ["Base"]
