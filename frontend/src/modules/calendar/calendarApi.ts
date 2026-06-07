import { api } from '../../api/client'

export interface CalendarEvent {
  id: number
  uid: string
  title: string
  start_dt: string   // ISO 8601 UTC
  end_dt: string
  all_day: boolean
  location: string | null
  description: string | null
  source: string
}

export async function getUpcomingEvents(limit = 5): Promise<CalendarEvent[]> {
  return api.get<CalendarEvent[]>(`/calendar/events?upcoming=true&limit=${limit}`)
}

export async function getEventsInRange(from: Date, to: Date): Promise<CalendarEvent[]> {
  const fromStr = from.toISOString()
  const toStr = to.toISOString()
  return api.get<CalendarEvent[]>(`/calendar/events?from_dt=${fromStr}&to_dt=${toStr}`)
}

export async function syncCalendar(): Promise<{ synced: number }> {
  return api.post<{ synced: number }>('/calendar/sync')
}
