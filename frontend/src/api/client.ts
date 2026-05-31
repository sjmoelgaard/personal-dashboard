const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: callerHeaders, ...restOptions } = options ?? {}
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(callerHeaders as Record<string, string>) },
    ...restOptions,
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
}
