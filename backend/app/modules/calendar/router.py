from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

import google.auth.exceptions

from app.core.auth import require_auth
from app.core.database import get_db
from app.modules.calendar.models import Event
from app.modules.calendar.schemas import EventCreate, EventOut, EventUpdate
from app.modules.calendar.source_models import CalendarSource
from app.modules.calendar.service import (
    get_events_in_range,
    get_upcoming_events,
    sync_all_sources,
)
from app.modules.calendar import google_service

router = APIRouter()


async def _enrich_with_colors(
    events: list, db: AsyncSession
) -> list[EventOut]:
    """Tilknyt source_color og editable til hvert event via en enkelt DB-forespørgsel."""
    source_ids = {e.source_id for e in events if e.source_id is not None}
    color_map: dict[int, str] = {}
    if source_ids:
        result = await db.execute(
            select(CalendarSource).where(CalendarSource.id.in_(source_ids))
        )
        color_map = {s.id: s.color for s in result.scalars()}
    return [
        EventOut.model_validate(e).model_copy(
            update={
                "source_color": color_map.get(e.source_id),
                "editable": e.google_event_id is not None,
            }
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


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    # Look up the source to get credentials and calendar_id
    result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == body.source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kalender-kilde ikke fundet")
    if source.source_type != "google":
        raise HTTPException(
            status_code=409,
            detail="Aftalen kan kun oprettes i Google Calendar-kilder",
        )

    event_data = body.model_dump()

    # Create in Google Calendar first
    try:
        google_event_id = await google_service.create_google_event(
            source.google_credentials, source.google_calendar_id, event_data
        )
    except google.auth.exceptions.RefreshError:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar-forbindelsen er udløbet — tilslut igen",
        )

    # Insert into local DB
    uid = f"google_{google_event_id}"
    new_event = Event(
        uid=uid,
        title=body.title,
        start_dt=body.start_dt,
        end_dt=body.end_dt,
        all_day=body.all_day,
        location=body.location,
        description=body.description,
        source="google",
        source_id=body.source_id,
        google_event_id=google_event_id,
        google_color_id=body.google_color_id,
        reminder_minutes=body.reminder_minutes,
    )
    db.add(new_event)
    try:
        await db.commit()
        await db.refresh(new_event)
    except Exception:
        # Best-effort: delete from Google to avoid orphan
        try:
            await google_service.delete_google_event(
                source.google_credentials, source.google_calendar_id, google_event_id
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Fejl ved gemning i database")

    enriched = await _enrich_with_colors([new_event], db)
    return enriched[0]


@router.put("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    body: EventUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Aftale ikke fundet")
    if not event.google_event_id:
        raise HTTPException(
            status_code=409,
            detail="Aftalen kan ikke redigeres (importeret fra iCal)",
        )

    # Look up source for credentials
    source_result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == event.source_id)
    )
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kalender-kilde ikke fundet")

    # Build merged event_data for Google
    event_data = {
        "title": body.title if body.title is not None else event.title,
        "start_dt": body.start_dt if body.start_dt is not None else event.start_dt,
        "end_dt": body.end_dt if body.end_dt is not None else event.end_dt,
        "all_day": body.all_day if body.all_day is not None else event.all_day,
        "location": body.location if body.location is not None else event.location,
        "description": body.description if body.description is not None else event.description,
        "reminder_minutes": body.reminder_minutes if body.reminder_minutes is not None else event.reminder_minutes,
        "google_color_id": body.google_color_id if body.google_color_id is not None else event.google_color_id,
    }

    try:
        await google_service.update_google_event(
            source.google_credentials,
            source.google_calendar_id,
            event.google_event_id,
            event_data,
        )
    except google.auth.exceptions.RefreshError:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar-forbindelsen er udløbet — tilslut igen",
        )

    # Update local DB
    for field, value in event_data.items():
        setattr(event, field, value)
    event.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(event)

    enriched = await _enrich_with_colors([event], db)
    return enriched[0]


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Aftale ikke fundet")
    if not event.google_event_id:
        raise HTTPException(
            status_code=409,
            detail="Aftalen kan ikke slettes (importeret fra iCal)",
        )

    source_result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == event.source_id)
    )
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kalender-kilde ikke fundet")

    try:
        await google_service.delete_google_event(
            source.google_credentials,
            source.google_calendar_id,
            event.google_event_id,
        )
    except google.auth.exceptions.RefreshError:
        raise HTTPException(
            status_code=401,
            detail="Google Calendar-forbindelsen er udløbet — tilslut igen",
        )

    await db.delete(event)
    await db.commit()


@router.post("/sync")
async def sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    count = await sync_all_sources(db)
    return {"synced": count}
