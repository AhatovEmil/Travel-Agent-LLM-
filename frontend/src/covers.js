const COVERS = {
  sea: '/images/dest-sea.jpg',
  city: '/images/dest-city.jpg',
  nature: '/images/dest-nature.jpg',
  default: '/images/dash-horizon.jpg',
}

const SEA = [
  'море',
  'пляж',
  'beach',
  'sea',
  'ocean',
  'батуми',
  'сочи',
  'крым',
  'ялта',
  'анапа',
  'геленджик',
  'балти',
  'рига',
  'барселон',
  'мальдив',
  'пхукет',
  'бали',
  'санторин',
  'ницца',
  'дубровник',
  'сплит',
  'одесс',
  'лимассол',
  'айя-нап',
  'тенериф',
  'канары',
  'остров',
]

const CITY = [
  'париж',
  'paris',
  'рим',
  'rome',
  'лондон',
  'london',
  'берлин',
  'berlin',
  'праг',
  'prague',
  'вен',
  'vienna',
  'москв',
  'moscow',
  'петербург',
  'питер',
  'istanbul',
  'стамбул',
  'токио',
  'tokyo',
  'нью-йорк',
  'new york',
  'милан',
  'барселон',
  'мадрид',
  'амстердам',
  'музей',
  'город',
  'столиц',
  'шоппинг',
  'nightlife',
  'ночн',
]

const NATURE = [
  'алтай',
  'горы',
  'mountain',
  'nature',
  'природ',
  'трек',
  'hiking',
  'лес',
  'озеро',
  'lake',
  'кавказ',
  'байкал',
  'камчат',
  'норвег',
  'исланд',
  'швейцар',
  'тибет',
  'непал',
  'патрит',
  'карпат',
  'хибин',
  'эльбрус',
  'национальн',
  'парк',
  'йосемит',
]

function score(text, words) {
  let n = 0
  for (const w of words) {
    if (text.includes(w)) n += 1
  }
  return n
}

/** Pick cover image from trip name / brief / destination text. */
export function coverForText(...parts) {
  const text = parts.filter(Boolean).join(' ').toLowerCase()
  if (!text.trim()) return COVERS.default

  const sea = score(text, SEA)
  const city = score(text, CITY)
  const nature = score(text, NATURE)

  // Barcelona matches both sea and city — prefer sea if beachy words, else city
  if (sea >= city && sea >= nature && sea > 0) return COVERS.sea
  if (nature > city && nature > 0) return COVERS.nature
  if (city > 0) return COVERS.city
  if (nature > 0) return COVERS.nature
  return COVERS.default
}

export function coverForTrip(trip) {
  if (!trip) return COVERS.default
  return coverForText(trip.name, trip.brief, trip.destination)
}

export { COVERS }
