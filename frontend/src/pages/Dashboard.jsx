import { useEffect, useState } from 'react'
import { api } from '../api.js'

const STATUS_LABELS = {
  draft: ['Черновик', 'badge'],
  running: ['Планирую…', 'badge running'],
  completed: ['Готов', 'badge done'],
  failed: ['Ошибка', 'badge failed'],
}

const INTERESTS = [
  'Море / пляж',
  'Еда и кафе',
  'Музеи / культура',
  'Природа / прогулки',
  'Ночная жизнь',
  'Шоппинг',
  'С детьми',
  'Без экстрима',
]

const STEPS = ['Куда', 'Срок', 'Бюджет', 'Интересы']

function buildBrief({ destination, days, budget, interests, notes, travelers, startDate }) {
  const parts = [
    `Направление: ${destination.trim()}.`,
    `Длительность: ${days} дн.`,
  ]
  if (startDate) parts.push(`Дата начала: ${startDate}.`)
  if (budget.trim()) parts.push(`Бюджет: ${budget.trim()}.`)
  if (travelers.trim()) parts.push(`Путешественники: ${travelers.trim()}.`)
  if (interests.length) parts.push(`Интересы: ${interests.join(', ')}.`)
  if (notes.trim()) parts.push(`Дополнительно: ${notes.trim()}.`)
  return parts.join(' ')
}

function defaultStartDate() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

export default function Dashboard({ onOpen }) {
  const [trips, setTrips] = useState([])
  const [step, setStep] = useState(0)
  const [destination, setDestination] = useState('')
  const [days, setDays] = useState('5')
  const [startDate, setStartDate] = useState(defaultStartDate)
  const [budget, setBudget] = useState('')
  const [travelers, setTravelers] = useState('2 взрослых')
  const [interests, setInterests] = useState([])
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const refresh = () => api.listTrips().then(setTrips).catch((e) => setError(e.message))

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 3000)
    return () => clearInterval(timer)
  }, [])

  const toggleInterest = (item) => {
    setInterests((prev) =>
      prev.includes(item) ? prev.filter((x) => x !== item) : [...prev, item],
    )
  }

  const canNext = () => {
    if (step === 0) return destination.trim().length >= 2
    if (step === 1) return Number(days) >= 1 && Number(days) <= 30 && Boolean(startDate)
    if (step === 2) return true
    return interests.length > 0 || notes.trim().length >= 3
  }

  const create = async () => {
    setError('')
    if (!canNext()) {
      setError('Заполните шаг или выберите интересы / добавьте заметку')
      return
    }
    setBusy(true)
    try {
      const brief = buildBrief({
        destination,
        days,
        budget,
        interests,
        notes,
        travelers,
        startDate,
      })
      const name = `${destination.trim()}, ${days} дн.`
      const trip = await api.createTrip(name.slice(0, 255), brief, startDate)
      await api.runTrip(trip.id)
      setDestination('')
      setDays('5')
      setStartDate(defaultStartDate())
      setBudget('')
      setTravelers('2 взрослых')
      setInterests([])
      setNotes('')
      setStep(0)
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
      <div className="page-hero">
        <h1>Куда отправимся?</h1>
        <p>
          Ответьте на несколько вопросов — агент соберёт план по дням, бюджет и чеклист.
          Цены и адреса ориентировочные.
        </p>
      </div>

      <section className="card">
        <div className="wizard-steps">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={`wizard-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            >
              {i < step ? '✓ ' : `${i + 1}. `}
              {label}
            </div>
          ))}
        </div>

        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault()
            if (step < STEPS.length - 1) {
              if (canNext()) setStep(step + 1)
              else setError('Заполните поле, чтобы продолжить')
            } else {
              create()
            }
          }}
        >
          {step === 0 && (
            <>
              <div>
                <label className="field-label">Город или страна</label>
                <input
                  placeholder="Например: Батуми"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <div>
                <label className="field-label">Кто едет</label>
                <input
                  placeholder="2 взрослых, с ребёнком…"
                  value={travelers}
                  onChange={(e) => setTravelers(e.target.value)}
                />
              </div>
            </>
          )}

          {step === 1 && (
            <div className="form-grid">
              <div>
                <label className="field-label">Сколько дней</label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label">Дата начала</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <label className="field-label">Бюджет (необязательно)</label>
              <input
                placeholder="50 000 ₽ на двоих"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                autoFocus
              />
              <p className="muted" style={{ marginTop: 8 }}>
                Можно пропустить — агент предложит ориентир сам.
              </p>
            </div>
          )}

          {step === 3 && (
            <>
              <div>
                <label className="field-label">Что важно в поездке</label>
                <div className="chip-row">
                  {INTERESTS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      className={`chip ${interests.includes(item) ? 'selected' : ''}`}
                      onClick={() => toggleInterest(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="field-label">Ещё детали</label>
                <textarea
                  placeholder="Без аренды авто, хотим местную кухню…"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </>
          )}

          {error && <div className="error">{error}</div>}

          <div className="wizard-nav">
            <button
              type="button"
              className="ghost"
              disabled={step === 0 || busy}
              onClick={() => {
                setError('')
                setStep((s) => Math.max(0, s - 1))
              }}
            >
              Назад
            </button>
            <button className="primary" disabled={busy || !canNext()}>
              {busy
                ? 'Запускаю агента…'
                : step < STEPS.length - 1
                  ? 'Далее'
                  : 'Спланировать поездку'}
            </button>
          </div>
        </form>
      </section>

      <div className="section-title">
        <h2>Мои поездки</h2>
        <span className="muted">{trips.length}</span>
      </div>
      {trips.length === 0 && <p className="muted">Пока пусто — пройдите мастер выше.</p>}
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
              {t.status === 'running' && <p className="muted">Фаза: {t.current_phase || '…'}</p>}
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
    </div>
  )
}
