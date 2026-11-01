"""Call usage, cost, tool calls, LiveKit room and post-call analysis; agents' analysis settings

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

JSON_COLUMNS = ("usage", "cost", "tool_calls", "analysis")


def upgrade() -> None:
    op.add_column("calls", sa.Column("room_sid", sa.String(40)))
    for name in JSON_COLUMNS:
        empty = "[]" if name == "tool_calls" else "{}"
        op.add_column("calls", sa.Column(name, sa.JSON(), nullable=False, server_default=empty))
    op.add_column("calls", sa.Column("analysis_status", sa.String(20)))
    op.add_column(
        "agents", sa.Column("analysis_fields", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column("agents", sa.Column("success_rule", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("agents", "success_rule")
    op.drop_column("agents", "analysis_fields")
    op.drop_column("calls", "analysis_status")
    for name in reversed(JSON_COLUMNS):
        op.drop_column("calls", name)
    op.drop_column("calls", "room_sid")
