import { Nav } from '../components/Nav'
import { UpcomingEvents } from '../modules/calendar/UpcomingEvents'

export function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <Nav />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <UpcomingEvents />
          {/* Finans, Sundhed, Karriere KPI-kort tilføjes i Phase 3-5 */}
          <div className="bg-gray-900 rounded-xl p-5 border-l-4 border-blue-400">
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-3">Finans</div>
            <div className="text-gray-500 text-sm">Bygges i Phase 4</div>
          </div>
          <div className="bg-gray-900 rounded-xl p-5 border-l-4 border-red-400">
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-3">Sundhed</div>
            <div className="text-gray-500 text-sm">Bygges i Phase 3</div>
          </div>
          <div className="bg-gray-900 rounded-xl p-5 border-l-4 border-purple-400">
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-3">Karriere</div>
            <div className="text-gray-500 text-sm">Bygges i Phase 5</div>
          </div>
        </div>
      </div>
    </div>
  )
}
