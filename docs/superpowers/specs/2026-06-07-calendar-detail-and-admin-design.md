# Calendar Detail Panel & Admin — Design Spec

**Date:** 2026-06-07
**Status:** Approved

---

## Goal

Two features built together:
1. **Event detail panel** — click an event in the month grid, see full details below the calendar without navigating away
2. **Admin section** — manage multiple iCal calendar sources (name, URL, color) through a UI; events colored by source

---

## Data Model

### New table: `calendar.calendar_sources`

```sql
id          SERIAL PRIMARY KEY
name        VARCHAR(128) NOT NULL
ical_url    TEXT NOT NULL
color       VARCHAR(7) NOT NULL DEFAULT '#eab308'  -- hex color
is_active   BOOLEAN NOT NULL DEFAULT true
created_at  TIMESTAMPTZ DEFAULT now()
```

### Modified table: `calendar.events`

Add column:
```sql
source_id   INTEGER REFERENCES calendar.calendar_sources(id) ON DELETE CASCADE
```

(Nullable — existing events without a source keep `NULL` until re-synced.)

---

## Backend

### New files

**`backend/app/modules/calendar/source_models.py`**
SQLAlchemy `CalendarSource` model.

**`backend/app/modules/calendar/source_schemas.py`**
Pydantic schemas: `CalendarSourceOut`, `CalendarSourceCreate`.

**`backend/app/modules/calendar/admin_router.py`**
CRUD endpoints, all require auth:
- `GET /api/admin/calendar-sources` → list all sources
- `POST /api/admin/calendar-sources` → create source (triggers sync of just that source)
- `DELETE /api/admin/calendar-sources/{id}` → delete source (and its events)

### Modified files

**`backend/app/modules/calendar/service.py`**
- `sync_calendar(db, ical_url, source_id)` — sets `source_id` on upserted events
- `sync_all_sources(db)` — fetches all active sources, calls `sync_calendar` for each
- `sync_source(db, source_id)` — syncs a single source by ID (used after create)
- Remove dependency on `settings.ical_url` — sources come from DB now

**`backend/app/modules/calendar/schemas.py`**
`EventOut` gains `source_id: int | None` and `source_color: str | None` (joined from CalendarSource).

**`backend/app/modules/calendar/router.py`**
`GET /api/calendar/events` — join CalendarSource to include `source_color` in response.

**`backend/main.py`**
Mount `admin_router` at `/api/admin`. Update scheduler to call `sync_all_sources`.

**`backend/alembic/versions/0003_calendar_sources.py`**
Migration: create `calendar_sources` table, add `source_id` column to `events`.

**`backend/app/core/models.py`**
Import `source_models` so Alembic finds it.

---

## Frontend

### New files

**`frontend/src/modules/calendar/adminApi.ts`**
API functions: `getCalendarSources`, `createCalendarSource`, `deleteCalendarSource`.

Types: `CalendarSource { id, name, ical_url, color, is_active, created_at }`.

**`frontend/src/modules/calendar/EventDetail.tsx`**
Detail panel shown below the calendar grid when an event is selected.
Shows: title, date + time (formatted in Danish), duration (calculated), location, description.
Left border colored with `source_color`. Hidden when no event selected.

**`frontend/src/pages/Admin.tsx`**
Page wrapper with Nav + AdminPage component.

**`frontend/src/modules/admin/AdminPage.tsx`**
Calendar sources list with:
- Color chip + name + truncated URL per row
- Delete button per row (with confirmation)
- "Tilføj kalender" form: name input, URL input, color picker (8 preset hex colors), submit button
- After submit: calls sync for new source, shows count

### Modified files

**`frontend/src/modules/calendar/CalendarPage.tsx`**
- `selectedEvent: CalendarEvent | null` state
- Clicking an event chip sets `selectedEvent` (clicking same event deselects)
- Event chips use `source_color` instead of hardcoded `bg-yellow-400`
- Renders `<EventDetail event={selectedEvent} />` below the grid

**`frontend/src/modules/calendar/calendarApi.ts`**
`CalendarEvent` gains `source_id: number | null` and `source_color: string | null`.

**`frontend/src/components/Nav.tsx`**
Add "⚙️ Admin" link to `/admin`.

**`frontend/src/App.tsx`**
Add `/admin` protected route.

---

## Color picker

8 preset colors (Tailwind-inspired):
- `#eab308` gul
- `#3b82f6` blå
- `#10b981` grøn
- `#ef4444` rød
- `#8b5cf6` lilla
- `#f97316` orange
- `#06b6d4` cyan
- `#ec4899` pink

Rendered as colored circles — click to select.

---

## Sync behavior

- **After adding a source:** immediately sync that source alone, return event count to UI
- **Daily scheduler:** calls `sync_all_sources` (replaces old `run_calendar_sync`)
- **Manual sync button on calendar page:** calls `POST /api/calendar/sync` which now calls `sync_all_sources`
- **Delete source:** deletes source row; events with that `source_id` get `source_id = NULL` (ON DELETE SET NULL), then a cleanup deletes orphaned events

---

## Migration chain

```
0001 (initial) → 0002 (calendar events) → 0003 (calendar sources + source_id on events)
```

---

## What is NOT included

- Editing a source (name/URL/color) — delete and re-add
- Reordering sources
- Per-source enable/disable toggle (all active sources always sync)
- Import from CalDAV or other protocols
