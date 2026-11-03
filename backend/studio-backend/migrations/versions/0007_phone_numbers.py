"""Phone numbers, call direction and number, voicemail message

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_numbers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("number", sa.String(20), nullable=False, unique=True),
        sa.Column("label", sa.String(120), nullable=False, server_default=""),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("dispatch_rule_id", sa.String(60), nullable=False),
        sa.Column("inbound_trunk_id", sa.String(60)),
        sa.Column("outbound_trunk_id", sa.String(60)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "calls",
        sa.Column("direction", sa.String(20), nullable=False, server_default="inbound"),
    )
    op.add_column("calls", sa.Column("remote_number", sa.String(20)))
    op.add_column(
        "agents", sa.Column("voicemail_message", sa.Text(), nullable=False, server_default="")
    )


def downgrade() -> None:
    op.drop_column("agents", "voicemail_message")
    op.drop_column("calls", "remote_number")
    op.drop_column("calls", "direction")
    op.drop_table("phone_numbers")
