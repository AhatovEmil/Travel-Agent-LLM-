import { useEffect, useState } from 'react'
import { api } from '../api.js'

const STATUS_LABELS = {
  draft: ['Черновик', 'badge'],
  running: ['Генерация…', 'badge running'],
  completed: ['Готов', 'badge done'],
  failed: ['Ошибка', 'badge failed'],
}

export default function Dashboard({ onOpen }) {
  const [projects, setProjects] = useState([])
  const [name, setName] = useState('')
  const [idea, setIdea] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const refresh = () => api.listProjects().then(setProjects).catch((e) => setError(e.message))

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
      const project = await api.createProject(name, idea)
      await api.runProject(project.id)
      setName('')
      setIdea('')
      await refresh()
      onOpen(project.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Удалить проект?')) return
    await api.deleteProject(id)
    refresh()
  }

  return (
    <div className="container">
      <section className="card">
        <h2>Новый проект</h2>
        <p className="muted">
          Опишите идею — агент проведёт анализ, составит план, выберет архитектуру и сгенерирует
          запускаемый код.
        </p>
        <form onSubmit={create} className="stack">
          <input
            placeholder="Название проекта, например: Маркетплейс одежды"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={255}
          />
          <textarea
            placeholder="Идея: Хочу сделать маркетплейс одежды с каталогом и заказами…"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={4}
            minLength={10}
            required
          />
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>
            {busy ? 'Запускаю агента…' : '🚀 Построить MVP'}
          </button>
        </form>
      </section>

      <section>
        <h2>Мои проекты</h2>
        {projects.length === 0 && <p className="muted">Пока пусто — создайте первый проект.</p>}
        <div className="grid">
          {projects.map((p) => {
            const [label, cls] = STATUS_LABELS[p.status] || [p.status, 'badge']
            return (
              <div key={p.id} className="card project-card" onClick={() => onOpen(p.id)}>
                <div className="row">
                  <h3>{p.name}</h3>
                  <span className={cls}>{label}</span>
                </div>
                <p className="muted clamp">{p.idea}</p>
                {p.status === 'running' && (
                  <p className="muted">Фаза: {p.current_phase || '…'}</p>
                )}
                <button
                  className="ghost danger"
                  onClick={(e) => {
                    e.stopPropagation()
                    remove(p.id)
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
