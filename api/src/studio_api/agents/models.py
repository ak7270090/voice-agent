from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_api.agents.constants import DRAFT_STATUS
from studio_api.database import Base, new_id, utc_now
from studio_api.knowledge.models import KnowledgeBase

agent_knowledge_bases = Table(
    "agent_knowledge_bases",
    Base.metadata,
    Column("agent_id", ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "knowledge_base_id", ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    template: Mapped[str | None] = mapped_column(String(60))
    instructions: Mapped[str] = mapped_column(Text)
    greeting: Mapped[str] = mapped_column(Text)
    llm_model: Mapped[str] = mapped_column(String(120))
    languages: Mapped[list[str]] = mapped_column(JSON)
    # Per language: {"stt_model": ..., "tts_model": ..., "voice": ...}
    language_settings: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default=DRAFT_STATUS)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    # selectin: loaded with the agent, since async sessions cannot lazy-load later.
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(
        secondary=agent_knowledge_bases, lazy="selectin"
    )

    @property
    def knowledge_base_ids(self) -> list[str]:
        return [knowledge_base.id for knowledge_base in self.knowledge_bases]
