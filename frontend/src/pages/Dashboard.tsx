import { useAuth } from '../hooks/useAuth'

export function Dashboard() {
  const { logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-semibold">Mit Dashboard</h1>
          <button
            onClick={logout}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Log ud
          </button>
        </div>
        <p className="text-gray-500">Moduler bygges i de næste faser.</p>
      </div>
    </div>
  )
}
