from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_auth
from app.core.database import get_db
from app.modules.calendar.schemas import EventOut
from app.modules.calendar.source_models import CalendarSource
from app.modules.calendar.service import (
    get_events_in_range,
    get_upcoming_events,
    sync_all_sources,
)

router = APIRouter()


async def _enrich_with_colors(
    events: list, db: AsyncSession
) -> list[EventOut]:
    """Tilknyt source_color til hvert event via en enkelt DB-forespørgsel."""
    source_ids = {e.source_id for e in events if e.source_id is not None}
    color_map: dict[int, str] = {}
    if source_ids:
        result = await db.execute(
            select(CalendarSource).where(CalendarSource.id.in_(source_ids))
        )
        color_map = {s.id: s.color for s in result.scalars()}
    return [
        EventOut.model_validate(e).model_copy(
            update={"source_color": color_map.get(e.source_id)}
        )
        for e in events
    ]


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
        events = await get_upcoming_events(db, limit=limit)
    elif from_dt and to_dt:
        events = await get_events_in_range(db, from_dt, to_dt)
    else:
        events = await get_upcoming_events(db, limit=limit)
    return await _enrich_with_colors(events, db)


@router.post("/sync")
async def sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    count = await sync_all_sources(db)
    return {"synced": count}
