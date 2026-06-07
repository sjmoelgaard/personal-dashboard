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
