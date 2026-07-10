export default function LinkButtons({ links, compact = false }) {
  if (!links) return null
  return (
    <div className={`link-btns ${compact ? 'compact' : ''}`}>
      {links.maps && (
        <a className="ghost compact" href={links.maps} target="_blank" rel="noreferrer">
          Карта
        </a>
      )}
      {links.booking && (
        <a className="ghost compact" href={links.booking} target="_blank" rel="noreferrer">
          Жильё
        </a>
      )}
      {links.tickets && (
        <a className="ghost compact" href={links.tickets} target="_blank" rel="noreferrer">
          Билеты
        </a>
      )}
    </div>
  )
}

export function FeasibilityBadge({ value }) {
  if (!value || value === 'unknown') return null
  const label =
    value === 'feasible' ? 'Успеете' : value === 'tight' ? 'Впритык' : 'Не успеете пешком'
  return <span className={`feasibility ${value}`}>{label}</span>
}
