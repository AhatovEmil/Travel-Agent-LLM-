import { useEffect, useState } from 'react'
import { clearToken, getToken } from './api.js'
import ToastHost from './Toast.jsx'
import Auth from './pages/Auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import ShareTrip from './pages/ShareTrip.jsx'
import Trip from './pages/Trip.jsx'

function parseHash() {
  const raw = (window.location.hash || '#/').replace(/^#/, '') || '/'
  const path = raw.startsWith('/') ? raw : `/${raw}`
  const share = path.match(/^\/share\/([^/]+)/)
  if (share) return { view: 'share', token: decodeURIComponent(share[1]), tripId: null }
  const trip = path.match(/^\/trip\/(\d+)/)
  if (trip) return { view: 'trip', tripId: Number(trip[1]), token: null }
  return { view: 'home', tripId: null, token: null }
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()))
  const [route, setRoute] = useState(parseHash)

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    const onLogout = () => {
      setAuthed(false)
      window.location.hash = '#/'
    }
    window.addEventListener('travel-logout', onLogout)
    return () => window.removeEventListener('travel-logout', onLogout)
  }, [])

  const openTrip = (id) => {
    window.location.hash = `#/trip/${id}`
  }

  const goHome = () => {
    window.location.hash = '#/'
  }

  const logout = () => {
    clearToken()
    setAuthed(false)
    goHome()
  }

  if (route.view === 'share') {
    return (
      <div className="layout">
        <header className="topbar">
          <button className="brand" onClick={goHome}>
            Travel <span>Agent</span>
          </button>
        </header>
        <main>
          <ShareTrip token={route.token} />
        </main>
        <ToastHost />
      </div>
    )
  }

  if (!authed) return <Auth onSuccess={() => setAuthed(true)} />

  return (
    <div className="layout">
      <header className="topbar">
        <button className="brand" onClick={goHome}>
          Travel <span>Agent</span>
        </button>
        <button className="ghost" onClick={logout}>
          Выйти
        </button>
      </header>
      <main>
        {route.view === 'trip' && route.tripId ? (
          <Trip tripId={route.tripId} onBack={goHome} />
        ) : (
          <Dashboard onOpen={openTrip} />
        )}
      </main>
      <ToastHost />
    </div>
  )
}
