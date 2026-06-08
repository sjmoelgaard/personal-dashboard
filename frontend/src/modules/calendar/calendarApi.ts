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
