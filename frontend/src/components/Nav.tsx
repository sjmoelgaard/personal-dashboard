import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const links = [
  { to: '/', label: 'Forside' },
  { to: '/kalender', label: '📅 Kalender' },
]

export function Nav() {
  const { logout } = useAuth()
  const { pathname } = useLocation()

  return (
    <nav className="flex items-center justify-between mb-8">
      <div className="flex items-center gap-6">
        <span className="text-white font-semibold text-lg">Mit Dashboard</span>
        {links.map(link => (
          <Link
            key={link.to}
            to={link.to}
            className={`text-sm transition-colors ${
              pathname === link.to
                ? 'text-white font-medium'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <button
        onClick={logout}
        className="text-sm text-gray-400 hover:text-white transition-colors"
      >
        Log ud
      </button>
    </nav>
  )
}
