import { useEffect, useRef, useState } from 'react'
import AskChat from '../AskChat.jsx'
import { coverForText } from '../covers.js'
import DestinationGallery from '../DestinationGallery.jsx'
import LinkButtons, { FeasibilityBadge, hasBookingOffers } from '../LinkButtons.jsx'
import Markdown, { plainText } from '../Markdown.jsx'
import { announceTripReady, ensureNotifyPermission } from '../notify.js'
import StreetSmart, { DayQuest } from '../StreetSmart.jsx'
import { toast } from '../Toast.jsx'
import TripMap from '../TripMap.jsx'
import { EveningCheckin, MemoriesJournal, MorningBriefing, TripModeBar } from '../TripOS.jsx'
import { api, downloadTripFile } from '../api.js'

const PHASES = [
  ['brief', 'ТЗ поездки', 'Собираю цели, ритм и ограничения'],
  ['itinerary', 'План по дням', 'Раскладываю маршрут по слотам'],
  ['budget', 'Бюджет', 'Считаю ориентиры по тратам'],
  ['checklist', 'Чеклист', 'Список вещей и дел перед выездом'],
]

const GEN_TIPS = [
  'Пока ждёте — можно уже прикинуть, какие дни хотите более спокойными.',
  'Цены и адреса в плане ориентировочные: перед бронью сверьте на месте.',
  'После генерации можно переписать план одной фразой: «больше еды, меньше музеев».',
  'Ссылку для друзей удобно кинуть, когда план уже готов — они проголосуют за слоты.',
]

const PHASE_TITLES = {
  brief: 'ТЗ поездки',
  itinerary: 'План по дням',
  budget: 'Бюджет',
  checklist: 'Чеклист',
}

const VERSION_SOURCE = {
  pipeline: 'Полная генерация',
  phase_rerun: 'Перегенерация фазы',
  chat_revise: 'Правка чатом',
  live_adjust: 'Я на месте',
  rebuild_votes: 'По голосам',
  rollback: 'Откат',
}

function formatVersionTime(iso) {
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function Trip({ tripId, onBack }) {
  const [trip, setTrip] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [extras, setExtras] = useState(null)
  const [votes, setVotes] = useState([])
  const [versions, setVersions] = useState([])
  const [openVersion, setOpenVersion] = useState(null)
  const [openArtifact, setOpenArtifact] = useState(null)
  const [openDay, setOpenDay] = useState(0)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [reviseMessage, setReviseMessage] = useState('')
  const [reviseBusy, setReviseBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [live, setLive] = useState(null)
  const [liveBusy, setLiveBusy] = useState(false)
  const [liveCoords, setLiveCoords] = useState({ lat: null, lon: null })
  const [shareMsg, setShareMsg] = useState('')
  const [shareUrl, setShareUrl] = useState('')
  const [mapDay, setMapDay] = useState(0)
  const [tripMode, setTripMode] = useState('plan')
  const [modeHint, setModeHint] = useState(null)
  const [journal, setJournal] = useState([])
  const [photos, setPhotos] = useState([])
  const [photosLoading, setPhotosLoading] = useState(false)
  const modeBootstrapped = useRef(false)
  const wasFastExtras = useRef(false)
  const prevStatus = useRef(null)

  useEffect(() => {
    ensureNotifyPermission()
  }, [])

  useEffect(() => {
    if (extras?.fast) {
      wasFastExtras.current = true
      return
    }
    if (wasFastExtras.current && extras && !extras.fast) {
      wasFastExtras.current = false
      if (extras.center || extras.weather?.length) {
        toast('Карта и погода готовы', 'ok')
      }
    }
  }, [extras])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const w = await api.tripWindow(tripId)
        if (cancelled) return
        setModeHint(w.phase)
        if (!modeBootstrapped.current) {
          modeBootstrapped.current = true
          setTripMode(w.phase === 'onsite' ? 'onsite' : w.phase === 'memories' ? 'memories' : 'plan')
        }
        if (w.day_index != null) {
          setOpenDay(w.day_index)
          setMapDay(w.day_index)
        }
      } catch {
        /* window optional until itinerary exists */
      }
      try {
        const j = await api.listJournal(tripId)
        if (!cancelled) setJournal(j)
      } catch {
        if (!cancelled) setJournal([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tripId, trip?.status])

  useEffect(() => {
    let timer
    let cancelled = false

    const load = async () => {
      try {
        const t = await api.getTrip(tripId)
        if (cancelled) return

        const wasRunning = prevStatus.current === 'running'
        if (wasRunning && t.status === 'completed') {
          announceTripReady(t.name, { toast })
        } else if (wasRunning && t.status === 'failed') {
          toast(t.error || 'Генерация не удалась', 'err')
        }
        prevStatus.current = t.status
        setTrip(t)

        const arts = await api.getArtifacts(tripId)
        if (cancelled) return
        setArtifacts(arts)

        const hasItinerary = arts.some((a) => a.phase === 'itinerary')
        if (t.status !== 'running' || hasItinerary) {
          try {
            // Сначала быстрая структура дней (без геокодинга), потом полные extras
            const fastEx = await api.getExtras(tripId, true)
            if (!cancelled) setExtras(fastEx)

            const [ex, v, vers] = await Promise.all([
              api.getExtras(tripId, false),
              t.status !== 'running' ? api.getVotes(tripId) : Promise.resolve([]),
              t.status !== 'running' ? api.getItineraryVersions(tripId).catch(() => []) : Promise.resolve(null),
            ])
            if (!cancelled) {
              setExtras(ex)
              if (t.status !== 'running') {
                setVotes(v)
                if (vers) setVersions(vers)
              }
            }
          } catch {
            if (!cancelled && t.status !== 'running') setExtras(null)
          }
        }

        if (arts.length) {
          setOpenArtifact((prev) => {
            const newest = arts[arts.length - 1]
            if (prev == null) return newest.id
            const stillThere = arts.some((a) => a.id === prev)
            if (!stillThere) return newest.id
            if (t.status === 'running') return newest.id
            return prev
          })
        }

        if (t.status === 'running') {
          timer = setTimeout(load, 2000)
        } else {
          setReviseBusy(false)
          setLiveBusy(false)
          if (liveCoords.lat != null || live) {
            api
              .getLive(tripId, liveCoords.lat, liveCoords.lon)
              .then((L) => {
                if (!cancelled) setLive(L)
              })
              .catch(() => {})
          }
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

  useEffect(() => {
    if (!trip || trip.status === 'running') return undefined
    let cancelled = false
    setPhotosLoading(true)
    ;(async () => {
      try {
        const res = await api.getPhotos(tripId)
        if (!cancelled) setPhotos(res.photos || [])
      } catch {
        if (!cancelled) setPhotos([])
      } finally {
        if (!cancelled) setPhotosLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tripId, trip?.id, trip?.status, trip?.brief])

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
  const phaseIndex = Math.max(
    0,
    PHASES.findIndex(([key]) => key === (trip.current_phase || 'brief')),
  )
  const progressPct = Math.round(
    ((donePhases.size + (trip.status === 'running' ? 0.35 : trip.status === 'completed' ? 0 : 0)) /
      PHASES.length) *
      100,
  )
  const tip = GEN_TIPS[tripId % GEN_TIPS.length]
  const cover = coverForText(trip.name, trip.brief)
  const latestLive = artifacts[artifacts.length - 1]
  const mapDaySafe = days?.length ? Math.min(mapDay, days.length - 1) : 0
  const mapRoute =
    days?.[mapDaySafe]?.slots?.filter((s) => s.lat != null && s.lon != null) || []
  const showModes = Boolean(idle && itinerary)
  const mode = showModes ? tripMode : 'plan'
  const focusDayIdx = days?.length ? Math.min(openDay < 0 ? mapDaySafe : openDay, days.length - 1) : 0
  const focusDay = days?.[focusDayIdx]
  const eveningEntry = journal.find((j) => j.kind === 'evening' && j.day_index === focusDayIdx)

  const selectDay = (idx) => {
    setMapDay(idx)
    setOpenDay(idx)
  }

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
      setLiveCoords({ lat, lon })
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
    if (!idle || !itinerary || (live && live.can_adjust === false)) return
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

  const recover = async () => {
    setActionError('')
    try {
      const t = await api.recoverTrip(tripId)
      setTrip(t)
    } catch (err) {
      setActionError(err.message)
    }
  }

  const copyShare = async () => {
    setShareMsg('')
    try {
      const res = await api.enableShare(tripId)
      const url = `${window.location.origin}${window.location.pathname}${res.share_path}`
      setShareUrl(url)
      await navigator.clipboard.writeText(url)
      setShareMsg('Ссылка скопирована')
      setTrip({ ...trip, share_token: res.share_token })
    } catch (err) {
      setActionError(err.message)
    }
  }

  const revokeShare = async () => {
    setShareMsg('')
    try {
      await api.revokeShare(tripId)
      setShareUrl('')
      setTrip({ ...trip, share_token: null })
      setShareMsg('Публичная ссылка отозвана')
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

  const rollbackVersion = async (versionId) => {
    if (!window.confirm('Вернуть этот вариант плана? Текущий сохранится в истории.')) return
    setActionError('')
    try {
      const t = await api.rollbackItinerary(tripId, versionId)
      setTrip(t)
      const [arts, ex, vers] = await Promise.all([
        api.getArtifacts(tripId),
        api.getExtras(tripId),
        api.getItineraryVersions(tripId),
      ])
      setArtifacts(arts)
      setExtras(ex)
      setVersions(vers)
      toast('План откатили к выбранной версии')
    } catch (err) {
      setActionError(err.message)
    }
  }

  return (
    <div className="container">
      <button className="ghost" onClick={onBack}>
        ← Все поездки
      </button>

      <DestinationGallery
        photos={photos}
        loading={photosLoading}
        fallbackSrc={cover}
        destination={extras?.destination || ''}
        title={trip.name}
        meta={trip.start_date ? `Старт: ${trip.start_date}` : ''}
      />

      <div className="page-hero trip-hero">
        <div className="row">
          <p className="trip-brief">{plainText(trip.brief)}</p>
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
                {(trip.share_token || shareUrl) && (
                  <button className="ghost" onClick={revokeShare}>
                    Отозвать ссылку
                  </button>
                )}
              </>
            )}
            {(trip.status === 'completed' || trip.status === 'failed') && (
              <button className="ghost" onClick={rerun}>
                Перегенерировать всё
              </button>
            )}
          </div>
        </div>
        {shareMsg && <p className="muted small">{shareMsg}</p>}
        {shareUrl && (
          <div className="share-box">
            <code className="share-url">{shareUrl}</code>
            <div className="row gap wrap">
              <button className="ghost compact" onClick={() => navigator.clipboard.writeText(shareUrl)}>
                Копировать ещё раз
              </button>
              <a className="ghost compact" href={shareUrl}>
                Открыть превью
              </a>
            </div>
          </div>
        )}
      </div>
      <p className="muted notice">
        Черновик от ИИ — адреса и цены ориентировочные.
      </p>

      {mode === 'plan' && idle && hasBookingOffers(extras?.links) && (
        <section className="booking-section booking-top">
          <div className="section-title">
            <h2>Жильё и билеты</h2>
            <span className="muted small">
              {extras.destination}
              {extras.links?.checkin
                ? ` · ${extras.links.checkin} → ${extras.links.checkout}`
                : ''}
            </span>
          </div>
          <LinkButtons links={extras.links} />
        </section>
      )}

      {idle && itinerary && (
        <TripModeBar mode={tripMode} onChange={setTripMode} phaseHint={modeHint} />
      )}

      {mode === 'onsite' && idle && itinerary && (
        <MorningBriefing tripId={tripId} dayIndex={focusDayIdx} />
      )}

      {mode === 'memories' && idle && itinerary && (
        <MemoriesJournal tripId={tripId} days={days || []} />
      )}

      {trip.status === 'running' && (
        <div className="notice-bar">
          Агент работает… Если зависло после перезапуска сервера —{' '}
          <button type="button" className="linkish" onClick={recover}>
            сбросить статус
          </button>
        </div>
      )}
      {trip.error && <div className="error">{trip.error}</div>}
      {downloadError && <div className="error">{downloadError}</div>}
      {actionError && <div className="error">{actionError}</div>}

      {(trip.status === 'running' || (!itinerary && trip.status !== 'failed')) && (
        <section className="gen-panel">
          <div className="gen-panel-top">
            <div>
              <h2>{trip.status === 'running' ? 'Собираю поездку' : 'Готовим документы'}</h2>
              <p className="muted">
                {PHASES[phaseIndex]?.[2] || 'Агент проходит фазы плана'}
              </p>
            </div>
            <div className="gen-pct">{Math.min(progressPct, 95)}%</div>
          </div>
          <div className="gen-bar" aria-hidden="true">
            <div
              className="gen-bar-fill"
              style={{
                width: `${trip.status === 'completed' ? 100 : Math.min(progressPct, 95)}%`,
              }}
            />
          </div>
          <div className="gen-phases">
            {PHASES.map(([key, label, hint], i) => {
              const isDone = donePhases.has(key)
              const isActive = trip.status === 'running' && trip.current_phase === key
              return (
                <div
                  key={key}
                  className={`gen-phase ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
                >
                  <div className="gen-phase-mark">
                    {isDone ? '✓' : isActive ? '⟳' : String(i + 1)}
                  </div>
                  <div>
                    <strong>{label}</strong>
                    <p>{hint}</p>
                  </div>
                </div>
              )
            })}
          </div>
          <p className="gen-tip">{tip}</p>
          {trip.status === 'running' && artifacts.length === 0 && (
            <div className="gen-skeletons" aria-hidden="true">
              <div className="skel skel-wide" />
              <div className="skel" />
              <div className="skel skel-mid" />
              <div className="skel-row">
                <div className="skel skel-card" />
                <div className="skel skel-card" />
                <div className="skel skel-card" />
              </div>
            </div>
          )}
          {trip.status === 'running' && artifacts.length > 0 && (
            <div className="live-feed">
              <div className="section-title">
                <h3>Уже готово</h3>
                <span className="muted small">
                  {artifacts.length} из {PHASES.length}
                  {latestLive ? ` · сейчас: ${PHASE_TITLES[latestLive.phase] || latestLive.phase}` : ''}
                </span>
              </div>
              {artifacts.map((a) => (
                <div key={a.id} className="card slim live-feed-card">
                  <button
                    type="button"
                    className="row expander"
                    onClick={() => setOpenArtifact(openArtifact === a.id ? null : a.id)}
                  >
                    <strong>
                      ✓ {PHASE_TITLES[a.phase] || a.title}
                    </strong>
                    <span>{openArtifact === a.id ? '▾' : '▸'}</span>
                  </button>
                  {openArtifact === a.id && (
                    <div className="live-feed-body">
                      <Markdown>{a.content}</Markdown>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {idle && trip.status !== 'completed' && (
        <div className="phases">
          {PHASES.map(([key, label]) => {
            const isDone = donePhases.has(key)
            return (
              <div key={key} className={`phase ${isDone ? 'done' : ''}`}>
                {isDone ? '✓' : '○'} {label}
              </div>
            )
          })}
        </div>
      )}

      {mode === 'onsite' && itinerary && idle && (
        <section className="live-panel">
          <div className="section-title">
            <h2>Я на месте</h2>
            <button className="ghost compact" onClick={enableLive} disabled={liveBusy}>
              {liveBusy ? '…' : live ? 'Обновить' : 'Включить геолокацию'}
            </button>
          </div>
          {live && (
            <>
              {live.notice && <p className="muted small">{live.notice}</p>}
              <p className="muted small">
                Режим: {live.mode} · сейчас {live.now}
                {live.day?.title ? ` · ${live.day.title}` : ''}
                {live.distance_km_to_next != null
                  ? ` · до следующей точки ~${live.distance_km_to_next} км`
                  : ''}
              </p>
              {live.current_slot && (
                <p>
                  <strong>Сейчас:</strong> {live.current_slot.start}–{live.current_slot.end}{' '}
                  {plainText(live.current_slot.place)}
                </p>
              )}
              {live.next_slot && (
                <p>
                  <strong>Далее:</strong> {live.next_slot.start}–{live.next_slot.end}{' '}
                  {plainText(live.next_slot.place)}
                </p>
              )}
              {live.weather && (
                <p className="muted small">
                  Погода: {live.weather.label}, {live.weather.temp_min}°…{live.weather.temp_max}°
                </p>
              )}
              <div className="row gap wrap">
                <button
                  className="ghost"
                  onClick={() => adjustLive('late')}
                  disabled={liveBusy || !idle || live.can_adjust === false}
                >
                  Опаздываю — сдвинь день
                </button>
                <button
                  className="ghost"
                  onClick={() => adjustLive('rain')}
                  disabled={liveBusy || !idle || live.can_adjust === false}
                >
                  Дождь — перестрой день
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {(mode === 'onsite' || mode === 'plan') && extras?.fast && idle && itinerary && (
        <div className="enrich-banner" role="status" aria-live="polite">
          <span className="enrich-spinner" aria-hidden="true" />
          <div>
            <strong>Догружаем карту и погоду</strong>
            <p className="muted small">
              План уже готов — точки на карте и прогноз появятся через несколько секунд.
            </p>
          </div>
        </div>
      )}

      {(mode === 'onsite' || mode === 'plan') && extras?.fast && idle && itinerary && (
        <section className="weather-strip weather-loading" aria-busy="true">
          <h2>Погода</h2>
          <div className="weather-row">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="weather-card skel-card" aria-hidden="true">
                <div className="skel skel-mid" />
                <div className="skel" />
              </div>
            ))}
          </div>
          <p className="muted small">Прогноз подгружается…</p>
        </section>
      )}

      {(mode === 'onsite' || mode === 'plan') && extras?.weather?.length > 0 && (
        <section className="weather-strip">
          <h2>Погода (ориентир)</h2>
          <p className="muted small">
            Прогноз Open-Meteo
            {extras.start_date ? ` с ${extras.start_date}` : ' от сегодня'} на {extras.days_count}{' '}
            дн.
          </p>
          <div className="weather-row">
            {extras.weather.map((w) => {
              const dayIdx = days?.findIndex((d) => d.date === w.date) ?? -1
              const active = dayIdx >= 0 && dayIdx === mapDaySafe
              return (
                <button
                  key={w.date}
                  type="button"
                  className={`weather-card ${active ? 'active' : ''} ${dayIdx >= 0 ? 'clickable' : ''}`}
                  onClick={() => {
                    if (dayIdx >= 0) selectDay(dayIdx)
                  }}
                  disabled={dayIdx < 0}
                >
                  <div className="weather-date">{w.date.slice(5)}</div>
                  <div className="weather-label">{w.label}</div>
                  <div className="weather-temp">
                    {w.temp_min}° … {w.temp_max}°
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      )}

      {(mode === 'onsite' || mode === 'plan') && extras?.fast && idle && itinerary && (
        <section className="map-section map-loading" aria-busy="true">
          <div className="section-title">
            <h2>Карта дня</h2>
            <span className="muted small">{extras.destination || '…'}</span>
          </div>
          <div className="map-placeholder">
            <span className="enrich-spinner" aria-hidden="true" />
            <p>
              <strong>Строим карту маршрута</strong>
              <span className="muted"> Ищем координаты мест — обычно меньше минуты.</span>
            </p>
          </div>
        </section>
      )}

      {(mode === 'onsite' || mode === 'plan') && extras?.center && (
        <section className="map-section">
          <div className="section-title">
            <h2>Карта дня</h2>
            <span className="muted small">{extras.destination}</span>
          </div>
          {days?.length > 0 && (
            <div className="map-day-chips" role="tablist" aria-label="День на карте">
              {days.map((day, idx) => (
                <button
                  key={`map-day-${idx}`}
                  type="button"
                  role="tab"
                  aria-selected={mapDaySafe === idx}
                  className={`chip ${mapDaySafe === idx ? 'selected' : ''}`}
                  onClick={() => selectDay(idx)}
                >
                  День {idx + 1}
                  {day.weather ? ` · ${day.weather.temp_max}°` : ''}
                </button>
              ))}
            </div>
          )}
          <TripMap center={extras.center} places={extras.places} route={mapRoute} />
          {days?.length > 0 && (
            <p className="muted small map-hint">
              {mapRoute.length > 1
                ? `Маршрут дня ${mapDaySafe + 1}: ${mapRoute.length} точек на карте`
                : mapRoute.length === 1
                  ? `Одна точка с координатами в дне ${mapDaySafe + 1}`
                  : 'Показан центр направления'}
            </p>
          )}
        </section>
      )}

      {mode === 'plan' && (
        <section className="plan-days-section">
          <div className="section-title">
            <h2>План по дням</h2>
            {itinerary && idle && (
              <button className="ghost compact" onClick={() => rerunPhase('itinerary')}>
                Перегенерировать план
              </button>
            )}
          </div>
          {!itinerary && (
            <div className="await-card">
              <img src={cover} alt="" />
              <div>
                <strong>План по дням ещё собирается</strong>
                <p className="muted">
                  {trip.status === 'running'
                    ? 'Скоро появятся слоты, карта и ссылки на бронирование. Готовые фазы уже выше.'
                    : 'Запустите генерацию или перегенерируйте план.'}
                </p>
              </div>
            </div>
          )}
          {itinerary && !days && (
            <div className="await-card compact">
              <div>
                <strong>Раскладываю план по дням…</strong>
                <p className="muted">Секунду — появятся слоты, без стены текста.</p>
              </div>
            </div>
          )}
          {itinerary && days && (
            <div className="day-cards">
              {days.map((day, idx) => (
                <div
                  key={`${day.title}-${idx}`}
                  className={`day-card ${openDay === idx ? 'open' : ''} ${mapDaySafe === idx ? 'on-map' : ''}`}
                >
                  <button
                    className="row expander day-expander"
                    onClick={() => {
                      if (openDay === idx) setOpenDay(-1)
                      else selectDay(idx)
                    }}
                  >
                    <div className="day-expander-copy">
                      <strong>
                        {plainText(day.title)}
                        {day.date ? ` · ${day.date}` : ''}
                      </strong>
                      {day.weather && (
                        <span className="day-weather-badge" title="Прогноз на день">
                          <em>{day.weather.label}</em>
                          <span>
                            {day.weather.temp_min}°…{day.weather.temp_max}°
                          </span>
                        </span>
                      )}
                    </div>
                    <span className="day-expander-chevron">{openDay === idx ? '▾' : '▸'}</span>
                  </button>
                  {openDay === idx && (
                    <div className="day-body">
                      {day.weather && (
                        <div className="day-weather-panel">
                          <strong>{day.weather.label}</strong>
                          <span>
                            {day.weather.temp_min}° … {day.weather.temp_max}°
                          </span>
                          <em className="muted small">Open-Meteo, ориентир</em>
                        </div>
                      )}
                      <DayQuest tripId={tripId} dayIndex={idx} dayTitle={day.title} />
                      {day.slots?.length > 0 ? (
                        <div className="slot-list">
                          {day.slots.map((slot, slotIdx) => {
                            const counts = voteCounts(slot.slot_key)
                            return (
                              <div key={slot.slot_key} className="slot-card">
                                <div className="row slot-card-head">
                                  <span className="slot-num">{slotIdx + 1}</span>
                                  <strong>
                                    {slot.start}–{slot.end}
                                  </strong>
                                  <span className="slot-place">{plainText(slot.place)}</span>
                                  {/уточнить/i.test(slot.place || '') && (
                                    <span className="slot-unverified" title="Место не найдено на карте">
                                      уточнить
                                    </span>
                                  )}
                                </div>
                                {slot.body && <Markdown>{slot.body}</Markdown>}
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
        </section>
      )}

      {mode === 'onsite' && idle && itinerary && <StreetSmart tripId={tripId} />}

      {mode === 'onsite' && idle && itinerary && (
        <EveningCheckin
          tripId={tripId}
          dayIndex={focusDayIdx}
          slots={focusDay?.slots || []}
          existing={eveningEntry}
          onSaved={async () => {
            try {
              setJournal(await api.listJournal(tripId))
            } catch {
              /* ignore */
            }
          }}
        />
      )}

      {mode === 'plan' && votes.length > 0 && idle && (
        <section className="chat-panel">
          <div className="section-title">
            <h2>Голоса друзей</h2>
            <button className="primary compact" onClick={rebuildVotes}>
              Пересобрать по голосам
            </button>
          </div>
          <p className="vote-summary">
            <strong>{votes.length}</strong> отметок от{' '}
            <strong>{new Set(votes.map((v) => v.voter)).size}</strong> человек
          </p>
        </section>
      )}

      {mode === 'plan' && itinerary && (
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

      {mode === 'plan' && idle && versions.length > 0 && (
        <section className="history-panel">
          <div className="section-title">
            <h2>История плана</h2>
            <span className="muted small">{versions.length}</span>
          </div>
          <p className="muted small">
            Снимки до правок чатом, live-adjust и пересборок. Можно откатиться.
          </p>
          <div className="history-list">
            {versions.map((v) => (
              <div key={v.id} className="card slim history-card">
                <button
                  type="button"
                  className="row expander"
                  onClick={() => setOpenVersion(openVersion === v.id ? null : v.id)}
                >
                  <div className="history-meta">
                    <strong>{VERSION_SOURCE[v.source] || v.source}</strong>
                    <span className="muted small">
                      {formatVersionTime(v.created_at)}
                      {v.source_meta ? ` · ${v.source_meta.slice(0, 80)}` : ''}
                    </span>
                  </div>
                  <span>{openVersion === v.id ? '▾' : '▸'}</span>
                </button>
                {openVersion === v.id && (
                  <div className="history-body">
                    <Markdown>{v.content}</Markdown>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => rollbackVersion(v.id)}
                    >
                      Вернуть этот вариант
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {mode === 'plan' && idle && (
        <section className="docs-section">
          <h2>Документы</h2>
          {otherArtifacts.length === 0 && (
            <div className="await-card compact">
              <img src="/images/empty-bag.jpg" alt="" />
              <div>
                <strong>Документы появятся по ходу</strong>
                <p className="muted">ТЗ, бюджет и чеклист откроются здесь, как только фазы завершатся.</p>
              </div>
            </div>
          )}
          {otherArtifacts.map((a) => (
            <div key={a.id} className="card slim">
              <button
                className="row expander"
                onClick={() => setOpenArtifact(openArtifact === a.id ? null : a.id)}
              >
                <strong>{PHASE_TITLES[a.phase] || a.title}</strong>
                <span className="row gap">
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
                  <span>{openArtifact === a.id ? '▾' : '▸'}</span>
                </span>
              </button>
              {openArtifact === a.id && <Markdown>{a.content}</Markdown>}
            </div>
          ))}
        </section>
      )}

      <AskChat tripId={tripId} disabled={false} />
    </div>
  )
}
