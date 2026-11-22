"""enable postgres extensions

Revision ID: f8dfd98ca458
Revises:
Create Date: 2026-11-15 09:06:45.475795+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f8dfd98ca458"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXTENSIONS = ("citext", "pg_trgm", "vector", "postgis")


def upgrade() -> None:
    for name in EXTENSIONS:
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {name}")


def downgrade() -> None:
    for name in reversed(EXTENSIONS):
        op.execute(f"DROP EXTENSION IF EXISTS {name}")
