import { differenceInMinutes, format, parseISO } from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'

function formatDuration(start: string, end: string, allDay: boolean): string {
  if (allDay) return 'Heldagsbegivenhed'
  const minutes = differenceInMinutes(parseISO(end), parseISO(start))
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remaining = minutes % 60
  return remaining > 0 ? `${hours} t ${remaining} min` : `${hours} t`
}

function formatDate(isoString: string, allDay: boolean): string {
  const dt = parseISO(isoString)
  return allDay
    ? format(dt, 'd. MMMM yyyy', { locale: da })
    : format(dt, 'd. MMMM yyyy HH:mm', { locale: da })
}

interface Props {
  event: CalendarEvent | null
}

export function EventDetail({ event }: Props) {
  if (!event) return null

  const borderColor = event.source_color ?? '#eab308'

  return (
    <div
      className="mt-4 bg-gray-900 rounded-xl p-5 border-l-4"
      style={{ borderColor }}
    >
      <h3 className="text-white font-semibold text-lg mb-3">{event.title}</h3>
      <div className="space-y-2 text-sm">
        <div className="flex gap-3">
          <span className="text-gray-500 w-24 shrink-0">Dato</span>
          <span className="text-gray-200">{formatDate(event.start_dt, event.all_day)}</span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-500 w-24 shrink-0">Varighed</span>
          <span className="text-gray-200">
            {formatDuration(event.start_dt, event.end_dt, event.all_day)}
          </span>
        </div>
        {event.location && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Sted</span>
            <span className="text-gray-200">{event.location}</span>
          </div>
        )}
        {event.description && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Beskrivelse</span>
            <span className="text-gray-200 whitespace-pre-wrap break-words">
              {event.description}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
