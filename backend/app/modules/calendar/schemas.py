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

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
