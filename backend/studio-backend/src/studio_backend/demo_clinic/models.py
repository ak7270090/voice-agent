from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from studio_backend.database import Base, new_id, utc_now


class DemoAppointment(Base):
    __tablename__ = "demo_appointments"
    # One booking per doctor and slot, enforced by the database (not just by a check first).
    __table_args__ = (UniqueConstraint("doctor_id", "day", "time"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_number: Mapped[int] = mapped_column(Integer, unique=True)
    patient_name: Mapped[str] = mapped_column(String(120))
    patient_age: Mapped[int] = mapped_column(Integer)
    doctor_id: Mapped[str] = mapped_column(String(40))
    day: Mapped[date] = mapped_column(Date)
    time: Mapped[str] = mapped_column(String(5))
    # Sent by the caller of the API: the same key again returns this booking instead of a second.
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
