from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from studio_backend.database import Base, new_id, utc_now


class FlowVersion(Base):
    """A published flow, kept so a call can be traced to the exact flow it ran."""

    __tablename__ = "flow_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    flow: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    @property
    def node_count(self) -> int:
        return len(self.flow.get("nodes", []))
