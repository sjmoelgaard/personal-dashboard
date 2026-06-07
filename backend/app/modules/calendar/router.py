from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_auth
from app.core.database import get_db
from app.modules.calendar.schemas import EventOut
from app.modules.calendar.service import (
    get_events_in_range,
    get_upcoming_events,
    sync_all_sources,
)

router = APIRouter()


@router.get("/events", response_model=list[EventOut])
async def list_events(
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    upcoming: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    if upcoming:
        return await get_upcoming_events(db, limit=limit)
    if from_dt and to_dt:
        return await get_events_in_range(db, from_dt, to_dt)
    # Default: upcoming events
    return await get_upcoming_events(db, limit=limit)


@router.post("/sync")
async def sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    count = await sync_all_sources(db)
    return {"synced": count}
