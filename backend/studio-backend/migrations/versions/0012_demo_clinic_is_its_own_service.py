"""The demo clinic is its own service: drop its table and point saved flows at its new address

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

OLD_URL = "http://api:8000/demo-clinic"
NEW_URL = "http://demo-clinic:8100"
FLOW_COLUMNS = (("agents", "flow"), ("agents", "published_flow"), ("flow_versions", "flow"))


def replace_clinic_url(old: str, new: str) -> None:
    for table, column in FLOW_COLUMNS:
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = replace({column}::text, :old, :new)::json "
                f"WHERE {column}::text LIKE :match"
            ).bindparams(old=old, new=new, match=f"%{old}%")
        )


def upgrade() -> None:
    replace_clinic_url(OLD_URL, NEW_URL)
    op.drop_table("demo_appointments")


def downgrade() -> None:
    op.create_table(
        "demo_appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("booking_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("patient_name", sa.String(120), nullable=False),
        sa.Column("patient_age", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.String(40), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("time", sa.String(5), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("doctor_id", "day", "time"),
    )
    replace_clinic_url(NEW_URL, OLD_URL)
