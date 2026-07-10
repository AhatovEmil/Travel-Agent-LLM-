import { useEffect, useState } from 'react'
import { api } from '../api.js'

const STATUS_LABELS = {
  draft: ['Черновик', 'badge'],
  running: ['Планирую…', 'badge running'],
  completed: ['Готов', 'badge done'],
  failed: ['Ошибка', 'badge failed'],
}

export default function Dashboard({ onOpen }) {
  const [trips, setTrips] = useState([])
  const [name, setName] = useState('')
  const [brief, setBrief] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const refresh = () => api.listTrips().then(setTrips).catch((e) => setError(e.message))

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 3000)
    return () => clearInterval(timer)
  }, [])

  const create = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const trip = await api.createTrip(name, brief)
      await api.runTrip(trip.id)
      setName('')
      setBrief('')
      await refresh()
      onOpen(trip.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Удалить поездку?')) return
    await api.deleteTrip(id)
    refresh()
  }

  return (
    <div className="container">
      <section className="card">
        <h2>Новая поездка</h2>
        <p className="muted">
          Опишите куда, на сколько дней, бюджет и интересы — агент соберёт план, бюджет и
          чеклист. Нужен ключ DeepSeek в backend/.env. Цены и адреса — ориентир, проверяйте.
        </p>
        <form onSubmit={create} className="stack">
          <input
            placeholder="Название, например: Батуми на майские"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={255}
          />
          <textarea
            placeholder="Батуми, 5 дней, бюджет 50 тыс ₽, море, еда, без экстрима…"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={4}
            minLength={10}
            required
          />
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>
            {busy ? 'Запускаю агента…' : 'Спланировать поездку'}
          </button>
        </form>
      </section>

      <section>
        <h2>Мои поездки</h2>
        {trips.length === 0 && <p className="muted">Пока пусто — создайте первую поездку.</p>}
        <div className="grid">
          {trips.map((t) => {
            const [label, cls] = STATUS_LABELS[t.status] || [t.status, 'badge']
            return (
              <div key={t.id} className="card project-card" onClick={() => onOpen(t.id)}>
                <div className="row">
                  <h3>{t.name}</h3>
                  <span className={cls}>{label}</span>
                </div>
                <p className="muted clamp">{t.brief}</p>
                {t.status === 'running' && (
                  <p className="muted">Фаза: {t.current_phase || '…'}</p>
                )}
                <button
                  className="ghost danger"
                  onClick={(e) => {
                    e.stopPropagation()
                    remove(t.id)
                  }}
                >
                  Удалить
                </button>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
