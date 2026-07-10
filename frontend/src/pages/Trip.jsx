import { useEffect, useState } from 'react'
import AskChat from '../AskChat.jsx'
import Markdown from '../Markdown.jsx'
import TripMap from '../TripMap.jsx'
import { api, downloadTripFile } from '../api.js'

const PHASES = [
  ['brief', 'ТЗ поездки'],
  ['itinerary', 'План по дням'],
  ['budget', 'Бюджет'],
  ['checklist', 'Чеклист'],
]

export default function Trip({ tripId, onBack }) {
  const [trip, setTrip] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [extras, setExtras] = useState(null)
  const [openArtifact, setOpenArtifact] = useState(null)
  const [openDay, setOpenDay] = useState(0)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [reviseMessage, setReviseMessage] = useState('')
  const [reviseBusy, setReviseBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  useEffect(() => {
    let timer
    let cancelled = false

    const load = async () => {
      try {
        const t = await api.getTrip(tripId)
        if (cancelled) return
        setTrip(t)
        const arts = await api.getArtifacts(tripId)
        if (cancelled) return
        setArtifacts(arts)
        if (t.status !== 'running') {
          try {
            const ex = await api.getExtras(tripId)
            if (!cancelled) setExtras(ex)
          } catch {
            if (!cancelled) setExtras(null)
          }
        }
        if (t.status === 'running') {
          timer = setTimeout(load, 2000)
        } else {
          setReviseBusy(false)
          setOpenArtifact((prev) => {
            if (prev != null) return prev
            return arts[0]?.id ?? null
          })
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }

    load()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [tripId, trip?.status])

  if (error)
    return (
      <div className="container">
        <div className="error">{error}</div>
      </div>
    )
  if (!trip) return <div className="container muted">Загрузка…</div>

  const donePhases = new Set(artifacts.map((a) => a.phase))
  const itinerary = artifacts.find((a) => a.phase === 'itinerary')
  const otherArtifacts = artifacts.filter((a) => a.phase !== 'itinerary')
  const days = extras?.days?.length ? extras.days : null
  const idle = trip.status !== 'running'

  const rerun = async () => {
    setActionError('')
    try {
      await api.runTrip(tripId)
      setArtifacts([])
      setExtras(null)
      setOpenArtifact(null)
      setTrip({ ...trip, status: 'running', current_phase: 'brief', error: '' })
    } catch (err) {
      setActionError(err.message)
    }
  }

  const rerunPhase = async (phase) => {
    setActionError('')
    try {
      await api.rerunPhase(tripId, phase)
      setTrip({ ...trip, status: 'running', current_phase: phase, error: '' })
    } catch (err) {
      setActionError(err.message)
    }
  }

  const sendRevise = async (e) => {
    e.preventDefault()
    if (!reviseMessage.trim() || reviseBusy) return
    setActionError('')
    setReviseBusy(true)
    try {
      await api.chatTrip(tripId, reviseMessage.trim())
      setReviseMessage('')
      setTrip({ ...trip, status: 'running', current_phase: 'itinerary', error: '' })
    } catch (err) {
      setReviseBusy(false)
      setActionError(err.message)
    }
  }

  const download = async (format) => {
    setDownloadError('')
    try {
      await downloadTripFile(tripId, trip.name, format)
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
          <div className="row gap wrap">
            {trip.status === 'completed' && (
              <>
                <button className="primary" onClick={() => download('pdf')}>
                  Скачать PDF
                </button>
                <button className="ghost" onClick={() => download('md')}>
                  .md
                </button>
              </>
            )}
            {(trip.status === 'completed' || trip.status === 'failed') && (
              <button className="ghost" onClick={rerun}>
                Перегенерировать всё
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
      {actionError && <div className="error">{actionError}</div>}

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

      {extras?.weather?.length > 0 && (
        <section className="weather-strip">
          <h2>Погода (ориентир)</h2>
          <p className="muted small">Прогноз Open-Meteo от сегодня на {extras.days_count} дн.</p>
          <div className="weather-row">
            {extras.weather.map((w) => (
              <div key={w.date} className="weather-card">
                <div className="weather-date">{w.date.slice(5)}</div>
                <div className="weather-label">{w.label}</div>
                <div className="weather-temp">
                  {w.temp_min}° … {w.temp_max}°
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {extras?.center && (
        <section>
          <div className="section-title">
            <h2>Карта</h2>
            <span className="muted small">{extras.destination}</span>
          </div>
          <TripMap center={extras.center} places={extras.places} />
        </section>
      )}

      <section>
        <div className="section-title">
          <h2>План по дням</h2>
          {itinerary && idle && (
            <button className="ghost compact" onClick={() => rerunPhase('itinerary')}>
              Перегенерировать план
            </button>
          )}
        </div>
        {!itinerary && <p className="muted">Агент ещё готовит itinerary…</p>}
        {itinerary && days && (
          <div className="day-cards">
            {days.map((day, idx) => (
              <div key={`${day.title}-${idx}`} className="day-card">
                <button
                  className="row expander"
                  onClick={() => setOpenDay(openDay === idx ? -1 : idx)}
                >
                  <strong>{day.title}</strong>
                  <span>{openDay === idx ? '▾' : '▸'}</span>
                </button>
                {openDay === idx && <Markdown>{day.content}</Markdown>}
              </div>
            ))}
          </div>
        )}
        {itinerary && !days && <Markdown>{itinerary.content}</Markdown>}
      </section>

      {itinerary && (
        <section className="chat-panel">
          <h2>Изменить план</h2>
          <p className="muted small">
            Перепишет itinerary. Для обычных вопросов — кнопка «?» справа внизу.
          </p>
          <form className="chat-form" onSubmit={sendRevise}>
            <input
              value={reviseMessage}
              onChange={(e) => setReviseMessage(e.target.value)}
              placeholder="Например: убери музеи, добавь пляжи"
              disabled={!idle || reviseBusy}
            />
            <button
              className="primary"
              type="submit"
              disabled={!idle || reviseBusy || !reviseMessage.trim()}
            >
              {reviseBusy || trip.status === 'running' ? 'Думаю…' : 'Переписать'}
            </button>
          </form>
        </section>
      )}

      <section>
        <h2>Остальные документы</h2>
        {otherArtifacts.length === 0 && <p className="muted">Пока пусто…</p>}
        {otherArtifacts.map((a) => (
          <div key={a.id} className="card slim">
            <button
              className="row expander"
              onClick={() => setOpenArtifact(openArtifact === a.id ? null : a.id)}
            >
              <strong>{a.title}</strong>
              <span className="row gap">
                {idle && (
                  <span
                    className="linkish"
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation()
                      rerunPhase(a.phase)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.stopPropagation()
                        rerunPhase(a.phase)
                      }
                    }}
                  >
                    ↻
                  </span>
                )}
                <span>{openArtifact === a.id ? '▾' : '▸'}</span>
              </span>
            </button>
            {openArtifact === a.id && <Markdown>{a.content}</Markdown>}
          </div>
        ))}
      </section>

      <AskChat tripId={tripId} disabled={false} />
    </div>
  )
}
