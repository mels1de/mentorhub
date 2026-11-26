"""add 2fa flag to users

Revision ID: 9b0ea0e65889
Revises: 691da670da40
Create Date: 2026-11-26 10:08:10.425874+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9b0ea0e65889"
down_revision: str | Sequence[str] | None = "691da670da40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_2fa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_2fa_enabled")
