from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from studio_backend.agents.constants import DRAFT_STATUS
from studio_backend.core.database import Base, new_id, utc_now
from studio_backend.knowledge.models import KnowledgeBase

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
    # Left on an answering machine when an outgoing call reaches one; empty: hang up instead.
    voicemail_message: Mapped[str] = mapped_column(Text, default="")
    llm_model: Mapped[str] = mapped_column(String(120))
    languages: Mapped[list[str]] = mapped_column(JSON)
    # Per language: {"stt_model": ..., "tts_model": ..., "voice": ...}
    language_settings: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default=DRAFT_STATUS)
    # Post-call analysis: [{"name", "type", "description", "choices"}] and a success rule.
    analysis_fields: Mapped[list[dict]] = mapped_column(JSON, default=list)
    success_rule: Mapped[str] = mapped_column(Text, default="")
    # Where each call's result goes: [{"id", "kind", "event", "url", "secret", ...}].
    after_call_actions: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # The flow being edited, and the one phone calls run (None: a prompt-only agent).
    flow: Mapped[dict | None] = mapped_column(JSON)
    published_flow: Mapped[dict | None] = mapped_column(JSON)
    published_flow_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    # selectin: loaded with the agent, since async sessions cannot lazy-load later.
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(
        secondary=agent_knowledge_bases, lazy="selectin"
    )

    @property
    def has_flow(self) -> bool:
        return self.flow is not None

    @property
    def knowledge_base_ids(self) -> list[str]:
        return [knowledge_base.id for knowledge_base in self.knowledge_bases]
