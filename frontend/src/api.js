const TOKEN_KEY = 'aitf_token'

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
    window.dispatchEvent(new Event('aitf-logout'))
  }
  if (!response.ok) {
    let detail = `Ошибка ${response.status}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* тело не JSON */
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
  listProjects: () => request('/api/projects'),
  createProject: (name, idea) =>
    request('/api/projects', { method: 'POST', body: JSON.stringify({ name, idea }) }),
  getProject: (id) => request(`/api/projects/${id}`),
  deleteProject: (id) => request(`/api/projects/${id}`, { method: 'DELETE' }),
  runProject: (id) => request(`/api/projects/${id}/run`, { method: 'POST' }),
  getArtifacts: (id) => request(`/api/projects/${id}/artifacts`),
  getFiles: (id) => request(`/api/projects/${id}/files`),
}

export async function downloadZip(id, name) {
  const response = await fetch(`/api/projects/${id}/download`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!response.ok) throw new Error('Скачивание недоступно: проект ещё не завершён')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${name || 'project'}.zip`
  link.click()
  URL.revokeObjectURL(url)
}
