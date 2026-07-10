import { useEffect, useState } from 'react'
import Markdown from './Markdown.jsx'
import { coverForText } from './covers.js'

const SEEN_KEY = 'travel_seen_example'

export const EXAMPLE = {
  name: 'Батуми, 3 дн.',
  brief: 'Море, набережная и еда. Без аренды авто. Бюджет ориентир ~40 000 ₽ на двоих.',
  start: '2026-07-18',
  cover: coverForText('Батуми море пляж'),
  days: [
    {
      title: 'День 1 — прибытие',
      slots: [
        { time: '11:00–13:00', place: 'Батумский бульвар', note: 'Прогулка вдоль моря, кофе у набережной.' },
        { time: '14:00–16:00', place: 'Старый Батуми', note: 'Улочки, площадь Европы, фото у алфавитной башни.' },
        { time: '19:00–21:00', place: 'Ужин у порта', note: 'Местная кухня: хачапури, свежая рыба.' },
      ],
    },
    {
      title: 'День 2 — пляж и город',
      slots: [
        { time: '10:00–13:00', place: 'Пляж Gonio', note: 'Утро у воды, зонт и вода с собой.' },
        { time: '15:00–17:00', place: 'Ботанический сад', note: 'Виды на залив, тень и прохлада.' },
        { time: '20:00–21:30', place: 'Поющий фонтан', note: 'Вечернее шоу на площади.' },
      ],
    },
    {
      title: 'День 3 — спокойный выезд',
      slots: [
        { time: '10:00–12:00', place: 'Рынок', note: 'Специи, чурчхела, сувениры.' },
        { time: '13:00–14:30', place: 'Обед и трансфер', note: 'Лёгкий обед, дорога в аэропорт.' },
      ],
    },
  ],
  budget: 'Жильё ~18 000 ₽ · еда ~12 000 ₽ · транспорт ~4 000 ₽ · итого ~40 000 ₽ на двоих (ориентир).',
  checklist: ['Паспорт / загран', 'Купальник и крем SPF', 'Карта / наличные лари', 'Зарядка и адаптер'],
}

export function hasSeenExample() {
  try {
    return localStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

export function markExampleSeen() {
  try {
    localStorage.setItem(SEEN_KEY, '1')
  } catch {
    /* ignore */
  }
}

export default function ExamplePreview({ open, onClose }) {
  const [day, setDay] = useState(0)

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const current = EXAMPLE.days[day]

  return (
    <div className="example-overlay" role="dialog" aria-modal="true" aria-label="Пример готового плана">
      <button type="button" className="example-backdrop" aria-label="Закрыть" onClick={onClose} />
      <div className="example-sheet">
        <div className="example-cover">
          <img src={EXAMPLE.cover} alt="" />
          <div className="example-cover-veil" />
          <div className="example-cover-copy">
            <p className="hero-kicker">Пример · 20 секунд</p>
            <h2>{EXAMPLE.name}</h2>
            <p>{EXAMPLE.brief}</p>
          </div>
          <button type="button" className="ghost compact example-close" onClick={onClose}>
            Закрыть
          </button>
        </div>

        <div className="example-body">
          <p className="muted small">Так выглядит готовая поездка: дни, слоты, бюджет и чеклист.</p>

          <div className="example-days">
            {EXAMPLE.days.map((d, i) => (
              <button
                key={d.title}
                type="button"
                className={`chip ${i === day ? 'selected' : ''}`}
                onClick={() => setDay(i)}
              >
                {d.title.split('—')[0].trim()}
              </button>
            ))}
          </div>

          <div className="day-card example-day">
            <strong>{current.title}</strong>
            <div className="slot-list">
              {current.slots.map((s) => (
                <div key={s.time + s.place} className="slot-card">
                  <div className="row">
                    <strong>{s.time}</strong>
                    <span>{s.place}</span>
                  </div>
                  <p className="muted small">{s.note}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="example-docs">
            <div className="card slim">
              <strong>Бюджет</strong>
              <Markdown>{EXAMPLE.budget}</Markdown>
            </div>
            <div className="card slim">
              <strong>Чеклист</strong>
              <ul className="example-check">
                {EXAMPLE.checklist.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <button type="button" className="primary example-cta" onClick={onClose}>
            Понятно — спланировать свою
          </button>
        </div>
      </div>
    </div>
  )
}
