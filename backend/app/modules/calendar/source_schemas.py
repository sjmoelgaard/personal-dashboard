from datetime import datetime
from pydantic import BaseModel


class CalendarSourceOut(BaseModel):
    id: int
    name: str
    source_type: str
    ical_url: str | None = None
    color: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarSourceCreate(BaseModel):
    name: str
    ical_url: str
    color: str = "#eab308"


class GoogleConnectRequest(BaseModel):
    session_token: str
    calendar_id: str
    name: str
    color: str = "#3b82f6"
