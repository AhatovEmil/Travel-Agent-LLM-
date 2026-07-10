import { useEffect, useRef, useState } from 'react'
import Markdown from './Markdown.jsx'
import { api } from './api.js'

export default function AskChat({ tripId, disabled }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    api
      .getMessages(tripId)
      .then((msgs) => {
        if (!cancelled) setMessages(msgs)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [tripId, open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  const send = async (e) => {
    e.preventDefault()
    if (!text.trim() || busy || disabled) return
    setBusy(true)
    setError('')
    const question = text.trim()
    setText('')
    setMessages((prev) => [...prev, { id: `tmp-${Date.now()}`, role: 'user', content: question }])
    try {
      const res = await api.askTrip(tripId, question)
      setMessages(res.messages)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={`chat-fab ${open ? 'open' : ''}`}
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Закрыть чат' : 'Открыть чат'}
      >
        {open ? '×' : '?'}
      </button>

      {open && (
        <div className="ask-chat">
          <div className="ask-chat-header">
            <strong>Спросить про поездку</strong>
            <span className="muted small">уточнения, без переписывания плана</span>
          </div>
          <div className="ask-chat-body">
            {messages.length === 0 && (
              <p className="muted small">
                Например: «сколько roughly на еду в день?» или «нужна ли виза?»
              </p>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`ask-bubble ${m.role}`}>
                {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
              </div>
            ))}
            {busy && <div className="ask-bubble assistant muted">Думаю…</div>}
            <div ref={bottomRef} />
          </div>
          {error && <div className="error ask-chat-error">{error}</div>}
          <form className="ask-chat-form" onSubmit={send}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ваш вопрос…"
              disabled={busy || disabled}
            />
            <button className="primary" type="submit" disabled={busy || disabled || !text.trim()}>
              →
            </button>
          </form>
        </div>
      )}
    </>
  )
}
