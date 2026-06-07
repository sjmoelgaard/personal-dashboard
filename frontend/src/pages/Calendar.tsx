import { Nav } from '../components/Nav'
import { CalendarPage } from '../modules/calendar/CalendarPage'

export function Calendar() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <Nav />
        <CalendarPage />
      </div>
    </div>
  )
}
