"""Flows on agents, published flow versions, call outcomes, and the demo clinic's bookings

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("flow", sa.JSON()))
    op.add_column("agents", sa.Column("published_flow", sa.JSON()))
    op.add_column("agents", sa.Column("published_flow_version", sa.Integer()))
    op.create_table(
        "flow_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(36),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("flow", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_id", "version"),
    )
    op.create_index("ix_flow_versions_agent_id", "flow_versions", ["agent_id"])
    op.add_column("calls", sa.Column("outcome", sa.String(60)))
    op.add_column("calls", sa.Column("fields", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("calls", sa.Column("flow_path", sa.JSON(), nullable=False, server_default="[]"))
    op.create_table(
        "demo_appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("booking_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("patient_name", sa.String(120), nullable=False),
        sa.Column("patient_age", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.String(40), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("time", sa.String(5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("doctor_id", "day", "time"),
    )


def downgrade() -> None:
    op.drop_table("demo_appointments")
    op.drop_column("calls", "flow_path")
    op.drop_column("calls", "fields")
    op.drop_column("calls", "outcome")
    op.drop_index("ix_flow_versions_agent_id", table_name="flow_versions")
    op.drop_table("flow_versions")
    op.drop_column("agents", "published_flow_version")
    op.drop_column("agents", "published_flow")
    op.drop_column("agents", "flow")
