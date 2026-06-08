import { useEffect, useState } from 'react'
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { getEventsInRange, syncCalendar } from './calendarApi'
import { EventDetail } from './EventDetail'
import { EventForm } from './EventForm'
import { resolveEventColor } from './googleColors'
import type { CalendarSource } from '../admin/adminApi'
import { getCalendarSources } from '../admin/adminApi'

type Mode = 'view' | 'create' | 'edit'

export function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const [mode, setMode] = useState<Mode>('view')
  const [sources, setSources] = useState<CalendarSource[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const calEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: calStart, end: calEnd })

  useEffect(() => {
    getCalendarSources().then(setSources).catch(() => setSources([]))
  }, [])

  useEffect(() => {
    setSelectedEvent(null)
    setMode('view')
    getEventsInRange(calStart, calEnd)
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [currentMonth])

  async function refreshEvents() {
    try {
      const fresh = await getEventsInRange(calStart, calEnd)
      setEvents(fresh)
    } catch {
      // ignore
    }
  }

  function eventsOnDay(day: Date): CalendarEvent[] {
    return events.filter(e => isSameDay(parseISO(e.start_dt), day))
  }

  function handleEventClick(e: CalendarEvent) {
    setSelectedEvent(prev => (prev?.id === e.id ? null : e))
    setMode('view')
  }

  async function handleSync() {
    setSyncing(true)
    setSyncMsg('')
    try {
      const result = await syncCalendar()
      setSyncMsg(`${result.synced} events synkroniseret`)
      await refreshEvents()
    } catch {
      setSyncMsg('Sync fejlede')
    } finally {
      setSyncing(false)
    }
  }

  function handleSave(saved: CalendarEvent) {
    setMode('view')
    setSelectedEvent(saved)
    refreshEvents()
  }

  function handleDelete() {
    setMode('view')
    setSelectedEvent(null)
    refreshEvents()
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
            onClick={() => {
              setMode('create')
              setSelectedEvent(null)
            }}
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            + Ny aftale
          </button>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="text-sm bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 text-white px-4 py-2 rounded-lg transition-colors"
          >
            {syncing ? 'Synkroniserer...' : '↻ Sync'}
          </button>
        </div>
      </div>

      {/* Kalender grid */}
      <div className="grid grid-cols-7 gap-px bg-gray-800 rounded-xl overflow-hidden">
        {weekDays.map(d => (
          <div
            key={d}
            className="bg-gray-900 text-center text-xs text-gray-500 py-2 font-medium"
          >
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
              {dayEvents.slice(0, 3).map(e => {
                const color = resolveEventColor(e)
                const isSelected = selectedEvent?.id === e.id
                return (
                  <button
                    key={e.id}
                    onClick={() => handleEventClick(e)}
                    className={`w-full text-left text-xs rounded px-1 py-0.5 mb-0.5 truncate font-medium transition-opacity ${
                      isSelected ? 'ring-2 ring-white ring-offset-1 ring-offset-gray-900' : 'hover:opacity-80'
                    }`}
                    style={{ backgroundColor: color, color: '#111827' }}
                    title={e.title}
                  >
                    {!e.all_day && (
                      <span className="opacity-70 mr-1">
                        {format(parseISO(e.start_dt), 'HH:mm')}
                      </span>
                    )}
                    {e.title}
                  </button>
                )
              })}
              {dayEvents.length > 3 && (
                <div className="text-xs text-gray-500">+{dayEvents.length - 3} mere</div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom panel */}
      {mode === 'view' && selectedEvent && (
        <EventDetail
          event={selectedEvent}
          onEdit={() => setMode('edit')}
          onDelete={handleDelete}
        />
      )}
      {mode === 'create' && (
        <EventForm
          sources={sources}
          onSave={handleSave}
          onCancel={() => setMode('view')}
        />
      )}
      {mode === 'edit' && selectedEvent && (
        <EventForm
          event={selectedEvent}
          sources={sources}
          onSave={handleSave}
          onCancel={() => setMode('view')}
        />
      )}
    </div>
  )
}
