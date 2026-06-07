from datetime import datetime
from pydantic import BaseModel


class CalendarSourceOut(BaseModel):
    id: int
    name: str
    ical_url: str
    color: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarSourceCreate(BaseModel):
    name: str
    ical_url: str
    color: str = "#eab308"
