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
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <h1>⚡ AI Technical Founder</h1>
        <p className="muted">Идея → готовый MVP. Под ключ.</p>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Пароль (минимум 6 символов)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={6}
          required
        />
        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy}>
          {busy ? '...' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
        >
          {mode === 'login' ? 'Нет аккаунта? Регистрация' : 'Уже есть аккаунт? Вход'}
        </button>
      </form>
    </div>
  )
}
