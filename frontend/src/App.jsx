import { useEffect, useState } from 'react'
import { clearToken, getToken } from './api.js'
import Auth from './pages/Auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Trip from './pages/Trip.jsx'

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()))
  const [tripId, setTripId] = useState(null)

  useEffect(() => {
    const onLogout = () => {
      setAuthed(false)
      setTripId(null)
    }
    window.addEventListener('travel-logout', onLogout)
    return () => window.removeEventListener('travel-logout', onLogout)
  }, [])

  const logout = () => {
    clearToken()
    setAuthed(false)
    setTripId(null)
  }

  if (!authed) return <Auth onSuccess={() => setAuthed(true)} />

  return (
    <div className="layout">
      <header className="topbar">
        <button className="brand" onClick={() => setTripId(null)}>
          Travel Agent
        </button>
        <button className="ghost" onClick={logout}>
          Выйти
        </button>
      </header>
      <main>
        {tripId === null ? (
          <Dashboard onOpen={setTripId} />
        ) : (
          <Trip tripId={tripId} onBack={() => setTripId(null)} />
        )}
      </main>
    </div>
  )
}
