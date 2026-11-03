"""Interruption count on calls

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calls", sa.Column("interruptions", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("calls", "interruptions")
