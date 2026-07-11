import { useEffect, useState } from 'react'
import { api } from './api.js'
import { toast } from './Toast.jsx'

const MOODS = [
  { id: 'great', label: 'Огонь', emoji: '🔥' },
  { id: 'wow', label: 'Вау', emoji: '✨' },
  { id: 'ok', label: 'Норм', emoji: '🙂' },
  { id: 'tired', label: 'Устал', emoji: '😮‍💨' },
  { id: 'meh', label: 'Так себе', emoji: '😐' },
]

const MODE_META = {
  plan: { label: 'План', hint: 'Маршрут, документы, правки' },
  onsite: { label: 'На месте', hint: 'Сегодня и live' },
  memories: { label: 'Воспоминания', hint: 'Дневник поездки' },
}

export function TripModeBar({ mode, onChange, phaseHint }) {
  return (
    <nav className="trip-os-bar" aria-label="Режим поездки">
      <div className="trip-os-bar-copy">
        <span className="trip-os-bar-label muted small">Режим</span>
        <span className="muted small trip-os-bar-hint">
          {MODE_META[mode]?.hint}
          {phaseHint && phaseHint !== mode
            ? ` · сейчас уместнее: ${MODE_META[phaseHint]?.label || phaseHint}`
            : ''}
        </span>
      </div>
      <div className="trip-os-tabs" role="tablist">
        {Object.entries(MODE_META).map(([id, meta]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={mode === id}
            className={`trip-os-tab ${mode === id ? 'active' : ''} ${phaseHint === id ? 'suggested' : ''}`}
            onClick={() => onChange(id)}
          >
            {meta.label}
          </button>
        ))}
      </div>
    </nav>
  )
}

export function MorningBriefing({ tripId, dayIndex }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const b = await api.tripBriefing(tripId, dayIndex)
        if (!cancelled) {
          setData(b)
          setError('')
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Не удалось загрузить брифинг')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tripId, dayIndex])

  if (error) return <div className="error">{error}</div>
  if (!data) return <p className="muted small">Собираю утренний брифинг…</p>

  return (
    <section className="trip-os-briefing">
      <header className="trip-os-briefing-head">
        <div>
          <p className="trip-os-kicker">Сегодня</p>
          <h2 className="trip-os-day-title">{data.day_title}</h2>
        </div>
        <div className="trip-os-briefing-meta">
          <span className="muted small">{data.day_date || `День ${data.day_index + 1}`}</span>
          {data.weather && (
            <span className="trip-os-weather">
              {data.weather.label} · {data.weather.temp_min}°…{data.weather.temp_max}°
            </span>
          )}
        </div>
      </header>
      {data.tip && (
        <p className="trip-os-tip">
          <strong>Совет дня.</strong> {data.tip}
        </p>
      )}
      {data.phrase && (
        <p className="trip-os-phrase muted small">
          Фраза: <em>{data.phrase.local || data.phrase.latin}</em>
          {data.phrase.ru ? ` — ${data.phrase.ru}` : ''}
        </p>
      )}
      {data.quest_teaser && (
        <p className="muted small trip-os-quest">Квест: {data.quest_teaser}</p>
      )}
      {data.slots_preview?.length > 0 && (
        <ol className="trip-os-slots">
          {data.slots_preview.map((s) => (
            <li key={s.slot_key || `${s.start}-${s.place}`}>
              <strong>
                {s.start}–{s.end}
              </strong>{' '}
              {s.place}
            </li>
          ))}
          {data.slots_total > data.slots_preview.length && (
            <li className="muted">ещё {data.slots_total - data.slots_preview.length} слотов в плане</li>
          )}
        </ol>
      )}
      {data.emergency?.title && (
        <p className="muted small">
          Экстренно: {data.emergency.title}
          {data.emergency.value ? ` · ${data.emergency.value}` : ''}
        </p>
      )}
    </section>
  )
}

export function EveningCheckin({ tripId, dayIndex, slots = [], existing, onSaved }) {
  const [mood, setMood] = useState(existing?.mood || 'ok')
  const [content, setContent] = useState(existing?.content || '')
  const [done, setDone] = useState(() => new Set(existing?.done_slots || []))
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setMood(existing?.mood || 'ok')
    setContent(existing?.content || '')
    setDone(new Set(existing?.done_slots || []))
  }, [existing])

  const toggle = (key) => {
    setDone((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await api.eveningCheckin(tripId, {
        day_index: dayIndex,
        mood,
        content,
        done_slots: [...done],
      })
      toast('Вечерний чекин сохранён', 'ok')
      if (onSaved) await onSaved()
    } catch (err) {
      toast(err.message || 'Не удалось сохранить', 'err')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="trip-os-evening">
      <header className="trip-os-evening-head">
        <p className="trip-os-kicker">Конец дня</p>
        <h2>Вечерний чекин</h2>
        <p className="muted small">
          Как прошёл день {dayIndex + 1}? Отметьте сделанное и настроение — это уйдёт в воспоминания.
        </p>
      </header>
      <form className="trip-os-evening-form" onSubmit={submit}>
        <div className="trip-os-moods" role="group" aria-label="Настроение">
          {MOODS.map((m) => (
            <button
              key={m.id}
              type="button"
              className={`trip-os-mood ${mood === m.id ? 'active' : ''}`}
              onClick={() => setMood(m.id)}
            >
              <span aria-hidden="true">{m.emoji}</span>
              {m.label}
            </button>
          ))}
        </div>
        {slots.length > 0 && (
          <div className="trip-os-done-list">
            {slots.map((s) => (
              <label key={s.slot_key} className="trip-os-done-item">
                <input
                  type="checkbox"
                  checked={done.has(s.slot_key)}
                  onChange={() => toggle(s.slot_key)}
                />
                <span>
                  {s.start}–{s.end} · {s.place}
                </span>
              </label>
            ))}
          </div>
        )}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Что запомнилось? Куда вернуться? Что вычеркнуть?"
          rows={3}
        />
        <button className="primary" type="submit" disabled={busy}>
          {busy ? 'Сохраняю…' : existing ? 'Обновить чекин' : 'Сохранить день'}
        </button>
      </form>
    </section>
  )
}

export function MemoriesJournal({ tripId, days = [] }) {
  const [entries, setEntries] = useState([])
  const [note, setNote] = useState('')
  const [dayIndex, setDayIndex] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const reload = async () => {
    const list = await api.listJournal(tripId)
    setEntries(list)
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await api.listJournal(tripId)
        if (!cancelled) {
          setEntries(list)
          setError('')
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Дневник недоступен')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tripId])

  const addNote = async (e) => {
    e.preventDefault()
    if (!note.trim()) return
    setBusy(true)
    try {
      await api.createJournal(tripId, {
        day_index: dayIndex,
        kind: 'note',
        content: note.trim(),
      })
      setNote('')
      await reload()
      toast('Запись в дневнике', 'ok')
    } catch (err) {
      toast(err.message || 'Не удалось сохранить', 'err')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    try {
      await api.deleteJournal(tripId, id)
      await reload()
    } catch (err) {
      toast(err.message || 'Не удалось удалить', 'err')
    }
  }

  const moodLabel = (id) => MOODS.find((m) => m.id === id)?.label || id

  return (
    <section className="trip-os-memories">
      <div className="section-title">
        <h2>Дневник поездки</h2>
        <span className="muted small">{entries.length} записей</span>
      </div>
      {error && <div className="error">{error}</div>}

      <form className="trip-os-note-form" onSubmit={addNote}>
        {days.length > 0 && (
          <select value={dayIndex} onChange={(e) => setDayIndex(Number(e.target.value))}>
            {days.map((d, i) => (
              <option key={i} value={i}>
                {d.title || `День ${i + 1}`}
                {d.date ? ` · ${d.date}` : ''}
              </option>
            ))}
          </select>
        )}
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Фото в голове, вкус, случайная встреча…"
          rows={2}
        />
        <button className="primary" type="submit" disabled={busy || !note.trim()}>
          Добавить
        </button>
      </form>

      {entries.length === 0 && (
        <div className="await-card compact">
          <img src="/images/empty-bag.jpg" alt="" />
          <div>
            <strong>Пока пусто</strong>
            <p className="muted">Вечерние чекины из режима «На месте» и заметки появятся здесь.</p>
          </div>
        </div>
      )}

      <div className="trip-os-timeline">
        {entries.map((e) => (
          <article key={e.id} className={`trip-os-entry ${e.kind}`}>
            <header>
              <strong>
                {e.kind === 'evening' ? 'Вечер' : 'Заметка'} · день {e.day_index + 1}
              </strong>
              {e.mood && <span className="trip-os-entry-mood">{moodLabel(e.mood)}</span>}
              <button type="button" className="ghost compact" onClick={() => remove(e.id)}>
                Удалить
              </button>
            </header>
            {e.content && <p>{e.content}</p>}
            {e.done_slots?.length > 0 && (
              <p className="muted small">Сделано слотов: {e.done_slots.length}</p>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

export { MOODS, MODE_META }
