import { useEffect, useState } from 'react'
import { api } from './api.js'

const cache = new Map()

/** Карточка настроения с реальным фото города (Wikimedia). */
export default function MoodCard({ label, place, fallback, onPick }) {
  const [src, setSrc] = useState(() => cache.get(place) || fallback)
  const [loaded, setLoaded] = useState(Boolean(cache.get(place)))

  useEffect(() => {
    let cancelled = false
    if (cache.has(place)) {
      setSrc(cache.get(place))
      setLoaded(true)
      return undefined
    }
    ;(async () => {
      try {
        const res = await api.lookupPhotos(place)
        const url = res.photos?.[0]?.url
        if (url && !cancelled) {
          cache.set(place, url)
          setSrc(url)
        }
      } catch {
        /* fallback остаётся */
      } finally {
        if (!cancelled) setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [place])

  return (
    <button type="button" className={`mood-card ${loaded ? 'ready' : 'loading'}`} onClick={onPick}>
      <img src={src} alt="" />
      <span className="mood-meta">
        <strong>{label}</strong>
        <em>{place}</em>
      </span>
    </button>
  )
}
