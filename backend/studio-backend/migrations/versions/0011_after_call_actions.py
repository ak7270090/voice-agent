"""After-call actions per agent, and their deliveries per call

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents", sa.Column("after_call_actions", sa.JSON(), nullable=False, server_default="[]")
    )
    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "call_id",
            sa.String(36),
            sa.ForeignKey("calls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("event", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("deliveries")
    op.drop_column("agents", "after_call_actions")
