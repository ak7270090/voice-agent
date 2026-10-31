"""Idempotency key on demo clinic bookings

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("demo_appointments", sa.Column("idempotency_key", sa.String(200), nullable=True))
    op.create_unique_constraint(
        "uq_demo_appointments_idempotency_key", "demo_appointments", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_demo_appointments_idempotency_key", "demo_appointments")
    op.drop_column("demo_appointments", "idempotency_key")
