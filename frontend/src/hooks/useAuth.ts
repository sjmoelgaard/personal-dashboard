import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface AuthState {
  user: string | null
  loading: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({ user: null, loading: true })

  useEffect(() => {
    api.get<{ user: string }>('/auth/me')
      .then(data => setState({ user: data.user, loading: false }))
      .catch(() => setState({ user: null, loading: false }))
  }, [])

  const login = useCallback(async (password: string) => {
    await api.post('/auth/login', { password })
    const data = await api.get<{ user: string }>('/auth/me')
    setState({ user: data.user, loading: false })
  }, [])

  const logout = useCallback(async () => {
    await api.post('/auth/logout')
    setState({ user: null, loading: false })
  }, [])

  return { ...state, login, logout }
}
