# Google Calendar Two-Way Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace read-only iCal sync with full Google Calendar API integration — create, edit, and delete events from the dashboard with real-time write-back to Google Calendar.

**Architecture:** OAuth2 flow stores credentials in DB; `google_service.py` wraps all Google API calls with `asyncio.to_thread`; `sync_source` branches on `source_type`; three new CRUD endpoints; EventForm frontend component for create/edit.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, google-api-python-client, google-auth-oauthlib, React 18, TypeScript, Tailwind CSS 3, PostgreSQL 16 with JSONB

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/requirements.txt` | Modify | Add 3 Google packages |
| `backend/app/core/config.py` | Modify | Add google_client_id/secret/redirect_uri settings |
| `backend/app/modules/calendar/source_models.py` | Modify | Add source_type, google_calendar_id, google_credentials; ical_url nullable |
| `backend/app/modules/calendar/models.py` | Modify | Add google_event_id, google_color_id, reminder_minutes |
| `backend/app/modules/calendar/google_session_models.py` | Create | GoogleOAuthSession temp table |
| `backend/app/core/models.py` | Modify | Import google_session_models for Alembic |
| `backend/alembic/versions/0004_google_calendar.py` | Create | Migration for all new columns + new table |
| `backend/app/modules/calendar/google_service.py` | Create | All Google API logic |
| `backend/app/modules/calendar/schemas.py` | Modify | EventOut new fields; add EventCreate, EventUpdate |
| `backend/app/modules/calendar/source_schemas.py` | Modify | CalendarSourceOut optional ical_url; add GoogleConnectRequest |
| `backend/app/modules/calendar/service.py` | Modify | sync_source branches on source_type; new sync_google_source |
| `backend/app/modules/calendar/admin_router.py` | Modify | Add 4 Google OAuth endpoints |
| `backend/app/modules/calendar/router.py` | Modify | Add editable field; add POST/PUT/DELETE /events endpoints |
| `backend/tests/calendar/test_google_service.py` | Create | Unit tests for google_service pure functions |
| `frontend/src/modules/calendar/calendarApi.ts` | Modify | New types + createEvent/updateEvent/deleteEvent |
| `frontend/src/modules/admin/adminApi.ts` | Modify | New Google OAuth functions + updated CalendarSource type |
| `frontend/src/modules/calendar/googleColors.ts` | Create | Google color map + resolveEventColor helper |
| `frontend/src/modules/calendar/EventForm.tsx` | Create | Shared create/edit form component |
| `frontend/src/modules/calendar/EventDetail.tsx` | Modify | Edit/delete buttons when editable; reminder display |
| `frontend/src/modules/calendar/CalendarPage.tsx` | Modify | mode state, sources state, + Ny aftale button |
| `frontend/src/modules/admin/AdminPage.tsx` | Modify | Google OAuth button + calendar picker after callback |

---

### Task 1: Add Google packages and config settings

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add Google packages to requirements.txt**

Open `backend/requirements.txt`. Add after the last line:

```
google-api-python-client==2.151.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
```

- [ ] **Step 2: Add Google settings to config.py**

Replace the `Settings` class body in `backend/app/core/config.py`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    owner_password: str
    ntfy_url: str = "http://ntfy:80"
    ntfy_topic: str = "mylife"
    anthropic_api_key: str = ""
    ical_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://mylife.smoelgaard.com/api/admin/google/callback"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py
git commit -m "feat: add Google Calendar packages and config settings"
```

---

### Task 2: Data models + migration 0004

**Files:**
- Modify: `backend/app/modules/calendar/source_models.py`
- Modify: `backend/app/modules/calendar/models.py`
- Create: `backend/app/modules/calendar/google_session_models.py`
- Modify: `backend/app/core/models.py`
- Create: `backend/alembic/versions/0004_google_calendar.py`

- [ ] **Step 1: Update source_models.py**

Replace the full content of `backend/app/modules/calendar/source_models.py`:

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.models import Base


class CalendarSource(Base):
    __tablename__ = "calendar_sources"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(16), default="ical")
    ical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_calendar_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_credentials: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#eab308")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
```

- [ ] **Step 2: Update models.py**

Replace the full content of `backend/app/modules/calendar/models.py`:

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.models import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_calendar_events_start_dt", "start_dt"), {"schema": "calendar"})

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    start_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="ical")
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("calendar.calendar_sources.id", ondelete="CASCADE"), nullable=True
    )
    google_event_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    google_color_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reminder_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: Create google_session_models.py**

Create `backend/app/modules/calendar/google_session_models.py`:

```python
from datetime import datetime
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.models import Base


class GoogleOAuthSession(Base):
    __tablename__ = "google_oauth_sessions"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(primary_key=True)
    session_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    credentials_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calendar_list_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
```

- [ ] **Step 4: Add import to core/models.py**

Replace the full content of `backend/app/core/models.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import alle modeller her så Alembic's autogenerate finder dem
from app.modules.calendar import models as _calendar_models  # noqa: F401, E402
from app.modules.calendar import source_models as _source_models  # noqa: F401, E402
from app.modules.calendar import google_session_models as _google_session_models  # noqa: F401, E402
```

- [ ] **Step 5: Create migration 0004**

Create `backend/alembic/versions/0004_google_calendar.py`:

```python
"""google calendar two-way sync

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # calendar_sources: make ical_url nullable
    op.alter_column("calendar_sources", "ical_url", nullable=True, schema="calendar")

    # calendar_sources: add new columns
    op.add_column(
        "calendar_sources",
        sa.Column("source_type", sa.String(16), nullable=False, server_default="ical"),
        schema="calendar",
    )
    op.add_column(
        "calendar_sources",
        sa.Column("google_calendar_id", sa.Text(), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "calendar_sources",
        sa.Column("google_credentials", JSONB(), nullable=True),
        schema="calendar",
    )

    # events: add new columns
    op.add_column(
        "events",
        sa.Column("google_event_id", sa.String(512), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "events",
        sa.Column("google_color_id", sa.String(16), nullable=True),
        schema="calendar",
    )
    op.add_column(
        "events",
        sa.Column("reminder_minutes", sa.Integer(), nullable=True),
        schema="calendar",
    )

    # new google_oauth_sessions table
    op.create_table(
        "google_oauth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_token", sa.String(128), nullable=False, unique=True),
        sa.Column("credentials_json", sa.Text(), nullable=True),
        sa.Column("calendar_list_json", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="calendar",
    )
    op.create_index(
        "ix_calendar_google_oauth_sessions_session_token",
        "google_oauth_sessions",
        ["session_token"],
        schema="calendar",
    )


def downgrade() -> None:
    op.drop_table("google_oauth_sessions", schema="calendar")
    op.drop_column("events", "reminder_minutes", schema="calendar")
    op.drop_column("events", "google_color_id", schema="calendar")
    op.drop_column("events", "google_event_id", schema="calendar")
    op.drop_column("calendar_sources", "google_credentials", schema="calendar")
    op.drop_column("calendar_sources", "google_calendar_id", schema="calendar")
    op.drop_column("calendar_sources", "source_type", schema="calendar")
    op.alter_column("calendar_sources", "ical_url", nullable=False, schema="calendar")
```

- [ ] **Step 6: Verify migration chain**

Check that 0003 exists and 0004 references it correctly:

```bash
ls backend/alembic/versions/
# Expected: 0001_*.py  0002_*.py  0003_*.py  0004_google_calendar.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/calendar/source_models.py \
        backend/app/modules/calendar/models.py \
        backend/app/modules/calendar/google_session_models.py \
        backend/app/core/models.py \
        backend/alembic/versions/0004_google_calendar.py
git commit -m "feat: data models and migration 0004 for Google Calendar sync"
```

---

### Task 3: google_service.py

**Files:**
- Create: `backend/app/modules/calendar/google_service.py`
- Create: `backend/tests/calendar/test_google_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/calendar/test_google_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/calendar/test_google_service.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — google_service.py doesn't exist yet.

- [ ] **Step 3: Create google_service.py**

Create `backend/app/modules/calendar/google_service.py`:

```python
"""Google Calendar API service — all Google API logic isolated here.

All public async functions wrap synchronous Google API calls with asyncio.to_thread.
"""
import asyncio
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

import google.auth.exceptions
import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


# ---------------------------------------------------------------------------
# Internal helpers (synchronous — safe to call directly in tests)
# ---------------------------------------------------------------------------

def _make_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def _dict_to_creds(creds_dict: dict) -> google.oauth2.credentials.Credentials:
    return google.oauth2.credentials.Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
    )


def _creds_to_dict(creds: google.oauth2.credentials.Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }


def _normalize_google_event(item: dict) -> dict:
    """Convert a Google Calendar API event dict to our Event model fields."""
    start = item.get("start", {})
    end = item.get("end", {})

    if "date" in start:
        # All-day event
        start_date = datetime.fromisoformat(start["date"])
        end_date = datetime.fromisoformat(end["date"])
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc)
        all_day = True
    else:
        start_dt = datetime.fromisoformat(start["dateTime"]).astimezone(timezone.utc)
        end_dt = datetime.fromisoformat(end["dateTime"]).astimezone(timezone.utc)
        all_day = False

    reminders = item.get("reminders", {})
    reminder_minutes = None
    if not reminders.get("useDefault", True):
        overrides = reminders.get("overrides", [])
        if overrides:
            reminder_minutes = overrides[0].get("minutes")

    return {
        "uid": f"google_{item['id']}",
        "google_event_id": item["id"],
        "title": item.get("summary") or "Ingen titel",
        "start_dt": start_dt,
        "end_dt": end_dt,
        "all_day": all_day,
        "location": item.get("location") or None,
        "description": item.get("description") or None,
        "google_color_id": item.get("colorId") or None,
        "reminder_minutes": reminder_minutes,
        "source": "google",
    }


def _event_data_to_google_body(data: dict) -> dict:
    """Convert our internal event_data dict to a Google Calendar API request body."""
    start_dt: datetime = data["start_dt"]
    end_dt: datetime = data["end_dt"]
    all_day: bool = data.get("all_day", False)

    if all_day:
        start = {"date": start_dt.strftime("%Y-%m-%d")}
        end = {"date": end_dt.strftime("%Y-%m-%d")}
    else:
        start = {"dateTime": start_dt.astimezone(timezone.utc).isoformat()}
        end = {"dateTime": end_dt.astimezone(timezone.utc).isoformat()}

    body: dict[str, Any] = {
        "summary": data["title"],
        "start": start,
        "end": end,
    }

    if data.get("location"):
        body["location"] = data["location"]
    if data.get("description"):
        body["description"] = data["description"]
    if data.get("google_color_id"):
        body["colorId"] = data["google_color_id"]

    reminder_minutes = data.get("reminder_minutes")
    if reminder_minutes is not None:
        body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": reminder_minutes}],
        }
    else:
        body["reminders"] = {"useDefault": True}

    return body


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def build_auth_url(state: str) -> str:
    """Build Google OAuth2 authorization URL."""
    def _sync():
        flow = _make_flow()
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )
        return url

    return await asyncio.to_thread(_sync)


async def exchange_code(code: str) -> dict:
    """Exchange OAuth2 authorization code for credentials dict."""
    def _sync():
        flow = _make_flow()
        flow.fetch_token(code=code)
        return _creds_to_dict(flow.credentials)

    return await asyncio.to_thread(_sync)


async def get_calendar_list(creds_dict: dict) -> list[dict]:
    """Return user's Google Calendars: [{id, name, color}]."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        service = build("calendar", "v3", credentials=creds)
        result = service.calendarList().list().execute()
        return [
            {
                "id": item["id"],
                "name": item.get("summary", item["id"]),
                "color": item.get("backgroundColor", "#4285f4"),
            }
            for item in result.get("items", [])
        ]

    return await asyncio.to_thread(_sync)


async def refresh_credentials_if_needed(creds_dict: dict) -> dict:
    """Refresh access token if expired. Returns updated credentials dict."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        if not creds.valid:
            creds.refresh(Request())
        return _creds_to_dict(creds)

    return await asyncio.to_thread(_sync)


async def fetch_google_events(
    creds_dict: dict,
    calendar_id: str,
    from_dt: datetime,
    to_dt: datetime,
) -> list[dict]:
    """Fetch events from Google Calendar API. Returns list of normalized event dicts."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        service = build("calendar", "v3", credentials=creds)
        events = []
        page_token = None
        while True:
            response = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=from_dt.isoformat(),
                    timeMax=to_dt.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    pageToken=page_token,
                )
                .execute()
            )
            for item in response.get("items", []):
                if item.get("status") == "cancelled":
                    continue
                events.append(_normalize_google_event(item))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return events

    return await asyncio.to_thread(_sync)


async def create_google_event(
    creds_dict: dict,
    calendar_id: str,
    event_data: dict,
) -> str:
    """Create event in Google Calendar. Returns google_event_id."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        service = build("calendar", "v3", credentials=creds)
        body = _event_data_to_google_body(event_data)
        result = service.events().insert(calendarId=calendar_id, body=body).execute()
        return result["id"]

    return await asyncio.to_thread(_sync)


async def update_google_event(
    creds_dict: dict,
    calendar_id: str,
    google_event_id: str,
    event_data: dict,
) -> None:
    """Update event in Google Calendar."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        service = build("calendar", "v3", credentials=creds)
        body = _event_data_to_google_body(event_data)
        service.events().update(
            calendarId=calendar_id, eventId=google_event_id, body=body
        ).execute()

    await asyncio.to_thread(_sync)


async def delete_google_event(
    creds_dict: dict,
    calendar_id: str,
    google_event_id: str,
) -> None:
    """Delete event from Google Calendar."""
    def _sync():
        creds = _dict_to_creds(creds_dict)
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()

    await asyncio.to_thread(_sync)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/calendar/test_google_service.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/calendar/google_service.py \
        backend/tests/calendar/test_google_service.py
git commit -m "feat: google_service.py with pure function unit tests"
```

---

### Task 4: Update schemas

**Files:**
- Modify: `backend/app/modules/calendar/schemas.py`
- Modify: `backend/app/modules/calendar/source_schemas.py`

- [ ] **Step 1: Update schemas.py**

Replace the full content of `backend/app/modules/calendar/schemas.py`:

```python
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
    google_event_id: str | None = None
    google_color_id: str | None = None
    reminder_minutes: int | None = None
    editable: bool = False

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None
    google_color_id: str | None = None
    source_id: int


class EventUpdate(BaseModel):
    title: str | None = None
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None
    google_color_id: str | None = None
```

- [ ] **Step 2: Update source_schemas.py**

Replace the full content of `backend/app/modules/calendar/source_schemas.py`:

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/calendar/schemas.py \
        backend/app/modules/calendar/source_schemas.py
git commit -m "feat: update schemas for Google Calendar integration"
```

---

### Task 5: Update service.py (sync branching + google sync)

**Files:**
- Modify: `backend/app/modules/calendar/service.py`

- [ ] **Step 1: Replace service.py**

Replace the full content of `backend/app/modules/calendar/service.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/modules/calendar/service.py
git commit -m "feat: service.py sync branching for google vs ical sources"
```

---

### Task 6: Backend CRUD endpoints in router.py

**Files:**
- Modify: `backend/app/modules/calendar/router.py`

- [ ] **Step 1: Replace router.py**

Replace the full content of `backend/app/modules/calendar/router.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/modules/calendar/router.py
git commit -m "feat: CRUD endpoints for Google Calendar events"
```

---

### Task 7: Google OAuth endpoints in admin_router.py

**Files:**
- Modify: `backend/app/modules/calendar/admin_router.py`

- [ ] **Step 1: Replace admin_router.py**

Replace the full content of `backend/app/modules/calendar/admin_router.py`:

```python
import json
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import google.auth.exceptions

from app.core.auth import require_auth
from app.core.database import get_db
from app.modules.calendar.google_session_models import GoogleOAuthSession
from app.modules.calendar.source_models import CalendarSource
from app.modules.calendar.source_schemas import (
    CalendarSourceCreate,
    CalendarSourceOut,
    GoogleConnectRequest,
)
from app.modules.calendar.service import sync_source
from app.modules.calendar import google_service

router = APIRouter()


@router.get("/calendar-sources", response_model=list[CalendarSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(
        select(CalendarSource).order_by(CalendarSource.created_at)
    )
    return list(result.scalars().all())


@router.post("/calendar-sources", response_model=CalendarSourceOut, status_code=201)
async def create_source(
    body: CalendarSourceCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    source = CalendarSource(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    try:
        await sync_source(db, source.id)
    except Exception:
        pass
    return source


@router.delete("/calendar-sources/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kilde ikke fundet")
    await db.delete(source)
    await db.commit()


# ---------------------------------------------------------------------------
# Google OAuth endpoints
# ---------------------------------------------------------------------------

@router.get("/google/auth-url")
async def google_auth_url(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Generate Google OAuth2 authorization URL. State is stored as a session token."""
    state = secrets.token_urlsafe(32)
    # Store state in DB so callback can validate it
    session = GoogleOAuthSession(
        session_token=state,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(session)
    await db.commit()

    auth_url = await google_service.build_auth_url(state=state)
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 callback from Google. Exchanges code, stores credentials in session, redirects to admin."""
    # Validate state token
    result = await db.execute(
        select(GoogleOAuthSession).where(GoogleOAuthSession.session_token == state)
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at < datetime.now(timezone.utc):
        return RedirectResponse(url="/admin?google_error=invalid_state")

    try:
        creds = await google_service.exchange_code(code=code)
        calendars = await google_service.get_calendar_list(creds)
    except Exception:
        return RedirectResponse(url="/admin?google_error=exchange_failed")

    # Store credentials + calendar list in session row
    session.credentials_json = json.dumps(creds)
    session.calendar_list_json = json.dumps(calendars)
    session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()

    return RedirectResponse(url=f"/admin?google_session={state}")


@router.get("/google/session/{token}")
async def google_session(
    token: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Return calendar list from a pending OAuth session."""
    result = await db.execute(
        select(GoogleOAuthSession).where(GoogleOAuthSession.session_token == token)
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Session ikke fundet eller udløbet")
    calendars = json.loads(session.calendar_list_json or "[]")
    return {"calendars": calendars}


@router.post("/google/connect", response_model=CalendarSourceOut, status_code=201)
async def google_connect(
    body: GoogleConnectRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Create a Google CalendarSource from an OAuth session and trigger initial sync."""
    result = await db.execute(
        select(GoogleOAuthSession).where(
            GoogleOAuthSession.session_token == body.session_token
        )
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Session ikke fundet eller udløbet")

    creds = json.loads(session.credentials_json or "{}")

    source = CalendarSource(
        name=body.name,
        source_type="google",
        google_calendar_id=body.calendar_id,
        google_credentials=creds,
        color=body.color,
        is_active=True,
    )
    db.add(source)

    # Delete the session row
    await db.delete(session)
    await db.commit()
    await db.refresh(source)

    # Trigger immediate sync (errors non-fatal)
    try:
        await sync_source(db, source.id)
    except Exception:
        pass

    return source
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/modules/calendar/admin_router.py
git commit -m "feat: Google OAuth endpoints in admin_router"
```

---

### Task 8: Frontend helpers — calendarApi.ts, adminApi.ts, googleColors.ts

**Files:**
- Modify: `frontend/src/modules/calendar/calendarApi.ts`
- Modify: `frontend/src/modules/admin/adminApi.ts`
- Create: `frontend/src/modules/calendar/googleColors.ts`

- [ ] **Step 1: Update calendarApi.ts**

Replace the full content of `frontend/src/modules/calendar/calendarApi.ts`:

```typescript
import { api } from '../../api/client'

export interface CalendarEvent {
  id: number
  uid: string
  title: string
  start_dt: string
  end_dt: string
  all_day: boolean
  location: string | null
  description: string | null
  source: string
  source_id: number | null
  source_color: string | null
  google_event_id: string | null
  google_color_id: string | null
  reminder_minutes: number | null
  editable: boolean
}

export interface EventCreate {
  title: string
  start_dt: string
  end_dt: string
  all_day: boolean
  source_id: number
  location?: string | null
  description?: string | null
  reminder_minutes?: number | null
  google_color_id?: string | null
}

export interface EventUpdate {
  title?: string
  start_dt?: string
  end_dt?: string
  all_day?: boolean
  location?: string | null
  description?: string | null
  reminder_minutes?: number | null
  google_color_id?: string | null
}

export async function getUpcomingEvents(limit = 5): Promise<CalendarEvent[]> {
  return api.get<CalendarEvent[]>(`/calendar/events?upcoming=true&limit=${limit}`)
}

export async function getEventsInRange(from: Date, to: Date): Promise<CalendarEvent[]> {
  return api.get<CalendarEvent[]>(
    `/calendar/events?from_dt=${from.toISOString()}&to_dt=${to.toISOString()}`
  )
}

export async function syncCalendar(): Promise<{ synced: number }> {
  return api.post<{ synced: number }>('/calendar/sync')
}

export async function createEvent(data: EventCreate): Promise<CalendarEvent> {
  return api.post<CalendarEvent>('/calendar/events', data)
}

export async function updateEvent(id: number, data: EventUpdate): Promise<CalendarEvent> {
  return api.put<CalendarEvent>(`/calendar/events/${id}`, data)
}

export async function deleteEvent(id: number): Promise<void> {
  return api.delete<void>(`/calendar/events/${id}`)
}
```

- [ ] **Step 2: Update adminApi.ts**

Replace the full content of `frontend/src/modules/admin/adminApi.ts`:

```typescript
import { api } from '../../api/client'

export interface CalendarSource {
  id: number
  name: string
  source_type: string
  ical_url: string | null
  color: string
  is_active: boolean
  created_at: string
}

export interface CalendarSourceCreate {
  name: string
  ical_url: string
  color: string
}

export interface GoogleConnectData {
  session_token: string
  calendar_id: string
  name: string
  color: string
}

export async function getCalendarSources(): Promise<CalendarSource[]> {
  return api.get<CalendarSource[]>('/admin/calendar-sources')
}

export async function createCalendarSource(
  data: CalendarSourceCreate
): Promise<CalendarSource> {
  return api.post<CalendarSource>('/admin/calendar-sources', data)
}

export async function deleteCalendarSource(id: number): Promise<void> {
  return api.delete<void>(`/admin/calendar-sources/${id}`)
}

export async function getGoogleAuthUrl(): Promise<{ auth_url: string }> {
  return api.get<{ auth_url: string }>('/admin/google/auth-url')
}

export async function getGoogleSession(
  token: string
): Promise<{ calendars: { id: string; name: string; color: string }[] }> {
  return api.get(`/admin/google/session/${token}`)
}

export async function connectGoogleCalendar(
  data: GoogleConnectData
): Promise<CalendarSource> {
  return api.post<CalendarSource>('/admin/google/connect', data)
}
```

- [ ] **Step 3: Check that api client has a put method**

Read `frontend/src/api/client.ts` to verify it exports `api.put`. If it doesn't, add it now.

```bash
cat frontend/src/api/client.ts
```

If `put` is missing, add it alongside `post` and `delete`:

```typescript
put: async <T>(path: string, body?: unknown): Promise<T> => {
  const res = await fetch(`${BASE}/api${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  const text = await res.text()
  return text ? JSON.parse(text) : (undefined as T)
},
```

- [ ] **Step 4: Create googleColors.ts**

Create `frontend/src/modules/calendar/googleColors.ts`:

```typescript
export const GOOGLE_COLORS: Record<string, string> = {
  '1': '#D50000',   // Tomat
  '2': '#E67C73',   // Flamingo
  '3': '#8E24AA',   // Drue
  '4': '#3F51B5',   // Blåbær
  '5': '#039BE5',   // Hav
  '6': '#33B679',   // Salvie
  '7': '#0B8043',   // Basilikum
  '8': '#7CB342',   // Avocado
  '9': '#F6BF26',   // Fersken
  '10': '#F09300',  // Banan
  '11': '#616161',  // Grafit
}

export const GOOGLE_COLOR_NAMES: Record<string, string> = {
  '1': 'Tomat', '2': 'Flamingo', '3': 'Drue', '4': 'Blåbær',
  '5': 'Hav', '6': 'Salvie', '7': 'Basilikum', '8': 'Avocado',
  '9': 'Fersken', '10': 'Banan', '11': 'Grafit',
}

export function resolveEventColor(event: {
  google_color_id: string | null
  source_color: string | null
}): string {
  if (event.google_color_id && GOOGLE_COLORS[event.google_color_id]) {
    return GOOGLE_COLORS[event.google_color_id]
  }
  return event.source_color ?? '#eab308'
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/modules/calendar/calendarApi.ts \
        frontend/src/modules/admin/adminApi.ts \
        frontend/src/modules/calendar/googleColors.ts \
        frontend/src/api/client.ts
git commit -m "feat: frontend API helpers and Google color utilities"
```

---

### Task 9: EventForm.tsx

**Files:**
- Create: `frontend/src/modules/calendar/EventForm.tsx`

- [ ] **Step 1: Create EventForm.tsx**

Create `frontend/src/modules/calendar/EventForm.tsx`:

```tsx
import { useState, type FormEvent } from 'react'
import { format, parseISO } from 'date-fns'
import type { CalendarEvent, EventCreate, EventUpdate } from './calendarApi'
import { createEvent, updateEvent } from './calendarApi'
import type { CalendarSource } from '../admin/adminApi'
import { GOOGLE_COLORS, GOOGLE_COLOR_NAMES } from './googleColors'

interface Props {
  event?: CalendarEvent       // undefined = create mode
  sources: CalendarSource[]
  defaultSourceId?: number
  onSave: (event: CalendarEvent) => void
  onCancel: () => void
}

const REMINDER_OPTIONS = [
  { label: 'Ingen', value: null },
  { label: '5 min', value: 5 },
  { label: '10 min', value: 10 },
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 time', value: 60 },
  { label: '1 dag', value: 1440 },
]

function toLocalDateString(isoString: string): string {
  return isoString.slice(0, 10)
}

function toLocalTimeString(isoString: string): string {
  return isoString.slice(11, 16)
}

export function EventForm({ event, sources, defaultSourceId, onSave, onCancel }: Props) {
  const isEdit = event !== undefined
  const googleSources = sources.filter(s => s.source_type === 'google')

  const [title, setTitle] = useState(event?.title ?? '')
  const [sourceId, setSourceId] = useState<number>(
    event?.source_id ?? defaultSourceId ?? googleSources[0]?.id ?? 0
  )
  const [allDay, setAllDay] = useState(event?.all_day ?? false)
  const [date, setDate] = useState(
    event ? toLocalDateString(event.start_dt) : format(new Date(), 'yyyy-MM-dd')
  )
  const [startTime, setStartTime] = useState(
    event && !event.all_day ? toLocalTimeString(event.start_dt) : '09:00'
  )
  const [endTime, setEndTime] = useState(
    event && !event.all_day ? toLocalTimeString(event.end_dt) : '10:00'
  )
  const [location, setLocation] = useState(event?.location ?? '')
  const [description, setDescription] = useState(event?.description ?? '')
  const [reminderMinutes, setReminderMinutes] = useState<number | null>(
    event?.reminder_minutes ?? null
  )
  const [colorId, setColorId] = useState<string | null>(event?.google_color_id ?? null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    setError('')

    try {
      const startIso = allDay
        ? `${date}T00:00:00.000Z`
        : `${date}T${startTime}:00.000Z`
      const endIso = allDay
        ? `${date}T00:00:00.000Z`
        : `${date}T${endTime}:00.000Z`

      let saved: CalendarEvent
      if (isEdit && event) {
        const payload: EventUpdate = {
          title: title.trim(),
          start_dt: startIso,
          end_dt: endIso,
          all_day: allDay,
          location: location.trim() || null,
          description: description.trim() || null,
          reminder_minutes: reminderMinutes,
          google_color_id: colorId,
        }
        saved = await updateEvent(event.id, payload)
      } else {
        const payload: EventCreate = {
          title: title.trim(),
          start_dt: startIso,
          end_dt: endIso,
          all_day: allDay,
          source_id: sourceId,
          location: location.trim() || null,
          description: description.trim() || null,
          reminder_minutes: reminderMinutes,
          google_color_id: colorId,
        }
        saved = await createEvent(payload)
      }
      onSave(saved)
    } catch {
      setError('Kunne ikke gemme aftalen — prøv igen')
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const labelClass = 'text-gray-400 text-xs mb-1 block'

  return (
    <div className="mt-4 bg-gray-900 rounded-xl p-5">
      <h3 className="text-white font-semibold text-lg mb-4">
        {isEdit ? 'Rediger aftale' : 'Ny aftale'}
      </h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Titel */}
        <div>
          <label className={labelClass}>Titel *</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            required
            placeholder="Titel"
            className={inputClass}
          />
        </div>

        {/* Kalender (create only) */}
        {!isEdit && (
          <div>
            <label className={labelClass}>Kalender</label>
            {googleSources.length === 0 ? (
              <p className="text-yellow-400 text-sm">
                Ingen Google Kalender tilsluttet — tilslut under Admin
              </p>
            ) : (
              <select
                value={sourceId}
                onChange={e => setSourceId(Number(e.target.value))}
                className={inputClass}
              >
                {googleSources.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Heldagsbegivenhed */}
        <div className="flex items-center gap-3">
          <input
            id="allDay"
            type="checkbox"
            checked={allDay}
            onChange={e => setAllDay(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="allDay" className="text-gray-300 text-sm">
            Heldagsbegivenhed
          </label>
        </div>

        {/* Dato */}
        <div>
          <label className={labelClass}>Dato</label>
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        {/* Fra / Til */}
        {!allDay && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Fra</label>
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                required
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Til</label>
              <input
                type="time"
                value={endTime}
                onChange={e => setEndTime(e.target.value)}
                required
                className={inputClass}
              />
            </div>
          </div>
        )}

        {/* Sted */}
        <div>
          <label className={labelClass}>Sted</label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Valgfrit"
            className={inputClass}
          />
        </div>

        {/* Beskrivelse */}
        <div>
          <label className={labelClass}>Beskrivelse</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Valgfrit"
            rows={3}
            className={inputClass + ' resize-none'}
          />
        </div>

        {/* Påmindelse */}
        <div>
          <label className={labelClass}>Påmindelse</label>
          <select
            value={reminderMinutes ?? ''}
            onChange={e =>
              setReminderMinutes(e.target.value === '' ? null : Number(e.target.value))
            }
            className={inputClass}
          >
            {REMINDER_OPTIONS.map(opt => (
              <option key={String(opt.value)} value={opt.value ?? ''}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Farve */}
        <div>
          <label className={labelClass}>Farve</label>
          <div className="flex gap-2 flex-wrap">
            {/* No color option */}
            <button
              type="button"
              onClick={() => setColorId(null)}
              className={`w-7 h-7 rounded-full border-2 transition-transform ${
                colorId === null
                  ? 'scale-125 border-white'
                  : 'border-gray-600 hover:scale-110'
              } bg-gray-600`}
              title="Kalenderfarve"
            />
            {Object.entries(GOOGLE_COLORS).map(([id, hex]) => (
              <button
                key={id}
                type="button"
                onClick={() => setColorId(id)}
                className={`w-7 h-7 rounded-full transition-transform ${
                  colorId === id
                    ? 'scale-125 ring-2 ring-white ring-offset-2 ring-offset-gray-900'
                    : 'hover:scale-110'
                }`}
                style={{ backgroundColor: hex }}
                title={GOOGLE_COLOR_NAMES[id]}
              />
            ))}
          </div>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || (!isEdit && googleSources.length === 0)}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm px-5 py-2 rounded-lg transition-colors"
          >
            {saving ? 'Gemmer...' : 'Gem'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-400 hover:text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            Annuller
          </button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/modules/calendar/EventForm.tsx
git commit -m "feat: EventForm component for create/edit calendar events"
```

---

### Task 10: Update EventDetail.tsx

**Files:**
- Modify: `frontend/src/modules/calendar/EventDetail.tsx`

- [ ] **Step 1: Replace EventDetail.tsx**

Replace the full content of `frontend/src/modules/calendar/EventDetail.tsx`:

```tsx
import { differenceInMinutes, format, parseISO } from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { deleteEvent } from './calendarApi'

function formatDuration(start: string, end: string, allDay: boolean): string {
  if (allDay) return 'Heldagsbegivenhed'
  const minutes = differenceInMinutes(parseISO(end), parseISO(start))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remaining = minutes % 60
  return remaining > 0 ? `${hours} t ${remaining} min` : `${hours} t`
}

function formatDate(isoString: string, allDay: boolean): string {
  const dt = parseISO(isoString)
  return allDay
    ? format(dt, 'd. MMMM yyyy', { locale: da })
    : format(dt, 'd. MMMM yyyy HH:mm', { locale: da })
}

function formatReminder(minutes: number): string {
  if (minutes < 60) return `${minutes} min før`
  if (minutes === 60) return '1 time før'
  if (minutes === 1440) return '1 dag før'
  return `${minutes} min før`
}

interface Props {
  event: CalendarEvent | null
  onEdit: () => void
  onDelete: () => void
}

export function EventDetail({ event, onEdit, onDelete }: Props) {
  if (!event) return null

  const borderColor = event.source_color ?? '#eab308'

  async function handleDelete() {
    if (!confirm(`Slet "${event!.title}"?`)) return
    try {
      await deleteEvent(event!.id)
      onDelete()
    } catch {
      alert('Kunne ikke slette aftalen')
    }
  }

  return (
    <div
      className="mt-4 bg-gray-900 rounded-xl p-5 border-l-4"
      style={{ borderColor }}
    >
      <h3 className="text-white font-semibold text-lg mb-3">{event.title}</h3>
      <div className="space-y-2 text-sm">
        <div className="flex gap-3">
          <span className="text-gray-500 w-24 shrink-0">Dato</span>
          <span className="text-gray-200">{formatDate(event.start_dt, event.all_day)}</span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-500 w-24 shrink-0">Varighed</span>
          <span className="text-gray-200">
            {formatDuration(event.start_dt, event.end_dt, event.all_day)}
          </span>
        </div>
        {event.location && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Sted</span>
            <span className="text-gray-200">{event.location}</span>
          </div>
        )}
        {event.description && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Beskrivelse</span>
            <span className="text-gray-200 whitespace-pre-wrap break-words">
              {event.description}
            </span>
          </div>
        )}
        {event.reminder_minutes != null && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Påmindelse</span>
            <span className="text-gray-200">{formatReminder(event.reminder_minutes)}</span>
          </div>
        )}
      </div>

      {event.editable && (
        <div className="flex gap-3 mt-4 pt-4 border-t border-gray-800">
          <button
            onClick={onEdit}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            ✏️ Rediger
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            🗑️ Slet
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/modules/calendar/EventDetail.tsx
git commit -m "feat: EventDetail edit/delete buttons and reminder display"
```

---

### Task 11: Update CalendarPage.tsx

**Files:**
- Modify: `frontend/src/modules/calendar/CalendarPage.tsx`

- [ ] **Step 1: Replace CalendarPage.tsx**

Replace the full content of `frontend/src/modules/calendar/CalendarPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { getEventsInRange, syncCalendar } from './calendarApi'
import { EventDetail } from './EventDetail'
import { EventForm } from './EventForm'
import { resolveEventColor } from './googleColors'
import type { CalendarSource } from '../admin/adminApi'
import { getCalendarSources } from '../admin/adminApi'

type Mode = 'view' | 'create' | 'edit'

export function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const [mode, setMode] = useState<Mode>('view')
  const [sources, setSources] = useState<CalendarSource[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const calEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: calStart, end: calEnd })

  useEffect(() => {
    getCalendarSources().then(setSources).catch(() => setSources([]))
  }, [])

  useEffect(() => {
    setSelectedEvent(null)
    setMode('view')
    getEventsInRange(calStart, calEnd)
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [currentMonth])

  async function refreshEvents() {
    try {
      const fresh = await getEventsInRange(calStart, calEnd)
      setEvents(fresh)
    } catch {
      // ignore
    }
  }

  function eventsOnDay(day: Date): CalendarEvent[] {
    return events.filter(e => isSameDay(parseISO(e.start_dt), day))
  }

  function handleEventClick(e: CalendarEvent) {
    setSelectedEvent(prev => (prev?.id === e.id ? null : e))
    setMode('view')
  }

  async function handleSync() {
    setSyncing(true)
    setSyncMsg('')
    try {
      const result = await syncCalendar()
      setSyncMsg(`${result.synced} events synkroniseret`)
      await refreshEvents()
    } catch {
      setSyncMsg('Sync fejlede')
    } finally {
      setSyncing(false)
    }
  }

  function handleSave(saved: CalendarEvent) {
    setMode('view')
    setSelectedEvent(saved)
    refreshEvents()
  }

  function handleDelete() {
    setMode('view')
    setSelectedEvent(null)
    refreshEvents()
  }

  const weekDays = ['Man', 'Tir', 'Ons', 'Tor', 'Fre', 'Lør', 'Søn']

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="text-gray-400 hover:text-white px-2 py-1 rounded"
          >
            ←
          </button>
          <h2 className="text-xl font-semibold capitalize">
            {format(currentMonth, 'MMMM yyyy', { locale: da })}
          </h2>
          <button
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="text-gray-400 hover:text-white px-2 py-1 rounded"
          >
            →
          </button>
        </div>
        <div className="flex items-center gap-3">
          {syncMsg && <span className="text-sm text-gray-400">{syncMsg}</span>}
          <button
            onClick={() => {
              setMode('create')
              setSelectedEvent(null)
            }}
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            + Ny aftale
          </button>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="text-sm bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 text-white px-4 py-2 rounded-lg transition-colors"
          >
            {syncing ? 'Synkroniserer...' : '↻ Sync'}
          </button>
        </div>
      </div>

      {/* Kalender grid */}
      <div className="grid grid-cols-7 gap-px bg-gray-800 rounded-xl overflow-hidden">
        {weekDays.map(d => (
          <div
            key={d}
            className="bg-gray-900 text-center text-xs text-gray-500 py-2 font-medium"
          >
            {d}
          </div>
        ))}
        {days.map(day => {
          const dayEvents = eventsOnDay(day)
          const inMonth = isSameMonth(day, currentMonth)
          const today = isToday(day)
          return (
            <div
              key={day.toISOString()}
              className={`bg-gray-900 min-h-[80px] p-2 ${!inMonth ? 'opacity-30' : ''}`}
            >
              <div
                className={`text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                  today ? 'bg-blue-600 text-white' : 'text-gray-400'
                }`}
              >
                {format(day, 'd')}
              </div>
              {dayEvents.slice(0, 3).map(e => {
                const color = resolveEventColor(e)
                const isSelected = selectedEvent?.id === e.id
                return (
                  <button
                    key={e.id}
                    onClick={() => handleEventClick(e)}
                    className={`w-full text-left text-xs rounded px-1 py-0.5 mb-0.5 truncate font-medium transition-opacity ${
                      isSelected ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-900' : 'hover:opacity-80'
                    }`}
                    style={{ backgroundColor: color, color: '#111827' }}
                    title={e.title}
                  >
                    {!e.all_day && (
                      <span className="opacity-70 mr-1">
                        {format(parseISO(e.start_dt), 'HH:mm')}
                      </span>
                    )}
                    {e.title}
                  </button>
                )
              })}
              {dayEvents.length > 3 && (
                <div className="text-xs text-gray-500">+{dayEvents.length - 3} mere</div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom panel */}
      {mode === 'view' && selectedEvent && (
        <EventDetail
          event={selectedEvent}
          onEdit={() => setMode('edit')}
          onDelete={handleDelete}
        />
      )}
      {mode === 'create' && (
        <EventForm
          sources={sources}
          onSave={handleSave}
          onCancel={() => setMode('view')}
        />
      )}
      {mode === 'edit' && selectedEvent && (
        <EventForm
          event={selectedEvent}
          sources={sources}
          onSave={handleSave}
          onCancel={() => setMode('view')}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/modules/calendar/CalendarPage.tsx
git commit -m "feat: CalendarPage mode state and create/edit flow"
```

---

### Task 12: Update AdminPage.tsx

**Files:**
- Modify: `frontend/src/modules/admin/AdminPage.tsx`

- [ ] **Step 1: Replace AdminPage.tsx**

Replace the full content of `frontend/src/modules/admin/AdminPage.tsx`:

```tsx
import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { CalendarSource } from './adminApi'
import {
  connectGoogleCalendar,
  deleteCalendarSource,
  getCalendarSources,
  getGoogleAuthUrl,
  getGoogleSession,
} from './adminApi'

const PRESET_COLORS = [
  '#eab308', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#f97316', '#06b6d4', '#ec4899',
]

interface GoogleCalendarOption {
  id: string
  name: string
  color: string
}

export function AdminPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [sources, setSources] = useState<CalendarSource[]>([])
  const [msg, setMsg] = useState('')

  // Google OAuth connect state
  const googleSession = searchParams.get('google_session')
  const googleError = searchParams.get('google_error')
  const [googleCalendars, setGoogleCalendars] = useState<GoogleCalendarOption[]>([])
  const [selectedCalendarId, setSelectedCalendarId] = useState('')
  const [connectName, setConnectName] = useState('')
  const [connectColor, setConnectColor] = useState('#3b82f6')
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    getCalendarSources().then(setSources).catch(() => setSources([]))
  }, [])

  useEffect(() => {
    if (googleSession) {
      getGoogleSession(googleSession)
        .then(data => {
          setGoogleCalendars(data.calendars)
          if (data.calendars.length > 0) {
            setSelectedCalendarId(data.calendars[0].id)
            setConnectName(data.calendars[0].name)
          }
        })
        .catch(() => setMsg('Kunne ikke hente kalender-liste fra Google'))
    }
  }, [googleSession])

  async function handleGoogleConnect(e: FormEvent) {
    e.preventDefault()
    if (!googleSession || !selectedCalendarId) return
    setConnecting(true)
    setMsg('')
    try {
      const source = await connectGoogleCalendar({
        session_token: googleSession,
        calendar_id: selectedCalendarId,
        name: connectName,
        color: connectColor,
      })
      setSources(prev => [...prev, source])
      setSearchParams({})  // Remove query params
      setGoogleCalendars([])
      setMsg('Google Kalender tilsluttet og synkroniseret')
    } catch {
      setMsg('Fejl ved tilslutning — prøv igen')
    } finally {
      setConnecting(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Slet kalender og alle dens aftaler?')) return
    try {
      await deleteCalendarSource(id)
      setSources(prev => prev.filter(s => s.id !== id))
    } catch {
      setMsg('Fejl ved sletning')
    }
  }

  async function handleGoogleAuth() {
    try {
      const { auth_url } = await getGoogleAuthUrl()
      window.location.href = auth_url
    } catch {
      setMsg('Kunne ikke starte Google-forbindelsen')
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold text-white mb-6">Kalender-kilder</h2>

      {/* Fejlbesked fra OAuth redirect */}
      {googleError && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-4 mb-6 text-red-300 text-sm">
          Google-forbindelsen fejlede ({googleError}) — prøv igen.
        </div>
      )}

      {/* Eksisterende sources */}
      <div className="space-y-2 mb-8">
        {sources.length === 0 && (
          <p className="text-gray-500 text-sm">Ingen kalender-kilder endnu.</p>
        )}
        {sources.map(s => (
          <div
            key={s.id}
            className="flex items-center justify-between bg-gray-900 rounded-lg p-4"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-4 h-4 rounded-full shrink-0"
                style={{ backgroundColor: s.color }}
              />
              <div className="min-w-0">
                <div className="text-white text-sm font-medium">{s.name}</div>
                <div className="text-gray-500 text-xs">
                  {s.source_type === 'google' ? '🔗 Google Calendar' : s.ical_url}
                </div>
              </div>
            </div>
            <button
              onClick={() => handleDelete(s.id)}
              className="text-gray-500 hover:text-red-400 text-sm transition-colors ml-4 shrink-0"
            >
              Slet
            </button>
          </div>
        ))}
      </div>

      {/* Google OAuth connect form (shown after OAuth callback) */}
      {googleSession && googleCalendars.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-5 mb-6">
          <h3 className="text-white font-medium mb-4">Vælg Google Kalender</h3>
          <form onSubmit={handleGoogleConnect} className="space-y-4">
            <div>
              <label className="text-gray-400 text-xs mb-1 block">Kalender</label>
              <select
                value={selectedCalendarId}
                onChange={e => {
                  const cal = googleCalendars.find(c => c.id === e.target.value)
                  setSelectedCalendarId(e.target.value)
                  if (cal) setConnectName(cal.name)
                }}
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {googleCalendars.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              placeholder="Navn"
              value={connectName}
              onChange={e => setConnectName(e.target.value)}
              required
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <div className="text-gray-400 text-xs mb-2">Farve</div>
              <div className="flex gap-2 flex-wrap">
                {PRESET_COLORS.map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setConnectColor(c)}
                    className={`w-7 h-7 rounded-full transition-transform ${
                      connectColor === c
                        ? 'scale-125 ring-2 ring-white ring-offset-2 ring-offset-gray-900'
                        : 'hover:scale-110'
                    }`}
                    style={{ backgroundColor: c }}
                    title={c}
                  />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                type="submit"
                disabled={connecting}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm px-5 py-2 rounded-lg transition-colors"
              >
                {connecting ? 'Tilslutter...' : 'Gem'}
              </button>
              <button
                type="button"
                onClick={() => setSearchParams({})}
                className="text-gray-400 hover:text-white text-sm"
              >
                Annuller
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tilføj Google Kalender */}
      {!googleSession && (
        <div className="bg-gray-900 rounded-xl p-5">
          <h3 className="text-white font-medium mb-4">Tilføj kalender</h3>
          <button
            onClick={handleGoogleAuth}
            className="flex items-center gap-2 bg-white hover:bg-gray-100 text-gray-900 text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Tilslut Google Kalender
          </button>
          {msg && <p className="text-sm text-gray-400 mt-3">{msg}</p>}
        </div>
      )}

      {msg && !googleSession && (
        <p className="text-sm text-gray-400 mt-4">{msg}</p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/modules/admin/AdminPage.tsx
git commit -m "feat: AdminPage Google OAuth flow and calendar picker"
```

---

### Task 13: Deploy

**Files:** No file changes — server operations only.

- [ ] **Step 1: Push to remote**

```bash
git push
```

- [ ] **Step 2: SSH to server and rebuild**

```bash
ssh root@46.62.165.156
cd /path/to/personal-dashboard
git pull
docker compose build backend frontend
docker compose up -d
```

- [ ] **Step 3: Run migration 0004**

```bash
docker compose exec backend alembic upgrade head
```

Expected output ends with: `Running upgrade 0003 -> 0004, google calendar two-way sync`

- [ ] **Step 4: Add Google credentials in Coolify**

In Coolify dashboard for the personal-dashboard service, add environment variables:
- `GOOGLE_CLIENT_ID` — from Google Cloud Console
- `GOOGLE_CLIENT_SECRET` — from Google Cloud Console

Redeploy or force-recreate so env vars load:

```bash
docker compose up -d --force-recreate backend
```

- [ ] **Step 5: Update Traefik**

```bash
bash scripts/update-traefik.sh
```

- [ ] **Step 6: Smoke test OAuth flow**

1. Open https://mylife.smoelgaard.com/admin
2. Click "Tilslut Google Kalender"
3. Verify redirect to Google consent screen
4. Authorize → verify redirect back to `/admin?google_session=...`
5. Select calendar, click Gem
6. Verify source appears in list
7. Click "↻ Sync" → verify events appear in calendar grid
8. Click a Google event → verify ✏️ Rediger and 🗑️ Slet appear
9. Click ✏️ Rediger → change title → Gem → verify title updated in Google Calendar
10. Click "+ Ny aftale" → fill form → Gem → verify new event in Google Calendar

- [ ] **Step 7: Tag release**

```bash
git tag v1.3.0-google-calendar
git push --tags
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ OAuth flow (auth-url, callback, session, connect)
- ✅ google_service.py with all 8 public functions
- ✅ Migration 0004 (all 7 column changes + new table)
- ✅ EventCreate/EventUpdate schemas
- ✅ EventOut.editable field
- ✅ POST/PUT/DELETE /events endpoints
- ✅ 409 for non-Google events
- ✅ 401 for expired tokens
- ✅ sync_source branching
- ✅ sync_google_source with ±90 day window
- ✅ EventForm with all 9 fields
- ✅ EventDetail edit/delete buttons
- ✅ CalendarPage mode state + sources + "+ Ny aftale"
- ✅ AdminPage Google button + calendar picker
- ✅ resolveEventColor using google_color_id
- ✅ Google Cloud setup instructions in deploy task

**Type consistency:**
- `EventCreate.source_id: int` → used in `router.py` POST → ✅
- `EventUpdate` all optional → used in PUT → ✅
- `GoogleConnectRequest` → matches `admin_router.py` POST /google/connect body → ✅
- `CalendarSource.source_type` added to `adminApi.ts` → used in `AdminPage.tsx` for display and `EventForm.tsx` filter → ✅
- `resolveEventColor({google_color_id, source_color})` → called in `CalendarPage.tsx` → ✅
- `EventDetail` props: `{event, onEdit, onDelete}` → called from `CalendarPage` → ✅
