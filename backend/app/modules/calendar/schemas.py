from datetime import datetime
from pydantic import BaseModel


class EventOut(BaseModel):
    id: int
    uid: str
    title: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool
    location: str | None
    description: str | None
    source: str
    source_id: int | None = None
    source_color: str | None = None
    google_event_id: str | None = None
    google_color_id: str | None = None
    reminder_minutes: int | None = None
    editable: bool = False

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None
    google_color_id: str | None = None
    source_id: int


class EventUpdate(BaseModel):
    title: str | None = None
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None
    google_color_id: str | None = None
