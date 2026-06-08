import { differenceInMinutes, format, parseISO } from 'date-fns'
import { da } from 'date-fns/locale'
import type { CalendarEvent } from './calendarApi'
import { deleteEvent } from './calendarApi'

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

function formatReminder(minutes: number): string {
  if (minutes < 60) return `${minutes} min før`
  if (minutes === 60) return '1 time før'
  if (minutes === 1440) return '1 dag før'
  return `${minutes} min før`
}

interface Props {
  event: CalendarEvent | null
  onEdit: () => void
  onDelete: () => void
}

export function EventDetail({ event, onEdit, onDelete }: Props) {
  if (!event) return null

  const borderColor = event.source_color ?? '#eab308'

  async function handleDelete() {
    if (!confirm(`Slet "${event!.title}"?`)) return
    try {
      await deleteEvent(event!.id)
      onDelete()
    } catch {
      alert('Kunne ikke slette aftalen')
    }
  }

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
        {event.reminder_minutes != null && (
          <div className="flex gap-3">
            <span className="text-gray-500 w-24 shrink-0">Påmindelse</span>
            <span className="text-gray-200">{formatReminder(event.reminder_minutes)}</span>
          </div>
        )}
      </div>

      {event.editable && (
        <div className="flex gap-3 mt-4 pt-4 border-t border-gray-800">
          <button
            onClick={onEdit}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            ✏️ Rediger
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            🗑️ Slet
          </button>
        </div>
      )}
    </div>
  )
}
