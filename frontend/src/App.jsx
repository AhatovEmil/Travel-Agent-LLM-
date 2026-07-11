import { useCallback, useEffect, useState } from 'react'
import { api, clearToken, getToken } from './api.js'
import QuotaModal, { QuotaBadge } from './QuotaModal.jsx'
import ToastHost from './Toast.jsx'
import Auth from './pages/Auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Faq from './pages/Faq.jsx'
import ShareTrip from './pages/ShareTrip.jsx'
import Trip from './pages/Trip.jsx'

function parseHash() {
  const raw = (window.location.hash || '#/').replace(/^#/, '') || '/'
  const path = raw.startsWith('/') ? raw : `/${raw}`
  const share = path.match(/^\/share\/([^/]+)/)
  if (share) return { view: 'share', token: decodeURIComponent(share[1]), tripId: null }
  const trip = path.match(/^\/trip\/(\d+)/)
  if (trip) return { view: 'trip', tripId: Number(trip[1]), token: null }
  if (path === '/faq' || path.startsWith('/faq/')) return { view: 'faq', tripId: null, token: null }
  return { view: 'home', tripId: null, token: null }
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()))
  const [route, setRoute] = useState(parseHash)
  const [quota, setQuota] = useState(null)
  const [quotaOpen, setQuotaOpen] = useState(false)
  const [quotaDetail, setQuotaDetail] = useState(null)

  const refreshQuota = useCallback(() => {
    if (!getToken()) {
      setQuota(null)
      return
    }
    api
      .me()
      .then((u) =>
        setQuota({
          free_left: u.free_left,
          free_limit: u.free_limit,
          free_used: u.free_used,
          credit_balance: u.credit_balance,
          period: u.period,
          telegram_linked: u.telegram_linked,
        }),
      )
      .catch(() => {})
  }, [])

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    const onLogout = () => {
      setAuthed(false)
      setQuota(null)
      window.location.hash = '#/'
    }
    window.addEventListener('travel-logout', onLogout)
    return () => window.removeEventListener('travel-logout', onLogout)
  }, [])

  useEffect(() => {
    const onQuota = (e) => {
      setQuotaDetail(e.detail || null)
      setQuotaOpen(true)
      refreshQuota()
    }
    window.addEventListener('travel-quota', onQuota)
    return () => window.removeEventListener('travel-quota', onQuota)
  }, [refreshQuota])

  useEffect(() => {
    if (authed) refreshQuota()
  }, [authed, refreshQuota])

  const openTrip = (id) => {
    window.location.hash = `#/trip/${id}`
  }

  const goHome = () => {
    window.location.hash = '#/'
  }

  const goFaq = () => {
    window.location.hash = '#/faq'
  }

  const logout = () => {
    clearToken()
    setAuthed(false)
    setQuota(null)
    goHome()
  }

  const openQuota = () => {
    setQuotaDetail(
      quota
        ? {
            free_left: quota.free_left,
            free_limit: quota.free_limit,
            credits: quota.credit_balance,
            telegram_linked: quota.telegram_linked,
          }
        : null,
    )
    setQuotaOpen(true)
  }

  if (route.view === 'share') {
    return (
      <div className="layout">
        <header className="topbar">
          <button className="brand" onClick={goHome}>
            Travel <span>Agent</span>
          </button>
          <button className="ghost compact" onClick={goFaq}>
            FAQ
          </button>
        </header>
        <main>
          <ShareTrip token={route.token} />
        </main>
        <ToastHost />
      </div>
    )
  }

  if (route.view === 'faq') {
    return (
      <div className="layout">
        <header className="topbar">
          <button className="brand" onClick={goHome}>
            Travel <span>Agent</span>
          </button>
          {authed ? (
            <button className="ghost" onClick={logout}>
              Выйти
            </button>
          ) : null}
        </header>
        <main>
          <Faq onBack={authed ? goHome : undefined} />
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
        <div className="topbar-actions">
          <QuotaBadge quota={quota} onClick={openQuota} />
          <button className="ghost compact" onClick={goFaq}>
            FAQ
          </button>
          <button className="ghost" onClick={logout}>
            Выйти
          </button>
        </div>
      </header>
      <main>
        {route.view === 'trip' && route.tripId ? (
          <Trip tripId={route.tripId} onBack={goHome} onQuotaChange={refreshQuota} />
        ) : (
          <Dashboard onOpen={openTrip} onQuotaChange={refreshQuota} />
        )}
      </main>
      <QuotaModal
        open={quotaOpen}
        initialDetail={quotaDetail}
        quota={quota}
        onLinked={(res) => {
          refreshQuota()
          setQuota((q) =>
            q
              ? {
                  ...q,
                  telegram_linked: true,
                  credit_balance: res.credit_balance ?? q.credit_balance,
                }
              : q,
          )
        }}
        onClose={() => {
          setQuotaOpen(false)
          refreshQuota()
        }}
      />
      <ToastHost />
    </div>
  )
}
