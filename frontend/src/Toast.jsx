import { useEffect, useState } from 'react'

let pushToast = null

export function toast(message, tone = 'ok') {
  if (pushToast) pushToast({ id: Date.now() + Math.random(), message, tone })
}

export default function ToastHost() {
  const [items, setItems] = useState([])

  useEffect(() => {
    pushToast = (item) => {
      setItems((prev) => [...prev.slice(-4), item])
      setTimeout(() => {
        setItems((prev) => prev.filter((x) => x.id !== item.id))
      }, 4200)
    }
    return () => {
      pushToast = null
    }
  }, [])

  if (!items.length) return null

  return (
    <div className="toast-host" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={`toast ${item.tone}`}>
          {item.message}
        </div>
      ))}
    </div>
  )
}
