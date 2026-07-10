import { useEffect, useState } from 'react'
import AskChat from '../AskChat.jsx'
import LinkButtons, { FeasibilityBadge } from '../LinkButtons.jsx'
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
  const [votes, setVotes] = useState([])
  const [openArtifact, setOpenArtifact] = useState(null)
  const [openDay, setOpenDay] = useState(0)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [reviseMessage, setReviseMessage] = useState('')
  const [reviseBusy, setReviseBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [live, setLive] = useState(null)
  const [liveBusy, setLiveBusy] = useState(false)
  const [shareMsg, setShareMsg] = useState('')

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
            const [ex, v] = await Promise.all([api.getExtras(tripId), api.getVotes(tripId)])
            if (!cancelled) {
              setExtras(ex)
              setVotes(v)
            }
          } catch {
            if (!cancelled) setExtras(null)
          }
        }
        if (t.status === 'running') {
          timer = setTimeout(load, 2000)
        } else {
          setReviseBusy(false)
          setLiveBusy(false)
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

  const voteCounts = (slotKey) => {
    const list = votes.filter((v) => v.slot_key === slotKey)
    return {
      want: list.filter((v) => v.value === 'want').length,
      skip: list.filter((v) => v.value === 'skip').length,
    }
  }

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

  const enableLive = () => {
    setLiveBusy(true)
    setActionError('')
    const done = (lat, lon) => {
      api
        .getLive(tripId, lat, lon)
        .then(setLive)
        .catch((err) => setActionError(err.message))
        .finally(() => setLiveBusy(false))
    }
    if (!navigator.geolocation) {
      done(null, null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => done(pos.coords.latitude, pos.coords.longitude),
      () => done(null, null),
      { timeout: 8000 },
    )
  }

  const adjustLive = async (reason) => {
    setActionError('')
    setLiveBusy(true)
    try {
      await api.liveAdjust(tripId, reason)
      setTrip({ ...trip, status: 'running', current_phase: 'itinerary', error: '' })
    } catch (err) {
      setLiveBusy(false)
      setActionError(err.message)
    }
  }

  const copyShare = async () => {
    setShareMsg('')
    try {
      const res = await api.enableShare(tripId)
      const url = `${window.location.origin}${window.location.pathname}${res.share_path}`
      await navigator.clipboard.writeText(url)
      setShareMsg('Ссылка скопирована')
      setTrip({ ...trip, share_token: res.share_token })
    } catch (err) {
      setActionError(err.message)
    }
  }

  const rebuildVotes = async () => {
    setActionError('')
    try {
      await api.rebuildFromVotes(tripId)
      setTrip({ ...trip, status: 'running', current_phase: 'itinerary', error: '' })
    } catch (err) {
      setActionError(err.message)
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
                <button className="ghost" onClick={copyShare}>
                  Ссылка для друзей
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
        {trip.start_date && <p className="muted small">Старт: {trip.start_date}</p>}
        {shareMsg && <p className="muted small">{shareMsg}</p>}
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

      {extras?.links && (
        <div className="row gap wrap" style={{ marginBottom: 16 }}>
          <LinkButtons links={extras.links} />
        </div>
      )}

      {itinerary && idle && (
        <section className="live-panel">
          <div className="section-title">
            <h2>Я на месте</h2>
            <button className="ghost compact" onClick={enableLive} disabled={liveBusy}>
              {liveBusy ? '…' : live ? 'Обновить' : 'Включить геолокацию'}
            </button>
          </div>
          {live && (
            <>
              <p className="muted small">
                Сейчас {live.now}
                {live.day?.title ? ` · ${live.day.title}` : ''}
                {live.distance_km_to_next != null
                  ? ` · до следующей точки ~${live.distance_km_to_next} км`
                  : ''}
              </p>
              {live.current_slot && (
                <p>
                  <strong>Сейчас:</strong> {live.current_slot.start}–{live.current_slot.end}{' '}
                  {live.current_slot.place}
                </p>
              )}
              {live.next_slot && (
                <p>
                  <strong>Далее:</strong> {live.next_slot.start}–{live.next_slot.end}{' '}
                  {live.next_slot.place}
                </p>
              )}
              {live.weather && (
                <p className="muted small">
                  Погода: {live.weather.label}, {live.weather.temp_min}°…{live.weather.temp_max}°
                </p>
              )}
              <div className="row gap wrap">
                <button className="ghost" onClick={() => adjustLive('late')} disabled={liveBusy}>
                  Опаздываю — сдвинь день
                </button>
                <button className="ghost" onClick={() => adjustLive('rain')} disabled={liveBusy}>
                  Дождь — перестрой день
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {extras?.weather?.length > 0 && (
        <section className="weather-strip">
          <h2>Погода (ориентир)</h2>
          <p className="muted small">
            Прогноз Open-Meteo
            {extras.start_date ? ` с ${extras.start_date}` : ' от сегодня'} на {extras.days_count}{' '}
            дн.
          </p>
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
                  <strong>
                    {day.title}
                    {day.date ? ` · ${day.date}` : ''}
                  </strong>
                  <span>{openDay === idx ? '▾' : '▸'}</span>
                </button>
                {openDay === idx && (
                  <div className="day-body">
                    {day.weather && (
                      <p className="muted small">
                        {day.weather.label}, {day.weather.temp_min}°…{day.weather.temp_max}°
                      </p>
                    )}
                    {day.slots?.length > 0 ? (
                      <div className="slot-list">
                        {day.slots.map((slot) => {
                          const counts = voteCounts(slot.slot_key)
                          return (
                            <div key={slot.slot_key} className="slot-card">
                              <div className="row">
                                <strong>
                                  {slot.start}–{slot.end}
                                </strong>
                                <span>{slot.place}</span>
                              </div>
                              {slot.body && <Markdown>{slot.body}</Markdown>}
                              <LinkButtons links={slot.links} compact />
                              {slot.transfer && (
                                <p className="muted small transfer-line">
                                  → {slot.transfer.to}
                                  {slot.transfer.distance_km != null
                                    ? ` · ${slot.transfer.distance_km} км пешком ~${slot.transfer.walk_min} мин`
                                    : ''}
                                  {slot.transfer.gap_min != null
                                    ? ` · окно ${slot.transfer.gap_min} мин`
                                    : ''}{' '}
                                  <FeasibilityBadge value={slot.transfer.feasibility} />
                                </p>
                              )}
                              {(counts.want > 0 || counts.skip > 0) && (
                                <p className="muted small">
                                  Голоса: 👍 {counts.want} · 👎 {counts.skip}
                                </p>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <Markdown>{day.content}</Markdown>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {itinerary && !days && <Markdown>{itinerary.content}</Markdown>}
      </section>

      {votes.length > 0 && idle && (
        <section className="chat-panel">
          <div className="section-title">
            <h2>Голоса друзей</h2>
            <button className="primary compact" onClick={rebuildVotes}>
              Пересобрать по голосам
            </button>
          </div>
          <p className="muted small">Всего отметок: {votes.length}</p>
        </section>
      )}

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
