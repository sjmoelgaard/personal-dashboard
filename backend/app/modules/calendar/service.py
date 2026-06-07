from datetime import date, datetime, timezone
import httpx
from icalendar import Calendar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.modules.calendar.models import Event


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


async def sync_calendar(db: AsyncSession, ical_url: str) -> int:
    """Fetch iCal, upsert events. Returns number of events synced."""
    raw = await fetch_ical(ical_url)
    events = parse_events(raw)
    if not events:
        return 0

    for event_data in events:
        stmt = (
            insert(Event)
            .values(**event_data)
            .on_conflict_do_update(
                index_elements=["uid"],
                set_={
                    "title": event_data["title"],
                    "start_dt": event_data["start_dt"],
                    "end_dt": event_data["end_dt"],
                    "all_day": event_data["all_day"],
                    "location": event_data["location"],
                    "description": event_data["description"],
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)

    await db.commit()
    return len(events)


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
