import { useEffect, useRef } from 'react'

function numberedIcon(L, n) {
  return L.divIcon({
    className: 'map-slot-marker',
    html: `<span>${n}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -12],
  })
}

/**
 * @param {{ lat: number, lon: number }} center
 * @param {Array} places - fallback markers
 * @param {Array<{lat, lon, place?, start?, end?}>} route - ordered day slots with coords
 */
export default function TripMap({ center, places, route }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const routeKey = (route || [])
    .map((p) => `${p.lat},${p.lon},${p.place || p.name || ''}`)
    .join('|')
  const placesKey = (places || []).map((p) => `${p.lat},${p.lon}`).join('|')

  useEffect(() => {
    const L = window.L
    if (!L || !ref.current || !center) return

    if (mapRef.current) {
      mapRef.current.remove()
      mapRef.current = null
    }

    const map = L.map(ref.current, { scrollWheelZoom: false }).setView(
      [center.lat, center.lon],
      12,
    )
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 18,
    }).addTo(map)

    const bounds = []
    const path = (route || []).filter((p) => p.lat != null && p.lon != null)

    if (path.length > 0) {
      const latlngs = path.map((p) => [p.lat, p.lon])
      L.polyline(latlngs, {
        color: '#0d7a7a',
        weight: 4,
        opacity: 0.75,
        lineJoin: 'round',
      }).addTo(map)

      path.forEach((p, i) => {
        const marker = L.marker([p.lat, p.lon], { icon: numberedIcon(L, i + 1) }).addTo(map)
        const time = p.start && p.end ? `${p.start}–${p.end}` : ''
        const title = p.place || p.name || p.label || `Точка ${i + 1}`
        marker.bindPopup(time ? `<strong>${time}</strong><br/>${title}` : title)
        bounds.push([p.lat, p.lon])
      })
    } else {
      const markers = places?.length ? places : [center]
      markers.forEach((p) => {
        if (p.lat == null || p.lon == null) return
        const marker = L.marker([p.lat, p.lon]).addTo(map)
        marker.bindPopup(p.name || p.label || p.query || 'Место')
        bounds.push([p.lat, p.lon])
      })
    }

    if (bounds.length > 1) map.fitBounds(bounds, { padding: [36, 36] })
    else if (bounds.length === 1) map.setView(bounds[0], 14)

    mapRef.current = map
    setTimeout(() => map.invalidateSize(), 80)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [center?.lat, center?.lon, routeKey, placesKey])

  if (!center) {
    return <p className="muted">Карта появится, когда найдём координаты направления.</p>
  }

  return <div className="trip-map" ref={ref} />
}
