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
