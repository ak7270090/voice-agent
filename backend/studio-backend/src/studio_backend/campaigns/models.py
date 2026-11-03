from datetime import datetime, time

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from studio_backend.campaigns.constants import DRAFT, PENDING
from studio_backend.database import Base, new_id, utc_now


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    # The number calls come from; it needs an outbound trunk.
    from_number_id: Mapped[str] = mapped_column(ForeignKey("phone_numbers.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default=DRAFT)
    # Calls start only inside this daily window, in the campaign's time zone.
    window_start: Mapped[time] = mapped_column(Time)
    window_end: Mapped[time] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(60))
    max_concurrent: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer)
    retry_after_minutes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    phone: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120), default="")
    # Passed into the agent's greeting and flow, e.g. {"appointment_time": "4 pm"}.
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=PENDING)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(60))
    last_room: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
