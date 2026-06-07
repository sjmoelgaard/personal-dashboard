import { Nav } from '../components/Nav'
import { AdminPage } from '../modules/admin/AdminPage'

export function Admin() {
  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <Nav />
        <AdminPage />
      </div>
    </div>
  )
}
