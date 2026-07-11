function LinkGroup({ title, items }) {
  if (!items?.length) return null
  return (
    <div className="link-group">
      <span className="link-group-label">{title}</span>
      <div className="link-group-btns">
        {items.map((item) => (
          <a
            key={item.id}
            className="ghost compact link-chip"
            href={item.url}
            target="_blank"
            rel="noreferrer"
          >
            {item.label}
          </a>
        ))}
      </div>
    </div>
  )
}

function normalizeStay(links) {
  if (Array.isArray(links.stay) && links.stay.length) return links.stay
  if (links.booking) return [{ id: 'booking', label: 'Booking', url: links.booking }]
  return []
}

function normalizeTickets(links) {
  if (Array.isArray(links.tickets) && links.tickets.length && typeof links.tickets[0] === 'object') {
    return links.tickets
  }
  if (links.tickets_url) return [{ id: 'aviasales', label: 'Aviasales', url: links.tickets_url }]
  if (typeof links.tickets === 'string' && links.tickets) {
    return [{ id: 'tickets', label: 'Билеты', url: links.tickets }]
  }
  return []
}

/** Есть ли жильё/билеты (не только карта) — для скрытия пустой секции. */
export function hasBookingOffers(links) {
  if (!links) return false
  return normalizeStay(links).length > 0 || normalizeTickets(links).length > 0
}

export default function LinkButtons({ links, compact = false }) {
  if (!links) return null

  const stay = normalizeStay(links)
  const tickets = normalizeTickets(links)
  if (!stay.length && !tickets.length && !links.maps) return null

  return (
    <div className={`link-panel ${compact ? 'compact' : ''}`}>
      {links.maps && (
        <a className="ghost compact link-chip" href={links.maps} target="_blank" rel="noreferrer">
          Яндекс.Карты
        </a>
      )}
      <LinkGroup title="Жильё" items={stay} />
      <LinkGroup title="Билеты" items={tickets} />
    </div>
  )
}

export function FeasibilityBadge({ value }) {
  if (!value || value === 'unknown') return null
  const label =
    value === 'feasible' ? 'Успеете' : value === 'tight' ? 'Впритык' : 'Не успеете пешком'
  return <span className={`feasibility ${value}`}>{label}</span>
}
