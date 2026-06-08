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
