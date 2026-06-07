import { api } from '../../api/client'

export interface CalendarSource {
  id: number
  name: string
  ical_url: string
  color: string
  is_active: boolean
  created_at: string
}

export interface CalendarSourceCreate {
  name: string
  ical_url: string
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
