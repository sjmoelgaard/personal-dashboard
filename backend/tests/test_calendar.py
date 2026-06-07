import pytest
from datetime import datetime, timezone


MINIMAL_ICAL = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-1@test
DTSTART:20260615T100000Z
DTEND:20260615T110000Z
SUMMARY:Møde med Peter
LOCATION:Kontoret
END:VEVENT
BEGIN:VEVENT
UID:test-event-2@test
DTSTART;VALUE=DATE:20260616
DTEND;VALUE=DATE:20260617
SUMMARY:Fridag
END:VEVENT
END:VCALENDAR""".encode("utf-8")


def test_parse_events_returns_correct_count():
    from app.modules.calendar.service import parse_events
    events = parse_events(MINIMAL_ICAL)
    assert len(events) == 2


def test_parse_events_extracts_fields():
    from app.modules.calendar.service import parse_events
    events = parse_events(MINIMAL_ICAL)
    meeting = next(e for e in events if e["uid"] == "test-event-1@test")
    assert meeting["title"] == "Møde med Peter"
    assert meeting["location"] == "Kontoret"
    assert meeting["all_day"] is False
    assert meeting["start_dt"].tzinfo is not None


def test_parse_events_handles_all_day():
    from app.modules.calendar.service import parse_events
    events = parse_events(MINIMAL_ICAL)
    allday = next(e for e in events if e["uid"] == "test-event-2@test")
    assert allday["all_day"] is True
    assert allday["title"] == "Fridag"


def test_parse_events_normalizes_to_utc():
    from app.modules.calendar.service import parse_events
    events = parse_events(MINIMAL_ICAL)
    for event in events:
        assert event["start_dt"].tzinfo == timezone.utc
