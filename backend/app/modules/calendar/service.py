import logging
from datetime import date, datetime, timezone, timedelta
import httpx
from icalendar import Calendar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

import google.auth.exceptions

from app.modules.calendar.models import Event
from app.modules.calendar.source_models import CalendarSource
from app.modules.calendar import google_service

logger = logging.getLogger(__name__)


async def fetch_ical(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
        return r.content


def parse_events(ical_bytes: bytes) -> list[dict]:
    cal = Calendar.from_ical(ical_bytes)
    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        uid = str(component.get("UID", ""))
        if not uid:
            continue
        title = str(component.get("SUMMARY", "Ingen titel"))
        dtstart = component.get("DTSTART").dt
        dtend_raw = component.get("DTEND") or component.get("DTSTART")
        dtend = dtend_raw.dt

        all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

        if all_day:
            start_dt = datetime(dtstart.year, dtstart.month, dtstart.day, tzinfo=timezone.utc)
            end_dt = datetime(dtend.year, dtend.month, dtend.day, tzinfo=timezone.utc)
        else:
            start_dt = dtstart.replace(tzinfo=timezone.utc) if dtstart.tzinfo is None else dtstart.astimezone(timezone.utc)
            end_dt = dtend.replace(tzinfo=timezone.utc) if dtend.tzinfo is None else dtend.astimezone(timezone.utc)

        location = str(component.get("LOCATION", "")).strip() or None
        description = str(component.get("DESCRIPTION", "")).strip() or None

        events.append({
            "uid": uid,
            "title": title,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "all_day": all_day,
            "location": location,
            "description": description,
            "source": "ical",
        })
    return events


async def sync_calendar(
    db: AsyncSession, ical_url: str, source_id: int | None = None
) -> int:
    """Fetch iCal, upsert events med source_id. Returns antal synkroniserede events."""
    raw = await fetch_ical(ical_url)
    events = parse_events(raw)
    if not events:
        return 0

    for event_data in events:
        data = {**event_data, "source_id": source_id}
        stmt = (
            insert(Event)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["uid"],
                set_={
                    "title": data["title"],
                    "start_dt": data["start_dt"],
                    "end_dt": data["end_dt"],
                    "all_day": data["all_day"],
                    "location": data["location"],
                    "description": data["description"],
                    "source_id": source_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)

    await db.commit()
    return len(events)


async def sync_google_source(db: AsyncSession, source: CalendarSource) -> int:
    """Fetch from Google Calendar API, upsert events. Returns antal synkroniserede events."""
    if not source.google_credentials or not source.google_calendar_id:
        logger.warning(f"Google source '{source.name}' mangler credentials eller calendar_id")
        return 0

    # Refresh credentials if needed and persist updated token
    try:
        updated_creds = await google_service.refresh_credentials_if_needed(source.google_credentials)
    except google.auth.exceptions.RefreshError:
        logger.error(f"Google token udløbet for '{source.name}' — tilslut igen")
        return 0

    if updated_creds != source.google_credentials:
        source.google_credentials = updated_creds
        await db.commit()

    now = datetime.now(timezone.utc)
    from_dt = now - timedelta(days=90)
    to_dt = now + timedelta(days=90)

    events = await google_service.fetch_google_events(
        updated_creds, source.google_calendar_id, from_dt, to_dt
    )

    for event_data in events:
        data = {
            **event_data,
            "source_id": source.id,
        }
        stmt = (
            insert(Event)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["uid"],
                set_={
                    "title": data["title"],
                    "start_dt": data["start_dt"],
                    "end_dt": data["end_dt"],
                    "all_day": data["all_day"],
                    "location": data["location"],
                    "description": data["description"],
                    "google_color_id": data.get("google_color_id"),
                    "reminder_minutes": data.get("reminder_minutes"),
                    "source_id": source.id,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)

    await db.commit()
    return len(events)


async def sync_source(db: AsyncSession, source_id: int) -> int:
    """Synkroniser én kilde fra DB."""
    result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise ValueError(f"CalendarSource {source_id} ikke fundet")

    if source.source_type == "google":
        return await sync_google_source(db, source)
    return await sync_calendar(db, source.ical_url, source.id)


async def sync_all_sources(db: AsyncSession) -> int:
    """Synkroniser alle aktive kalender-kilder. Returns total antal events."""
    result = await db.execute(
        select(CalendarSource).where(CalendarSource.is_active == True)  # noqa: E712
    )
    sources = list(result.scalars().all())
    total = 0
    for source in sources:
        try:
            if source.source_type == "google":
                count = await sync_google_source(db, source)
            else:
                count = await sync_calendar(db, source.ical_url, source.id)
            total += count
            logger.info(f"Synkroniseret {count} events fra '{source.name}'")
        except Exception as e:
            logger.error(f"Sync fejlede for '{source.name}': {e}")
    return total


async def get_upcoming_events(db: AsyncSession, limit: int = 10) -> list[Event]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Event)
        .where(Event.end_dt >= now)
        .order_by(Event.start_dt)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_events_in_range(
    db: AsyncSession, from_dt: datetime, to_dt: datetime
) -> list[Event]:
    result = await db.execute(
        select(Event)
        .where(Event.start_dt >= from_dt, Event.start_dt <= to_dt)
        .order_by(Event.start_dt)
    )
    return list(result.scalars().all())
