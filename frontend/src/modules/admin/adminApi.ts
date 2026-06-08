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
