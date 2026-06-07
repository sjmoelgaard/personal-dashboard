import { useEffect, useState, type FormEvent } from 'react'
import type { CalendarSource, CalendarSourceCreate } from './adminApi'
import { createCalendarSource, deleteCalendarSource, getCalendarSources } from './adminApi'

const PRESET_COLORS = [
  '#eab308', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#f97316', '#06b6d4', '#ec4899',
]

export function AdminPage() {
  const [sources, setSources] = useState<CalendarSource[]>([])
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [color, setColor] = useState('#3b82f6')
  const [adding, setAdding] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    getCalendarSources().then(setSources).catch(() => setSources([]))
  }, [])

  async function handleAdd(e: FormEvent) {
    e.preventDefault()
    setAdding(true)
    setMsg('')
    try {
      const data: CalendarSourceCreate = { name, ical_url: url, color }
      const source = await createCalendarSource(data)
      setSources(prev => [...prev, source])
      setName('')
      setUrl('')
      setMsg('Kalender tilføjet og synkroniseret')
    } catch {
      setMsg('Fejl ved tilføjelse — tjek at URL er en gyldig iCal-adresse')
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Slet kalender og alle dens aftaler?')) return
    try {
      await deleteCalendarSource(id)
      setSources(prev => prev.filter(s => s.id !== id))
    } catch {
      setMsg('Fejl ved sletning')
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold text-white mb-6">Kalender-kilder</h2>

      {/* Liste */}
      <div className="space-y-2 mb-8">
        {sources.length === 0 && (
          <p className="text-gray-500 text-sm">Ingen kalender-kilder endnu.</p>
        )}
        {sources.map(s => (
          <div
            key={s.id}
            className="flex items-center justify-between bg-gray-900 rounded-lg p-4"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-4 h-4 rounded-full shrink-0"
                style={{ backgroundColor: s.color }}
              />
              <div className="min-w-0">
                <div className="text-white text-sm font-medium">{s.name}</div>
                <div className="text-gray-500 text-xs truncate">{s.ical_url}</div>
              </div>
            </div>
            <button
              onClick={() => handleDelete(s.id)}
              className="text-gray-500 hover:text-red-400 text-sm transition-colors ml-4 shrink-0"
            >
              Slet
            </button>
          </div>
        ))}
      </div>

      {/* Tilføj formular */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h3 className="text-white font-medium mb-4">Tilføj kalender</h3>
        <form onSubmit={handleAdd} className="space-y-4">
          <input
            type="text"
            placeholder="Navn (f.eks. Privat)"
            value={name}
            onChange={e => setName(e.target.value)}
            required
            className="w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="url"
            placeholder="iCal URL (https://calendar.google.com/...)"
            value={url}
            onChange={e => setUrl(e.target.value)}
            required
            className="w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div>
            <div className="text-gray-400 text-xs mb-2">Farve</div>
            <div className="flex gap-2 flex-wrap">
              {PRESET_COLORS.map(c => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`w-7 h-7 rounded-full transition-transform ${
                    color === c
                      ? 'scale-125 ring-2 ring-white ring-offset-2 ring-offset-gray-900'
                      : 'hover:scale-110'
                  }`}
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={adding}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm px-5 py-2 rounded-lg transition-colors"
            >
              {adding ? 'Tilføjer og synkroniserer...' : 'Tilføj'}
            </button>
            {msg && <span className="text-sm text-gray-400">{msg}</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
