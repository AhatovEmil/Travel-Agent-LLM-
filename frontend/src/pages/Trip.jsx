import { useEffect, useState } from 'react'
import { api } from '../api.js'

const PHASES = [
  ['brief', 'ТЗ поездки'],
  ['itinerary', 'План по дням'],
  ['budget', 'Бюджет'],
  ['checklist', 'Чеклист'],
]

export default function Trip({ tripId, onBack }) {
  const [trip, setTrip] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [openArtifact, setOpenArtifact] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let timer
    const load = async () => {
      try {
        const t = await api.getTrip(tripId)
        setTrip(t)
        setArtifacts(await api.getArtifacts(tripId))
        if (t.status === 'running') timer = setTimeout(load, 2000)
      } catch (err) {
        setError(err.message)
      }
    }
    load()
    return () => clearTimeout(timer)
  }, [tripId])

  if (error)
    return (
      <div className="container">
        <div className="error">{error}</div>
      </div>
    )
  if (!trip) return <div className="container muted">Загрузка…</div>

  const donePhases = new Set(artifacts.map((a) => a.phase))

  const rerun = async () => {
    try {
      await api.runTrip(tripId)
      setArtifacts([])
      setTrip({ ...trip, status: 'running', current_phase: 'brief', error: '' })
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="container">
      <button className="ghost" onClick={onBack}>
        ← Все поездки
      </button>
      <div className="row">
        <h1>{trip.name}</h1>
        <div className="row gap">
          {(trip.status === 'completed' || trip.status === 'failed') && (
            <button className="ghost" onClick={rerun}>
              Перегенерировать
            </button>
          )}
        </div>
      </div>
      <p className="muted">{trip.brief}</p>
      <p className="muted notice">
        Черновик от ИИ: адреса, часы работы и цены ориентировочные — проверяйте перед поездкой.
      </p>
      {trip.error && <div className="error">{trip.error}</div>}

      <div className="phases">
        {PHASES.map(([key, label]) => {
          const isDone = donePhases.has(key)
          const isActive = trip.status === 'running' && trip.current_phase === key
          return (
            <div key={key} className={`phase ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}>
              {isDone ? '✓' : isActive ? '⟳' : '○'} {label}
            </div>
          )
        })}
      </div>

      <section>
        <h2>Артефакты</h2>
        {artifacts.length === 0 && <p className="muted">Агент ещё работает…</p>}
        {artifacts.map((a) => (
          <div key={a.id} className="card slim">
            <button
              className="row expander"
              onClick={() => setOpenArtifact(openArtifact === a.id ? null : a.id)}
            >
              <strong>{a.title}</strong>
              <span>{openArtifact === a.id ? '▾' : '▸'}</span>
            </button>
            {openArtifact === a.id && <pre className="doc">{a.content}</pre>}
          </div>
        ))}
      </section>
    </div>
  )
}
