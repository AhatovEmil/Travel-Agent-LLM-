import { useEffect, useState } from 'react'
import { clearToken, getToken } from './api.js'
import Auth from './pages/Auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Project from './pages/Project.jsx'

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()))
  const [projectId, setProjectId] = useState(null)

  useEffect(() => {
    const onLogout = () => {
      setAuthed(false)
      setProjectId(null)
    }
    window.addEventListener('aitf-logout', onLogout)
    return () => window.removeEventListener('aitf-logout', onLogout)
  }, [])

  const logout = () => {
    clearToken()
    setAuthed(false)
    setProjectId(null)
  }

  if (!authed) return <Auth onSuccess={() => setAuthed(true)} />

  return (
    <div className="layout">
      <header className="topbar">
        <button className="brand" onClick={() => setProjectId(null)}>
          ⚡ AI Technical Founder
        </button>
        <button className="ghost" onClick={logout}>
          Выйти
        </button>
      </header>
      <main>
        {projectId === null ? (
          <Dashboard onOpen={setProjectId} />
        ) : (
          <Project projectId={projectId} onBack={() => setProjectId(null)} />
        )}
      </main>
    </div>
  )
}
