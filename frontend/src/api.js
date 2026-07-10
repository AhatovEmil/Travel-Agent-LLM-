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
  createTrip: (name, brief, startDate) =>
    request('/api/trips', {
      method: 'POST',
      body: JSON.stringify({ name, brief, start_date: startDate || null }),
    }),
  getTrip: (id) => request(`/api/trips/${id}`),
  deleteTrip: (id) => request(`/api/trips/${id}`, { method: 'DELETE' }),
  runTrip: (id) => request(`/api/trips/${id}/run`, { method: 'POST' }),
  rerunPhase: (id, phase) =>
    request(`/api/trips/${id}/phases/rerun`, {
      method: 'POST',
      body: JSON.stringify({ phase }),
    }),
  chatTrip: (id, message) =>
    request(`/api/trips/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  askTrip: (id, message) =>
    request(`/api/trips/${id}/ask`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  getMessages: (id) => request(`/api/trips/${id}/messages`),
  getArtifacts: (id) => request(`/api/trips/${id}/artifacts`),
  getExtras: (id) => request(`/api/trips/${id}/extras`),
  getLive: (id, lat, lon) => {
    const q = new URLSearchParams()
    if (lat != null) q.set('lat', String(lat))
    if (lon != null) q.set('lon', String(lon))
    const qs = q.toString()
    return request(`/api/trips/${id}/live${qs ? `?${qs}` : ''}`)
  },
  liveAdjust: (id, reason, message = '') =>
    request(`/api/trips/${id}/live/adjust`, {
      method: 'POST',
      body: JSON.stringify({ reason, message }),
    }),
  enableShare: (id) => request(`/api/trips/${id}/share`, { method: 'POST' }),
  getVotes: (id) => request(`/api/trips/${id}/votes`),
  rebuildFromVotes: (id) => request(`/api/trips/${id}/rebuild-from-votes`, { method: 'POST' }),
  recoverTrip: (id) => request(`/api/trips/${id}/recover`, { method: 'POST' }),
  getShared: (token) => request(`/api/share/${token}`),
  castVote: (token, payload) =>
    request(`/api/share/${token}/votes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}

export async function downloadTripFile(id, name, format = 'md') {
  const path = format === 'pdf' ? `/api/trips/${id}/export.pdf` : `/api/trips/${id}/export`
  const response = await fetch(path, {
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
  link.download = `${safe}.${format === 'pdf' ? 'pdf' : 'md'}`
  link.click()
  URL.revokeObjectURL(url)
}

export async function downloadTripMarkdown(id, name) {
  return downloadTripFile(id, name, 'md')
}
