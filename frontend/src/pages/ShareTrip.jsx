import { useEffect, useState } from 'react'
import LinkButtons, { FeasibilityBadge } from '../LinkButtons.jsx'
import Markdown, { plainText } from '../Markdown.jsx'
import { api } from '../api.js'

const VOTER_KEY = 'travel_share_voter'

export default function ShareTrip({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [voter, setVoter] = useState(() => localStorage.getItem(VOTER_KEY) || '')
  const [openDay, setOpenDay] = useState(0)
  const [busy, setBusy] = useState(false)

  const load = () =>
    api
      .getShared(token)
      .then(setData)
      .catch((err) => setError(err.message))

  useEffect(() => {
    load()
  }, [token])

  const myVote = (slotKey) => {
    const name = voter.trim()
    if (!name || !data?.votes?.[slotKey]) return null
    const found = data.votes[slotKey].voters?.find((v) => v.voter === name)
    return found?.value || null
  }

  const vote = async (dayIndex, slotKey, value) => {
    const name = voter.trim()
    if (name.length < 1) {
      setError('Введите имя, чтобы голосовать')
      return
    }
    localStorage.setItem(VOTER_KEY, name)
    setBusy(true)
    setError('')
    try {
      await api.castVote(token, {
        voter: name,
        day_index: dayIndex,
        slot_key: slotKey,
        value,
      })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !data)
    return (
      <div className="container">
        <div className="error">{error}</div>
      </div>
    )
  if (!data) return <div className="container muted">Загрузка совместного плана…</div>

  const hasAnySlots = (data.days || []).some((d) => (d.slots || []).length > 0)

  return (
    <div className="container">
      <div className="page-hero">
        <h1>{data.name}</h1>
        <p>{plainText(data.brief)}</p>
        <p className="muted small">Совместный план — отметьте, что хотите / не хотите</p>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="card slim voter-sticky">
        <label className="field-label">Как вас зовут</label>
        <input
          value={voter}
          onChange={(e) => setVoter(e.target.value)}
          placeholder="Имя для голосов"
          maxLength={40}
        />
      </div>

      {data.links && (
        <section className="booking-section booking-top">
          <h2>Жильё и билеты</h2>
          <LinkButtons links={data.links} />
        </section>
      )}

      <section>
        <h2>План по дням</h2>
        {!hasAnySlots && (
          <p className="muted">
            Владелец ещё не сгенерировал слоты по времени — покажите ему, что нужно перегенерировать
            план.
          </p>
        )}
        <div className="day-cards">
          {(data.days || []).map((day, idx) => (
            <div key={`${day.title}-${idx}`} className="day-card">
              <button
                className="row expander"
                onClick={() => setOpenDay(openDay === idx ? -1 : idx)}
              >
                <strong>
                  {plainText(day.title)}
                  {day.date ? ` · ${day.date}` : ''}
                </strong>
                <span>{openDay === idx ? '▾' : '▸'}</span>
              </button>
              {openDay === idx && (
                <div className="day-body">
                  {(day.slots || []).length > 0 ? (
                    <div className="slot-list">
                      {day.slots.map((slot) => {
                        const agg = data.votes?.[slot.slot_key]
                        const mine = myVote(slot.slot_key)
                        return (
                          <div
                            key={slot.slot_key}
                            className={`slot-card ${mine ? `voted-${mine}` : ''}`}
                          >
                            <div className="row">
                              <strong>
                                {slot.start}–{slot.end}
                              </strong>
                              <span>{plainText(slot.place)}</span>
                            </div>
                            {slot.body && <Markdown>{slot.body}</Markdown>}
                            {slot.transfer && (
                              <p className="muted small">
                                <FeasibilityBadge value={slot.transfer.feasibility} />
                              </p>
                            )}
                            <p className="muted small">
                              👍 {agg?.want || 0} · 👎 {agg?.skip || 0}
                              {mine ? ` · ваш голос: ${mine === 'want' ? 'хочу' : 'не хочу'}` : ''}
                            </p>
                            <div className="row gap">
                              <button
                                className={`ghost compact ${mine === 'want' ? 'selected-vote' : ''}`}
                                disabled={busy}
                                onClick={() => vote(day.day_index ?? idx, slot.slot_key, 'want')}
                              >
                                Хочу
                              </button>
                              <button
                                className={`ghost compact ${mine === 'skip' ? 'selected-vote' : ''}`}
                                disabled={busy}
                                onClick={() => vote(day.day_index ?? idx, slot.slot_key, 'skip')}
                              >
                                Не хочу
                              </button>
                            </div>
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
      </section>
    </div>
  )
}
