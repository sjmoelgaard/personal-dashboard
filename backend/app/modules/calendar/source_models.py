from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.models import Base


class CalendarSource(Base):
    __tablename__ = "calendar_sources"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    ical_url: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(7), default="#eab308")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
