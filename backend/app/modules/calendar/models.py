from datetime import datetime
from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.models import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_calendar_events_start_dt", "start_dt"),
        {"schema": "calendar"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    start_dt: Mapped[datetime]
    end_dt: Mapped[datetime]
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="ical")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
