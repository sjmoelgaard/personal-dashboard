"""Unit tests for google_service pure/synchronous helper functions."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.modules.calendar.google_service import (
    _event_data_to_google_body,
    _normalize_google_event,
)


def test_normalize_google_event_timed():
    item = {
        "id": "abc123",
        "summary": "Team meeting",
        "start": {"dateTime": "2026-06-10T10:00:00+02:00"},
        "end": {"dateTime": "2026-06-10T11:00:00+02:00"},
        "location": "Office",
        "description": "Weekly sync",
        "colorId": "5",
    }
    result = _normalize_google_event(item)
    assert result["uid"] == "google_abc123"
    assert result["google_event_id"] == "abc123"
    assert result["title"] == "Team meeting"
    assert result["all_day"] is False
    assert result["location"] == "Office"
    assert result["description"] == "Weekly sync"
    assert result["google_color_id"] == "5"
    assert result["start_dt"].tzinfo is not None


def test_normalize_google_event_all_day():
    item = {
        "id": "day1",
        "summary": "Holiday",
        "start": {"date": "2026-12-25"},
        "end": {"date": "2026-12-26"},
    }
    result = _normalize_google_event(item)
    assert result["all_day"] is True
    assert result["uid"] == "google_day1"
    assert result["google_color_id"] is None


def test_normalize_google_event_missing_summary():
    item = {
        "id": "no_title",
        "start": {"dateTime": "2026-06-10T10:00:00Z"},
        "end": {"dateTime": "2026-06-10T11:00:00Z"},
    }
    result = _normalize_google_event(item)
    assert result["title"] == "Ingen titel"


def test_event_data_to_google_body_timed():
    data = {
        "title": "Lunch",
        "start_dt": datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
        "end_dt": datetime(2026, 6, 10, 13, 0, tzinfo=timezone.utc),
        "all_day": False,
        "location": "Canteen",
        "description": None,
        "reminder_minutes": 30,
        "google_color_id": "3",
    }
    body = _event_data_to_google_body(data)
    assert body["summary"] == "Lunch"
    assert "dateTime" in body["start"]
    assert body["location"] == "Canteen"
    assert body["colorId"] == "3"
    assert body["reminders"]["useDefault"] is False
    assert body["reminders"]["overrides"][0]["minutes"] == 30


def test_event_data_to_google_body_all_day():
    data = {
        "title": "Ferie",
        "start_dt": datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
        "end_dt": datetime(2026, 7, 8, 0, 0, tzinfo=timezone.utc),
        "all_day": True,
        "location": None,
        "description": None,
        "reminder_minutes": None,
        "google_color_id": None,
    }
    body = _event_data_to_google_body(data)
    assert body["start"] == {"date": "2026-07-01"}
    assert body["end"] == {"date": "2026-07-08"}
    assert body["reminders"]["useDefault"] is True
    assert "colorId" not in body


def test_event_data_to_google_body_no_reminder():
    data = {
        "title": "X",
        "start_dt": datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        "end_dt": datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        "all_day": False,
        "location": None,
        "description": None,
        "reminder_minutes": None,
        "google_color_id": None,
    }
    body = _event_data_to_google_body(data)
    assert body["reminders"]["useDefault"] is True


def test_normalize_google_event_with_reminder():
    item = {
        "id": "remind1",
        "summary": "Meeting with reminder",
        "start": {"dateTime": "2026-06-10T14:00:00Z"},
        "end": {"dateTime": "2026-06-10T15:00:00Z"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 15}],
        },
    }
    result = _normalize_google_event(item)
    assert result["reminder_minutes"] == 15
