import { useEffect, useState } from 'react'
import Markdown from '../Markdown.jsx'
import { api, downloadTripMarkdown } from '../api.js'

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
  const [downloadError, setDownloadError] = useState('')

  useEffect(() => {
    let timer
    const load = async () => {
      try {
        const t = await api.getTrip(tripId)
        setTrip(t)
        const arts = await api.getArtifacts(tripId)
        setArtifacts(arts)
        if (t.status === 'running') timer = setTimeout(load, 2000)
        else if (arts.length && openArtifact === null) setOpenArtifact(arts[0].id)
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
      setOpenArtifact(null)
      setTrip({ ...trip, status: 'running', current_phase: 'brief', error: '' })
    } catch (err) {
      setError(err.message)
    }
  }

  const download = async () => {
    setDownloadError('')
    try {
      await downloadTripMarkdown(tripId, trip.name)
    } catch (err) {
      setDownloadError(err.message)
    }
  }

  return (
    <div className="container">
      <button className="ghost" onClick={onBack}>
        ← Все поездки
      </button>
      <div className="page-hero" style={{ marginTop: 16 }}>
        <div className="row">
          <h1>{trip.name}</h1>
          <div className="row gap">
            {trip.status === 'completed' && (
              <button className="primary" onClick={download}>
                Скачать .md
              </button>
            )}
            {(trip.status === 'completed' || trip.status === 'failed') && (
              <button className="ghost" onClick={rerun}>
                Перегенерировать
              </button>
            )}
          </div>
        </div>
        <p>{trip.brief}</p>
      </div>
      <p className="muted notice">
        Черновик от ИИ: адреса, часы работы и цены ориентировочные — проверяйте перед поездкой.
      </p>
      {trip.error && <div className="error">{trip.error}</div>}
      {downloadError && <div className="error">{downloadError}</div>}

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
        <h2>План поездки</h2>
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
            {openArtifact === a.id && <Markdown>{a.content}</Markdown>}
          </div>
        ))}
      </section>
    </div>
  )
}
