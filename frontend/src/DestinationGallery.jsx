import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Галерея реальных фото направления (свайп / стрелки).
 * fallbackSrc — статичная обложка, пока грузятся или если фото нет.
 */
export default function DestinationGallery({
  photos = [],
  loading = false,
  fallbackSrc,
  destination = '',
  title,
  meta,
}) {
  const [index, setIndex] = useState(0)
  const touchX = useRef(null)
  const list = photos.length > 0 ? photos : fallbackSrc ? [{ url: fallbackSrc, credit: '' }] : []
  const safeIndex = list.length ? Math.min(index, list.length - 1) : 0
  const current = list[safeIndex]

  useEffect(() => {
    setIndex(0)
  }, [photos])

  const go = useCallback(
    (delta) => {
      if (list.length < 2) return
      setIndex((i) => (i + delta + list.length) % list.length)
    },
    [list.length],
  )

  useEffect(() => {
    if (list.length < 2) return undefined
    const onKey = (e) => {
      if (e.key === 'ArrowLeft') go(-1)
      if (e.key === 'ArrowRight') go(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [go, list.length])

  const onTouchStart = (e) => {
    touchX.current = e.changedTouches[0]?.clientX ?? null
  }

  const onTouchEnd = (e) => {
    if (touchX.current == null || list.length < 2) return
    const x = e.changedTouches[0]?.clientX
    if (x == null) return
    const dx = x - touchX.current
    touchX.current = null
    if (Math.abs(dx) < 40) return
    go(dx < 0 ? 1 : -1)
  }

  if (!current) return null

  return (
    <div
      className={`trip-cover dest-gallery ${loading ? 'loading' : ''}`}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <img
        key={current.url}
        src={current.url}
        alt={destination ? `Фото: ${destination}` : ''}
        className="dest-gallery-img"
      />
      <div className="trip-cover-veil" />
      <div className="trip-cover-copy">
        <p className="hero-kicker">Поездка</p>
        {title && <h1>{title}</h1>}
        {meta && <p className="trip-cover-meta">{meta}</p>}
      </div>

      {list.length > 1 && (
        <>
          <button
            type="button"
            className="dest-gallery-nav prev"
            aria-label="Предыдущее фото"
            onClick={() => go(-1)}
          >
            ‹
          </button>
          <button
            type="button"
            className="dest-gallery-nav next"
            aria-label="Следующее фото"
            onClick={() => go(1)}
          >
            ›
          </button>
          <div className="dest-gallery-pager" aria-label="Фото города">
            <span className="dest-gallery-count" aria-hidden="true">
              {safeIndex + 1}
              <em>/</em>
              {list.length}
            </span>
            <div className="dest-gallery-dots" role="tablist">
              {list.map((p, i) => (
                <button
                  key={p.url + i}
                  type="button"
                  role="tab"
                  aria-label={`Фото ${i + 1} из ${list.length}`}
                  aria-selected={i === safeIndex}
                  className={`dest-gallery-dot ${i === safeIndex ? 'active' : ''}`}
                  onClick={() => setIndex(i)}
                />
              ))}
            </div>
          </div>
        </>
      )}

      <div className="dest-gallery-credit">
        {loading && photos.length === 0 ? (
          <span>Ищем фото города…</span>
        ) : current.credit ? (
          <span>
            {destination ? `${destination} · ` : ''}
            {current.credit}
          </span>
        ) : photos.length > 1 ? (
          <span>
            {safeIndex + 1} / {list.length}
            {destination ? ` · ${destination}` : ''}
          </span>
        ) : null}
      </div>
    </div>
  )
}
