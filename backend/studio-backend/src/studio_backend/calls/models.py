from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from studio_backend.calls.constants import ACTIVE_STATUS, INBOUND_DIRECTION
from studio_backend.database import Base, new_id, utc_now


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    room_name: Mapped[str] = mapped_column(String(120), unique=True)
    channel: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(20), default=INBOUND_DIRECTION)
    # Phone calls: the caller's number (inbound) or the number dialled (outbound).
    remote_number: Mapped[str | None] = mapped_column(String(20))
    # Campaign calls: the contact whose attempt this was.
    campaign_contact_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaign_contacts.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default=ACTIVE_STATUS)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # [{"role": "user" | "assistant", "text": ...}]
    transcript: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # Flow calls: how it ended, what was collected, and the node ids passed through.
    outcome: Mapped[str | None] = mapped_column(String(60))
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    flow_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Per agent reply, milliseconds per stage (e2e_latency = caller stops -> agent's first audio).
    turn_latency_ms: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # Agent replies the caller talked over.
    interruptions: Mapped[int] = mapped_column(Integer, default=0)
    # LiveKit's id of the room session: the link to its recording in LiveKit Cloud.
    room_sid: Mapped[str | None] = mapped_column(String(40))
    # Tokens, speech-to-text seconds, characters spoken; and the cost in dollars per part.
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    cost: Mapped[dict] = mapped_column(JSON, default=dict)
    # [{"name", "by", "at", "ms", "ok", "unavailable", "result"}]
    tool_calls: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # Post-call analysis: pending, done, skipped (the caller never spoke) or failed.
    analysis_status: Mapped[str | None] = mapped_column(String(20))
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
