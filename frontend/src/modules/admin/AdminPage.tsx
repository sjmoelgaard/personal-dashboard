import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { CalendarSource } from './adminApi'
import {
  connectGoogleCalendar,
  deleteCalendarSource,
  getCalendarSources,
  getGoogleAuthUrl,
  getGoogleSession,
} from './adminApi'

const PRESET_COLORS = [
  '#eab308', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#f97316', '#06b6d4', '#ec4899',
]

interface GoogleCalendarOption {
  id: string
  name: string
  color: string
}

export function AdminPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [sources, setSources] = useState<CalendarSource[]>([])
  const [msg, setMsg] = useState('')

  // Google OAuth connect state
  const googleSession = searchParams.get('google_session')
  const googleError = searchParams.get('google_error')
  const [googleCalendars, setGoogleCalendars] = useState<GoogleCalendarOption[]>([])
  const [selectedCalendarId, setSelectedCalendarId] = useState('')
  const [connectName, setConnectName] = useState('')
  const [connectColor, setConnectColor] = useState('#3b82f6')
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    getCalendarSources().then(setSources).catch(() => setSources([]))
  }, [])

  useEffect(() => {
    if (googleSession) {
      getGoogleSession(googleSession)
        .then(data => {
          setGoogleCalendars(data.calendars)
          if (data.calendars.length > 0) {
            setSelectedCalendarId(data.calendars[0].id)
            setConnectName(data.calendars[0].name)
          }
        })
        .catch(() => setMsg('Kunne ikke hente kalender-liste fra Google'))
    }
  }, [googleSession])

  async function handleGoogleConnect(e: FormEvent) {
    e.preventDefault()
    if (!googleSession || !selectedCalendarId) return
    setConnecting(true)
    setMsg('')
    try {
      const source = await connectGoogleCalendar({
        session_token: googleSession,
        calendar_id: selectedCalendarId,
        name: connectName,
        color: connectColor,
      })
      setSources(prev => [...prev, source])
      setSearchParams({})  // Remove query params
      setGoogleCalendars([])
      setMsg('Google Kalender tilsluttet og synkroniseret')
    } catch {
      setMsg('Fejl ved tilslutning — prøv igen')
    } finally {
      setConnecting(false)
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

  async function handleGoogleAuth() {
    try {
      const { auth_url } = await getGoogleAuthUrl()
      window.location.href = auth_url
    } catch {
      setMsg('Kunne ikke starte Google-forbindelsen')
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold text-white mb-6">Kalender-kilder</h2>

      {/* Fejlbesked fra OAuth redirect */}
      {googleError && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-4 mb-6 text-red-300 text-sm">
          Google-forbindelsen fejlede ({googleError}) — prøv igen.
        </div>
      )}

      {/* Eksisterende sources */}
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
                <div className="text-gray-500 text-xs">
                  {s.source_type === 'google' ? '🔗 Google Calendar' : s.ical_url}
                </div>
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

      {/* Google OAuth connect form (shown after OAuth callback) */}
      {googleSession && googleCalendars.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-5 mb-6">
          <h3 className="text-white font-medium mb-4">Vælg Google Kalender</h3>
          <form onSubmit={handleGoogleConnect} className="space-y-4">
            <div>
              <label className="text-gray-400 text-xs mb-1 block">Kalender</label>
              <select
                value={selectedCalendarId}
                onChange={e => {
                  const cal = googleCalendars.find(c => c.id === e.target.value)
                  setSelectedCalendarId(e.target.value)
                  if (cal) setConnectName(cal.name)
                }}
                className="w-full bg-gray-800 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {googleCalendars.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              placeholder="Navn"
              value={connectName}
              onChange={e => setConnectName(e.target.value)}
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
                    onClick={() => setConnectColor(c)}
                    className={`w-7 h-7 rounded-full transition-transform ${
                      connectColor === c
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
                disabled={connecting}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm px-5 py-2 rounded-lg transition-colors"
              >
                {connecting ? 'Tilslutter...' : 'Gem'}
              </button>
              <button
                type="button"
                onClick={() => setSearchParams({})}
                className="text-gray-400 hover:text-white text-sm"
              >
                Annuller
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tilføj Google Kalender */}
      {!googleSession && (
        <div className="bg-gray-900 rounded-xl p-5">
          <h3 className="text-white font-medium mb-4">Tilføj kalender</h3>
          <button
            onClick={handleGoogleAuth}
            className="flex items-center gap-2 bg-white hover:bg-gray-100 text-gray-900 text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Tilslut Google Kalender
          </button>
          {msg && <p className="text-sm text-gray-400 mt-3">{msg}</p>}
        </div>
      )}
    </div>
  )
}
