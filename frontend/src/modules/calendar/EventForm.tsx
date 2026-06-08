import { useState, type FormEvent } from 'react'
import { format } from 'date-fns'
import type { CalendarEvent, EventCreate, EventUpdate } from './calendarApi'
import { createEvent, updateEvent } from './calendarApi'
import type { CalendarSource } from '../admin/adminApi'
import { GOOGLE_COLORS, GOOGLE_COLOR_NAMES } from './googleColors'

interface Props {
  event?: CalendarEvent       // undefined = create mode
  sources: CalendarSource[]
  defaultSourceId?: number
  onSave: (event: CalendarEvent) => void
  onCancel: () => void
}

const REMINDER_OPTIONS = [
  { label: 'Ingen', value: null },
  { label: '5 min', value: 5 },
  { label: '10 min', value: 10 },
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 time', value: 60 },
  { label: '1 dag', value: 1440 },
]

function toLocalDateString(isoString: string): string {
  return isoString.slice(0, 10)
}

function toLocalTimeString(isoString: string): string {
  return isoString.slice(11, 16)
}

export function EventForm({ event, sources, defaultSourceId, onSave, onCancel }: Props) {
  const isEdit = event !== undefined
  const googleSources = sources.filter(s => s.source_type === 'google')

  const [title, setTitle] = useState(event?.title ?? '')
  const [sourceId, setSourceId] = useState<number>(
    event?.source_id ?? defaultSourceId ?? googleSources[0]?.id ?? 0
  )
  const [allDay, setAllDay] = useState(event?.all_day ?? false)
  const [date, setDate] = useState(
    event ? toLocalDateString(event.start_dt) : format(new Date(), 'yyyy-MM-dd')
  )
  const [startTime, setStartTime] = useState(
    event && !event.all_day ? toLocalTimeString(event.start_dt) : '09:00'
  )
  const [endTime, setEndTime] = useState(
    event && !event.all_day ? toLocalTimeString(event.end_dt) : '10:00'
  )
  const [location, setLocation] = useState(event?.location ?? '')
  const [description, setDescription] = useState(event?.description ?? '')
  const [reminderMinutes, setReminderMinutes] = useState<number | null>(
    event?.reminder_minutes ?? null
  )
  const [colorId, setColorId] = useState<string | null>(event?.google_color_id ?? null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    setError('')

    try {
      const startIso = allDay
        ? `${date}T00:00:00.000Z`
        : `${date}T${startTime}:00.000Z`
      const endIso = allDay
        ? `${date}T00:00:00.000Z`
        : `${date}T${endTime}:00.000Z`

      let saved: CalendarEvent
      if (isEdit && event) {
        const payload: EventUpdate = {
          title: title.trim(),
          start_dt: startIso,
          end_dt: endIso,
          all_day: allDay,
          location: location.trim() || null,
          description: description.trim() || null,
          reminder_minutes: reminderMinutes,
          google_color_id: colorId,
        }
        saved = await updateEvent(event.id, payload)
      } else {
        const payload: EventCreate = {
          title: title.trim(),
          start_dt: startIso,
          end_dt: endIso,
          all_day: allDay,
          source_id: sourceId,
          location: location.trim() || null,
          description: description.trim() || null,
          reminder_minutes: reminderMinutes,
          google_color_id: colorId,
        }
        saved = await createEvent(payload)
      }
      onSave(saved)
    } catch {
      setError('Kunne ikke gemme aftalen — prøv igen')
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    'w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const labelClass = 'text-gray-400 text-xs mb-1 block'

  return (
    <div className="mt-4 bg-gray-900 rounded-xl p-5">
      <h3 className="text-white font-semibold text-lg mb-4">
        {isEdit ? 'Rediger aftale' : 'Ny aftale'}
      </h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Titel */}
        <div>
          <label className={labelClass}>Titel *</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            required
            placeholder="Titel"
            className={inputClass}
          />
        </div>

        {/* Kalender (create only) */}
        {!isEdit && (
          <div>
            <label className={labelClass}>Kalender</label>
            {googleSources.length === 0 ? (
              <p className="text-yellow-400 text-sm">
                Ingen Google Kalender tilsluttet — tilslut under Admin
              </p>
            ) : (
              <select
                value={sourceId}
                onChange={e => setSourceId(Number(e.target.value))}
                className={inputClass}
              >
                {googleSources.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Heldagsbegivenhed */}
        <div className="flex items-center gap-3">
          <input
            id="allDay"
            type="checkbox"
            checked={allDay}
            onChange={e => setAllDay(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="allDay" className="text-gray-300 text-sm">
            Heldagsbegivenhed
          </label>
        </div>

        {/* Dato */}
        <div>
          <label className={labelClass}>Dato</label>
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            required
            className={inputClass}
          />
        </div>

        {/* Fra / Til */}
        {!allDay && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Fra</label>
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                required
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Til</label>
              <input
                type="time"
                value={endTime}
                onChange={e => setEndTime(e.target.value)}
                required
                className={inputClass}
              />
            </div>
          </div>
        )}

        {/* Sted */}
        <div>
          <label className={labelClass}>Sted</label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Valgfrit"
            className={inputClass}
          />
        </div>

        {/* Beskrivelse */}
        <div>
          <label className={labelClass}>Beskrivelse</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Valgfrit"
            rows={3}
            className={inputClass + ' resize-none'}
          />
        </div>

        {/* Påmindelse */}
        <div>
          <label className={labelClass}>Påmindelse</label>
          <select
            value={reminderMinutes ?? ''}
            onChange={e =>
              setReminderMinutes(e.target.value === '' ? null : Number(e.target.value))
            }
            className={inputClass}
          >
            {REMINDER_OPTIONS.map(opt => (
              <option key={String(opt.value)} value={opt.value ?? ''}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Farve */}
        <div>
          <label className={labelClass}>Farve</label>
          <div className="flex gap-2 flex-wrap">
            {/* No color option */}
            <button
              type="button"
              onClick={() => setColorId(null)}
              className={`w-7 h-7 rounded-full border-2 transition-transform ${
                colorId === null
                  ? 'scale-125 border-white'
                  : 'border-gray-600 hover:scale-110'
              } bg-gray-600`}
              title="Kalenderfarve"
            />
            {Object.entries(GOOGLE_COLORS).map(([id, hex]) => (
              <button
                key={id}
                type="button"
                onClick={() => setColorId(id)}
                className={`w-7 h-7 rounded-full transition-transform ${
                  colorId === id
                    ? 'scale-125 ring-2 ring-white ring-offset-2 ring-offset-gray-900'
                    : 'hover:scale-110'
                }`}
                style={{ backgroundColor: hex }}
                title={GOOGLE_COLOR_NAMES[id]}
              />
            ))}
          </div>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || (!isEdit && googleSources.length === 0)}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm px-5 py-2 rounded-lg transition-colors"
          >
            {saving ? 'Gemmer...' : 'Gem'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="text-gray-400 hover:text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            Annuller
          </button>
        </div>
      </form>
    </div>
  )
}
