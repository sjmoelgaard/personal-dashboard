# Google Calendar To-Vejs Sync — Design Spec

**Date:** 2026-06-08
**Status:** Approved

---

## Goal

Replace the existing read-only iCal sync with full two-way Google Calendar API integration. Users can create, edit, and delete events directly in the dashboard — changes are pushed to Google Calendar in real time. Existing iCal infrastructure is replaced.

---

## Architecture Overview

Three new components working together:

1. **OAuth2-flow** — user clicks "Tilslut Google Kalender" in admin → browser redirected to Google consent screen → Google redirects back with `code` → backend exchanges for tokens → credentials stored in DB
2. **Google Calendar sync service** — replaces iCal parsing. Uses `google-api-python-client` to fetch and push events via Google Calendar API
3. **CRUD endpoints + UI** — new API endpoints for create/update/delete, new EventForm component in frontend

---

## Data Model

### Migration 0004

**`calendar.calendar_sources`** — three new columns:

```sql
source_type        VARCHAR(16)  NOT NULL DEFAULT 'ical'
google_calendar_id TEXT         NULL
google_credentials JSONB        NULL
```

`google_credentials` stores: `{access_token, refresh_token, token_uri, client_id, client_secret, expiry}`

`ical_url` becomes nullable (existing iCal rows keep their URL; new Google sources have NULL).

**`calendar.events`** — one new column:

```sql
google_event_id    VARCHAR(512)  NULL
```

Used to identify the event in Google Calendar API for update/delete operations.

### CalendarSource types

- `source_type = "ical"` — existing read-only sources (iCal URL sync, no write-back)
- `source_type = "google"` — OAuth-connected Google Calendar sources (full CRUD)

---

## Backend

### New file: `backend/app/modules/calendar/google_service.py`

Isolates all Google API logic. Functions:

- `build_auth_url(state: str) -> str` — builds Google OAuth2 authorization URL with scopes `calendar.events` + `calendar.readonly`
- `exchange_code(code: str) -> dict` — exchanges authorization code for credentials dict
- `get_calendar_list(credentials: dict) -> list[dict]` — returns user's Google Calendars `[{id, summary, backgroundColor}]`
- `refresh_credentials(credentials: dict) -> dict` — refreshes access_token if expired, returns updated credentials
- `fetch_google_events(credentials: dict, calendar_id: str, from_dt: datetime, to_dt: datetime) -> list[dict]` — fetches events from Google Calendar API, returns normalized dicts matching Event model fields + `google_event_id`
- `create_google_event(credentials: dict, calendar_id: str, event_data: dict) -> str` — creates event, returns google_event_id
- `update_google_event(credentials: dict, calendar_id: str, google_event_id: str, event_data: dict) -> None`
- `delete_google_event(credentials: dict, calendar_id: str, google_event_id: str) -> None`

### Modified: `backend/app/modules/calendar/service.py`

`sync_source` branches on `source_type`:
- `"ical"` → existing iCal fetch + parse (unchanged)
- `"google"` → calls `google_service.fetch_google_events`, refreshes credentials if needed, upserts events with `google_event_id`

`sync_all_sources` unchanged — still iterates all active sources.

### Modified: `backend/app/modules/calendar/admin_router.py`

Two new endpoints for OAuth flow:

```
GET /api/admin/google/auth-url
```
Returns `{auth_url}`. Builds Google OAuth2 URL with `state` parameter (CSRF token stored in session or signed JWT).

```
GET /api/admin/google/callback?code=xxx&state=xxx
```
- Validates state
- Exchanges code for credentials
- Fetches user's calendar list from Google
- Stores credentials in a temp table `calendar.google_oauth_sessions` (TTL 10 min, keyed by a random session_token)
- Redirects to `/admin?google_session=<session_token>`

Frontend reads `google_session` param on page load → calls `GET /api/admin/google/session/{token}` → receives calendar list. When user selects calendar and submits:

```
POST /api/admin/google/connect
```
Body: `{session_token, calendar_id, name, color}` — backend looks up credentials from session, creates CalendarSource with `source_type="google"`, deletes session row, triggers immediate sync.

### Modified: `backend/app/modules/calendar/router.py`

Three new endpoints (all require auth):

```
POST /api/calendar/events
```
Body: `EventCreate` (see schemas). Creates event in Google Calendar via `google_service.create_google_event`, inserts into local DB with returned `google_event_id`. Returns `EventOut`.

```
PUT /api/calendar/events/{id}
```
Body: `EventUpdate`. Updates event in Google Calendar, updates local DB row. Returns `EventOut`.

```
DELETE /api/calendar/events/{id}
```
Deletes event from Google Calendar, deletes from local DB. Returns 204.

Events with no `google_event_id` (old iCal-synced events) cannot be edited via these endpoints — returns 409 with message "Aftalen kan ikke redigeres (importeret fra iCal)".

### Modified: `backend/app/modules/calendar/schemas.py`

New schemas:

```python
class EventCreate(BaseModel):
    title: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None   # e.g. 30 = 30 min before
    google_color_id: str | None = None    # Google color key e.g. "1" (tomato)
    source_id: int                        # which CalendarSource to create in

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

`EventOut` gains new fields:
```python
google_event_id: str | None = None
google_color_id: str | None = None   # Google color key e.g. "1" (tomato)
editable: bool = False               # True only when google_event_id is not None
```

### New: `backend/alembic/versions/0004_google_calendar.py`

Migration adds:
- `calendar_sources.source_type` VARCHAR(16) NOT NULL DEFAULT 'ical'
- `calendar_sources.google_calendar_id` TEXT NULL
- `calendar_sources.google_credentials` JSONB NULL
- `calendar_sources.ical_url` altered to nullable
- `events.google_event_id` VARCHAR(512) NULL

### Modified: `backend/app/core/config.py`

Two new settings:

```python
google_client_id: str = ""
google_client_secret: str = ""
google_redirect_uri: str = "https://mylife.smoelgaard.com/api/admin/google/callback"
```

### New Python packages

```
google-api-python-client==2.151.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
```

---

## Frontend

### Modified: `frontend/src/modules/calendar/calendarApi.ts`

`CalendarEvent` gains:
```ts
google_event_id: string | null
editable: boolean
```

New API functions:
```ts
createEvent(data: EventCreate): Promise<CalendarEvent>
updateEvent(id: number, data: EventUpdate): Promise<CalendarEvent>
deleteEvent(id: number): Promise<void>
```

New types:
```ts
interface EventCreate {
  title: string
  start_dt: string
  end_dt: string
  all_day: boolean
  source_id: number
  location?: string
  description?: string
  reminder_minutes?: number
  google_color_id?: string
}

interface EventUpdate {
  title?: string
  start_dt?: string
  end_dt?: string
  all_day?: boolean
  location?: string
  description?: string
  reminder_minutes?: number
  google_color_id?: string
}
```

### New: `frontend/src/modules/calendar/EventForm.tsx`

Shared form component for create and edit. Props:
```ts
interface Props {
  event?: CalendarEvent        // undefined = create mode, defined = edit mode
  sources: CalendarSource[]    // for calendar dropdown
  defaultSourceId?: number
  onSave: (event: CalendarEvent) => void
  onCancel: () => void
}
```

Fields rendered:
1. **Titel** — text input, required
2. **Kalender** — dropdown (only shown when creating, hidden when editing)
3. **Heldagsbegivenhed** — checkbox. When checked, hides time fields
4. **Dato** — date input
5. **Fra / Til** — time inputs (hidden when all-day)
6. **Sted** — text input
7. **Beskrivelse** — textarea
8. **Påmindelse** — dropdown: Ingen, 5 min, 10 min, 15 min, 30 min, 1 time, 1 dag før
9. **Farve** — 11 Google color circles:
   - Tomat (#D50000), Flamingo (#E67C73), Drue (#8E24AA), Blåbær (#3F51B5)
   - Hav (#039BE5), Salvie (#33B679), Basilikum (#0B8043), Avocado (#7CB342)
   - Fersken (#F6BF26), Banan (#F09300), Grafit (#616161)

Submit: shows spinner, calls `createEvent` or `updateEvent`, calls `onSave` with result.

### Modified: `frontend/src/modules/calendar/EventDetail.tsx`

When `event.editable === true`, show two buttons below the details:
- ✏️ **Rediger** — calls `onEdit` prop → parent switches to EventForm
- 🗑️ **Slet** — confirmation dialog → calls `deleteEvent` → calls `onDelete` prop

New props:
```ts
onEdit: () => void
onDelete: () => void
```

### Modified: `frontend/src/modules/calendar/CalendarPage.tsx`

New state:
```ts
const [mode, setMode] = useState<'view' | 'create' | 'edit'>('view')
const [sources, setSources] = useState<CalendarSource[]>([])
```

`useEffect` on mount fetches `getCalendarSources()` and stores in `sources` state (used for the calendar dropdown in EventForm).

Bottom panel logic:
- `mode === 'view'` → show `<EventDetail>` (or nothing if no selection)
- `mode === 'create'` → show `<EventForm>` (empty, with calendar dropdown)
- `mode === 'edit'` → show `<EventForm>` (pre-filled with selectedEvent)

"＋ Ny aftale" button in header → `setMode('create')`.

After save/delete/cancel → `setMode('view')`, refresh events for current month.

### Modified: `frontend/src/modules/admin/AdminPage.tsx`

"Tilføj kalender" section changes:

1. **iCal URL input removed**
2. **"Tilslut Google Kalender" button** → calls `GET /api/admin/google/auth-url` → redirects browser to returned URL
3. **After OAuth callback**, `/admin?google_calendars=xxx` param is present → show calendar picker:
   - Dropdown of user's Google Calendars (name + Google background color as hint)
   - Name input (pre-filled with calendar name)
   - Color picker (8 preset hex colors as before)
   - "Gem" button → calls `POST /api/admin/google/connect`

### Modified: `frontend/src/modules/admin/adminApi.ts`

New functions:
```ts
getGoogleAuthUrl(): Promise<{auth_url: string}>
getGoogleSession(token: string): Promise<{calendars: {id: string, name: string, color: string}[]}>
connectGoogleCalendar(data: {session_token: string, calendar_id: string, name: string, color: string}): Promise<CalendarSource>
```

---

## Google Cloud Setup (one-time, done by user)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project "Personal Dashboard"
3. Enable "Google Calendar API"
4. Create OAuth2 credentials (type: Web application)
5. Add authorized redirect URI: `https://mylife.smoelgaard.com/api/admin/google/callback`
6. Copy Client ID + Client Secret
7. Add to Coolify env vars: `GOOGLE_CLIENT_ID=...` and `GOOGLE_CLIENT_SECRET=...`

---

## Google Event Colors

Google Calendar uses numeric color IDs 1–11:

| ID | Name | Hex |
|----|------|-----|
| 1 | Tomat | #D50000 |
| 2 | Flamingo | #E67C73 |
| 3 | Drue | #8E24AA |
| 4 | Blåbær | #3F51B5 |
| 5 | Hav | #039BE5 |
| 6 | Salvie | #33B679 |
| 7 | Basilikum | #0B8043 |
| 8 | Avocado | #7CB342 |
| 9 | Fersken | #F6BF26 |
| 10 | Banan | #F09300 |
| 11 | Grafit | #616161 |

---

## Sync Behavior

- **Daily sync (APScheduler):** Fetches all events from Google Calendar for ±3 months, upserts into local DB. Token refreshed automatically.
- **After create/edit/delete:** Local DB updated immediately (no need to wait for next sync).
- **Conflict resolution:** Daily sync overwrites local data — last sync wins. Since this is a personal dashboard, concurrent edits from both places are acceptable with this simple strategy.
- **iCal sources:** Still supported in sync (existing rows with `source_type="ical"` continue to work read-only). No write-back.

---

## Error Handling

- **Token expired:** `google_service` catches `google.auth.exceptions.RefreshError`, returns 401 with `"Google Calendar-forbindelsen er udløbet — tilslut igen"`. Admin UI shows "Gentilslut" button.
- **Event not found in Google:** 404 from Google API → return 404 to frontend with `"Aftalen findes ikke i Google Calendar"`
- **No google_event_id:** Editing iCal-imported events returns 409 `"Aftalen kan ikke redigeres (importeret fra iCal)"`
- **Network failure during create:** If Google API call succeeds but DB insert fails → attempt to delete the Google event before returning 500

---

## What Is NOT Included

- Recurring events (RRULE) — editing recurrence is very complex
- Attendees/invitations — requires additional API scopes and email handling
- Google Meet links — requires separate conferencing API scope
- Timezone selection per event — all times stored/displayed in UTC
- CalDAV support for non-Google calendars
- Multiple Google accounts — one OAuth connection per source, all from the same Google account
