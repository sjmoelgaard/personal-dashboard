import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client'

interface AuthState {
  user: string | null
  loading: boolean
  login: (password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<{ user: string }>('/auth/me')
      .then(data => { setUser(data.user); setLoading(false) })
      .catch(() => { setUser(null); setLoading(false) })
  }, [])

  const login = useCallback(async (password: string) => {
    await api.post('/auth/login', { password })
    const data = await api.get<{ user: string }>('/auth/me')
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    await api.post('/auth/logout')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
