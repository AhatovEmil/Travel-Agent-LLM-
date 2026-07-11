import { useState } from 'react'
import { api, setToken } from '../api.js'

export default function Auth({ onSuccess }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const fn = mode === 'login' ? api.login : api.register
      const { access_token } = await fn(email, password)
      setToken(access_token)
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-scene">
      <div className="auth-photo" aria-hidden="true">
        <img src="/images/auth-coast.jpg" alt="" />
        <div className="auth-photo-veil" />
      </div>

      <div className="auth-stage">
        <header className="auth-hero">
          <p className="auth-eyebrow">Планировщик поездок</p>
          <h1 className="auth-brand">
            Travel <span>Agent</span>
          </h1>
        </header>

        <form className="auth-panel" onSubmit={submit}>
          <p className="auth-tagline">Маршрут, бюджет и чеклист — за несколько вопросов</p>
          <div className="tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'login'}
              className={mode === 'login' ? 'tab active' : 'tab'}
              onClick={() => setMode('login')}
            >
              Вход
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'register'}
              className={mode === 'register' ? 'tab active' : 'tab'}
              onClick={() => setMode('register')}
            >
              Регистрация
            </button>
          </div>
          <div className="stack">
            <div>
              <label className="field-label" htmlFor="auth-email">
                Email
              </label>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                inputMode="email"
                placeholder="you@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="auth-password">
                Пароль
              </label>
              <input
                id="auth-password"
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="минимум 8 символов"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && <div className="error">{error}</div>}
            <button className="primary auth-cta" disabled={busy}>
              {busy ? '…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
            </button>
            <p className="auth-faq-link">
              <a href="#/faq">Частые вопросы</a>
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}
