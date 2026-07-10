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
  getItineraryVersions: (id) => request(`/api/trips/${id}/itinerary/versions`),
  rollbackItinerary: (id, versionId) =>
    request(`/api/trips/${id}/itinerary/versions/${versionId}/rollback`, { method: 'POST' }),
  getExtras: (id, fast = false) =>
    request(`/api/trips/${id}/extras${fast ? '?fast=1' : ''}`),
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
  streetSurvival: (id) => request(`/api/trips/${id}/street-smart/survival`),
  streetSurvivalEnrich: (id) =>
    request(`/api/trips/${id}/street-smart/survival/enrich`, { method: 'POST' }),
  streetTraps: (id) => request(`/api/trips/${id}/street-smart/traps`),
  streetTrapsEnrich: (id) =>
    request(`/api/trips/${id}/street-smart/traps/enrich`, { method: 'POST' }),
  streetTaste: (id) => request(`/api/trips/${id}/street-smart/taste`),
  streetArrival: (id) => request(`/api/trips/${id}/street-smart/arrival`),
  streetQuest: (id, dayIndex) =>
    request(`/api/trips/${id}/street-smart/quest`, {
      method: 'POST',
      body: JSON.stringify({ day_index: dayIndex }),
    }),
  tripWindow: (id) => request(`/api/trips/${id}/os/window`),
  tripBriefing: (id, dayIndex) => {
    const q = dayIndex != null ? `?day_index=${dayIndex}` : ''
    return request(`/api/trips/${id}/os/briefing${q}`)
  },
  listJournal: (id) => request(`/api/trips/${id}/journal`),
  createJournal: (id, payload) =>
    request(`/api/trips/${id}/journal`, { method: 'POST', body: JSON.stringify(payload) }),
  updateJournal: (id, entryId, payload) =>
    request(`/api/trips/${id}/journal/${entryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteJournal: (id, entryId) =>
    request(`/api/trips/${id}/journal/${entryId}`, { method: 'DELETE' }),
  eveningCheckin: (id, payload) =>
    request(`/api/trips/${id}/os/evening`, { method: 'POST', body: JSON.stringify(payload) }),
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
