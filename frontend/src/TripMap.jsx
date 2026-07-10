import { useEffect, useRef } from 'react'

export default function TripMap({ center, places }) {
  const ref = useRef(null)
  const mapRef = useRef(null)

  useEffect(() => {
    const L = window.L
    if (!L || !ref.current || !center) return

    if (mapRef.current) {
      mapRef.current.remove()
      mapRef.current = null
    }

    const map = L.map(ref.current).setView([center.lat, center.lon], 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 18,
    }).addTo(map)

    const markers = places?.length ? places : [center]
    const bounds = []
    markers.forEach((p) => {
      const marker = L.marker([p.lat, p.lon]).addTo(map)
      marker.bindPopup(p.name || p.label || p.query || 'Место')
      bounds.push([p.lat, p.lon])
    })
    if (bounds.length > 1) map.fitBounds(bounds, { padding: [28, 28] })

    mapRef.current = map
    setTimeout(() => map.invalidateSize(), 80)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [center, places])

  if (!center) {
    return <p className="muted">Карта появится, когда найдём координаты направления.</p>
  }

  return <div className="trip-map" ref={ref} />
}
