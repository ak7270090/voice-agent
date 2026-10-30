from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from studio_api.agents.constants import DRAFT_STATUS
from studio_api.database import Base, new_id, utc_now


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
