import { useEffect, useState } from 'react'
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isToday,
  parseISO,
  isSameDay,
  addMonths,
  subMonths,
} from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { getEventsInRange, syncCalendar } from './calendarApi'

export function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const calEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: calStart, end: calEnd })

  useEffect(() => {
    getEventsInRange(calStart, calEnd)
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [currentMonth])

  function eventsOnDay(day: Date): CalendarEvent[] {
    return events.filter(e => isSameDay(parseISO(e.start_dt), day))
  }

  async function handleSync() {
    setSyncing(true)
    setSyncMsg('')
    try {
      const result = await syncCalendar()
      setSyncMsg(`${result.synced} events synkroniseret`)
      const fresh = await getEventsInRange(calStart, calEnd)
      setEvents(fresh)
    } catch {
      setSyncMsg('Sync fejlede — tjek ICAL_URL i .env')
    } finally {
      setSyncing(false)
    }
  }

  const weekDays = ['Man', 'Tir', 'Ons', 'Tor', 'Fre', 'Lør', 'Søn']

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="text-gray-400 hover:text-white px-2 py-1 rounded"
          >
            ←
          </button>
          <h2 className="text-xl font-semibold capitalize">
            {format(currentMonth, 'MMMM yyyy', { locale: da })}
          </h2>
          <button
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="text-gray-400 hover:text-white px-2 py-1 rounded"
          >
            →
          </button>
        </div>
        <div className="flex items-center gap-3">
          {syncMsg && <span className="text-sm text-gray-400">{syncMsg}</span>}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="text-sm bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 text-white px-4 py-2 rounded-lg transition-colors"
          >
            {syncing ? 'Synkroniserer...' : '↻ Sync'}
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-px bg-gray-800 rounded-xl overflow-hidden">
        {weekDays.map(d => (
          <div key={d} className="bg-gray-900 text-center text-xs text-gray-500 py-2 font-medium">
            {d}
          </div>
        ))}
        {days.map(day => {
          const dayEvents = eventsOnDay(day)
          const inMonth = isSameMonth(day, currentMonth)
          const today = isToday(day)
          return (
            <div
              key={day.toISOString()}
              className={`bg-gray-900 min-h-[80px] p-2 ${!inMonth ? 'opacity-30' : ''}`}
            >
              <div
                className={`text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                  today ? 'bg-blue-600 text-white' : 'text-gray-400'
                }`}
              >
                {format(day, 'd')}
              </div>
              {dayEvents.slice(0, 3).map(e => (
                <div
                  key={e.id}
                  className="text-xs bg-yellow-400 text-gray-900 rounded px-1 py-0.5 mb-0.5 truncate font-medium"
                  title={e.title}
                >
                  {!e.all_day && (
                    <span className="opacity-70 mr-1">
                      {format(parseISO(e.start_dt), 'HH:mm')}
                    </span>
                  )}
                  {e.title}
                </div>
              ))}
              {dayEvents.length > 3 && (
                <div className="text-xs text-gray-500">+{dayEvents.length - 3} mere</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
