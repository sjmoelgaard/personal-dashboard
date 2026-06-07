import { useEffect, useState } from 'react'
import { format, isToday, isTomorrow, parseISO } from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { getUpcomingEvents } from './calendarApi'

function formatEventDate(isoString: string, allDay: boolean): string {
  const dt = parseISO(isoString)
  if (isToday(dt)) return allDay ? 'I dag' : `I dag ${format(dt, 'HH:mm')}`
  if (isTomorrow(dt)) return allDay ? 'I morgen' : `I morgen ${format(dt, 'HH:mm')}`
  return allDay
    ? format(dt, 'd. MMM', { locale: da })
    : format(dt, 'd. MMM HH:mm', { locale: da })
}

export function UpcomingEvents() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getUpcomingEvents(3)
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="bg-gray-900 rounded-xl p-5 border-l-4 border-yellow-400">
      <div className="text-xs text-gray-400 uppercase tracking-widest mb-3">Kalender</div>
      {loading && <div className="text-gray-500 text-sm">Henter aftaler...</div>}
      {!loading && events.length === 0 && (
        <div className="text-gray-500 text-sm">Ingen kommende aftaler</div>
      )}
      {!loading && events.length > 0 && (
        <ul className="space-y-2">
          {events.map(event => (
            <li key={event.id} className="flex justify-between items-start gap-4">
              <span className="text-white text-sm font-medium truncate">{event.title}</span>
              <span className="text-yellow-400 text-xs whitespace-nowrap">
                {formatEventDate(event.start_dt, event.all_day)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
