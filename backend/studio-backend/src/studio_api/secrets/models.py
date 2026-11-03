from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from studio_api.database import Base, new_id, utc_now


class Secret(Base):
    """An API key or token a tool or after-call action sends; stored encrypted."""

    __tablename__ = "secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    encrypted_value: Mapped[str] = mapped_column(Text)
    # What the console shows instead of the value, e.g. "cal_…c33d".
    preview: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
