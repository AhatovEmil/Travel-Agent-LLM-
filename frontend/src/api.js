const TOKEN_KEY = 'travel_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(path, { ...options, headers })
  if (response.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('travel-logout'))
  }
  if (!response.ok) {
    let detail = `Ошибка ${response.status}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  register: (email, password) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email, password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/api/auth/me'),
  listTrips: () => request('/api/trips'),
  createTrip: (name, brief) =>
    request('/api/trips', { method: 'POST', body: JSON.stringify({ name, brief }) }),
  getTrip: (id) => request(`/api/trips/${id}`),
  deleteTrip: (id) => request(`/api/trips/${id}`, { method: 'DELETE' }),
  runTrip: (id) => request(`/api/trips/${id}/run`, { method: 'POST' }),
  getArtifacts: (id) => request(`/api/trips/${id}/artifacts`),
}

export async function downloadTripMarkdown(id, name) {
  const response = await fetch(`/api/trips/${id}/export`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!response.ok) {
    let detail = 'Скачивание недоступно'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const safe = (name || 'trip').replace(/[^\w\-а-яА-ЯёЁ ]+/gi, '').trim() || 'trip'
  link.download = `${safe}.md`
  link.click()
  URL.revokeObjectURL(url)
}
