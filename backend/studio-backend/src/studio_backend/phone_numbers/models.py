from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from studio_backend.database import Base, new_id, utc_now
from studio_backend.phone_numbers.constants import SIP_TRUNK_PROVIDER


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    label: Mapped[str] = mapped_column(String(120), default="")
    provider: Mapped[str] = mapped_column(String(20))
    # The agent that answers; calls to an unbound number are not answered.
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))
    # LiveKit's side, removed with the number. The dispatch rule carries only this number's id,
    # so binding another agent changes this row, not LiveKit.
    dispatch_rule_id: Mapped[str] = mapped_column(String(60))
    inbound_trunk_id: Mapped[str | None] = mapped_column(String(60))
    outbound_trunk_id: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    @property
    def can_call_out(self) -> bool:
        return self.outbound_trunk_id is not None

    @property
    def can_transfer(self) -> bool:
        return self.provider == SIP_TRUNK_PROVIDER
