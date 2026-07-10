import { useEffect, useState } from 'react'
import { api } from './api.js'
import { toast } from './Toast.jsx'

const TABS = [
  ['survival', 'Выживание'],
  ['traps', 'Не ведись'],
  ['taste', 'Вкус'],
  ['arrival', '90 минут'],
]

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast('Скопировано')
  } catch {
    toast('Не удалось скопировать', 'err')
  }
}

function questStorageKey(tripId, dayIndex) {
  return `travel_quest_${tripId}_${dayIndex}`
}

export function loadQuestChecks(tripId, dayIndex) {
  try {
    const raw = localStorage.getItem(questStorageKey(tripId, dayIndex))
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

export function saveQuestChecks(tripId, dayIndex, map) {
  try {
    localStorage.setItem(questStorageKey(tripId, dayIndex), JSON.stringify(map))
  } catch {
    /* ignore */
  }
}

export function DayQuest({ tripId, dayIndex, dayTitle }) {
  const [missions, setMissions] = useState(null)
  const [checks, setChecks] = useState(() => loadQuestChecks(tripId, dayIndex))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async (force = false) => {
    setBusy(true)
    setError('')
    try {
      const data = await api.streetQuest(tripId, dayIndex)
      setMissions(data.missions || [])
      if (force) {
        setChecks({})
        saveQuestChecks(tripId, dayIndex, {})
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    setChecks(loadQuestChecks(tripId, dayIndex))
    load()
  }, [tripId, dayIndex])

  const toggle = (id) => {
    setChecks((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      saveQuestChecks(tripId, dayIndex, next)
      return next
    })
  }

  return (
    <div className="day-quest">
      <div className="section-title">
        <h3>Квест дня</h3>
        <button type="button" className="ghost compact" onClick={() => load(true)} disabled={busy}>
          {busy ? '…' : 'Обновить'}
        </button>
      </div>
      <p className="muted small">Три микромиссии · {dayTitle}</p>
      {error && <div className="error">{error}</div>}
      {!missions && !error && <p className="muted small">Загружаю…</p>}
      {missions && (
        <ul className="quest-list">
          {missions.map((m) => (
            <li key={m.id}>
              <label className={`quest-item ${checks[m.id] ? 'done' : ''}`}>
                <input
                  type="checkbox"
                  checked={Boolean(checks[m.id])}
                  onChange={() => toggle(m.id)}
                />
                <span>{m.text}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function StreetSmart({ tripId }) {
  const [tab, setTab] = useState('survival')
  const [data, setData] = useState({
    survival: null,
    traps: null,
    taste: null,
    arrival: null,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const ensure = async (key, loader) => {
    if (data[key]) return data[key]
    setBusy(true)
    setError('')
    try {
      const res = await loader()
      setData((prev) => ({ ...prev, [key]: res }))
      return res
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    ensure('survival', () => api.streetSurvival(tripId))
  }, [tripId])

  useEffect(() => {
    if (tab === 'survival') ensure('survival', () => api.streetSurvival(tripId))
    if (tab === 'traps') ensure('traps', () => api.streetTraps(tripId))
    if (tab === 'taste') ensure('taste', () => api.streetTaste(tripId))
    if (tab === 'arrival') ensure('arrival', () => api.streetArrival(tripId))
  }, [tab, tripId])

  const enrichPhrases = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.streetSurvivalEnrich(tripId)
      setData((prev) => ({ ...prev, survival: res }))
      toast('Фразы обновлены')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const enrichTraps = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.streetTrapsEnrich(tripId)
      setData((prev) => ({ ...prev, traps: res }))
      toast('Ловушки обновлены')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const survival = data.survival
  const traps = data.traps
  const taste = data.taste
  const arrival = data.arrival

  return (
    <section className="street-smart">
      <div className="section-title">
        <h2>На улице</h2>
        <span className="muted small">Street Smart</span>
      </div>
      <p className="muted small street-lead">
        Карманный режим: фразы, ловушки, вкус и первые 90 минут — чтобы не выглядеть туристом.
      </p>

      <div className="street-tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            className={`chip ${tab === id ? 'selected' : ''}`}
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="error">{error}</div>}
      {busy && !survival && tab === 'survival' && <p className="muted">Загружаю…</p>}

      {tab === 'survival' && survival && (
        <div className="street-panel">
          <div className="street-meta">
            <strong>{survival.destination}</strong>
            <span className="muted small">
              {survival.region_label} · {survival.currency}
            </span>
          </div>

          <h3>Экстренное</h3>
          <div className="street-emergency">
            {survival.emergency.map((e) => (
              <button
                key={e.title}
                type="button"
                className="emergency-chip"
                onClick={() => copyText(e.value)}
              >
                <em>{e.title}</em>
                <strong>{e.value}</strong>
              </button>
            ))}
          </div>

          <h3>Ориентиры</h3>
          <ul className="street-tips">
            {survival.tips.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>

          <button
            type="button"
            className="ghost"
            onClick={() => copyText(survival.taxi_line)}
          >
            Фраза для такси — копировать
          </button>

          <div className="section-title" style={{ marginTop: 16 }}>
            <h3>Фразы</h3>
            <button type="button" className="ghost compact" onClick={enrichPhrases} disabled={busy}>
              Оживить фразы
            </button>
          </div>
          <div className="phrase-grid">
            {survival.phrases.map((p) => (
              <button
                key={p.local + p.ru}
                type="button"
                className="phrase-card"
                onClick={() => copyText(`${p.local} (${p.latin}) — ${p.ru}`)}
              >
                <strong>{p.local}</strong>
                <span className="muted small">{p.latin}</span>
                <em>{p.ru}</em>
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === 'traps' && (
        <div className="street-panel">
          {!traps && <p className="muted">Загружаю…</p>}
          {traps && (
            <>
              <div className="section-title">
                <h3>Не ведись</h3>
                <button type="button" className="ghost compact" onClick={enrichTraps} disabled={busy}>
                  Ещё ловушки
                </button>
              </div>
              <div className="trap-list">
                {traps.traps.map((t) => (
                  <article key={t.title} className="trap-card">
                    <strong>{t.title}</strong>
                    <p>{t.how}</p>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'taste' && (
        <div className="street-panel">
          {!taste && <p className="muted">Загружаю…</p>}
          {taste && (
            <>
              <h3>Вкусовой паспорт</h3>
              <div className="taste-grid">
                {taste.items.map((item) => (
                  <article key={item.dish} className="taste-card">
                    <strong>{item.dish}</strong>
                    <span className="muted small">{item.where}</span>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'arrival' && (
        <div className="street-panel">
          {!arrival && <p className="muted">Загружаю…</p>}
          {arrival && (
            <>
              <h3>Первые 90 минут</h3>
              {arrival.start_date && (
                <p className="muted small">Старт поездки: {arrival.start_date}</p>
              )}
              <ol className="arrival-steps">
                {arrival.steps.map((s) => (
                  <li key={s.n}>
                    <span className="arrival-n">{s.n}</span>
                    <span>{s.text}</span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      )}
    </section>
  )
}
