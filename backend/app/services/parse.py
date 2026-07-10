"""Парсинг brief / itinerary для карточек дней, слотов, карты и погоды."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta


def extract_destination(brief: str, name: str = "") -> str:
    match = re.search(r"Направление:\s*([^.\n]+)", brief, re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(".")
    if name:
        return name.split(",")[0].strip()
    first = brief.strip().split("\n")[0]
    return first[:80].strip() or "путешествие"


def extract_days_count(brief: str) -> int:
    match = re.search(r"Длительность:\s*(\d+)\s*дн", brief, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 16))
    match = re.search(r"(\d+)\s*дн", brief, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 16))
    return 5


def extract_start_date(brief: str, fallback: date | None = None) -> date | None:
    match = re.search(r"Дата начала:\s*(\d{4}-\d{2}-\d{2})", brief, re.IGNORECASE)
    if match:
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return fallback


def parse_day_slots(day_body: str) -> list[dict]:
    """Парсит слоты ### HH:MM–HH:MM — Место."""
    if not day_body.strip():
        return []
    pattern = re.compile(
        r"^###\s*(\d{1,2}:\d{2})\s*[–—-]\s*(\d{1,2}:\d{2})\s*[—–-]\s*(.+?)\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(day_body))
    if not matches:
        return []
    slots: list[dict] = []
    for i, match in enumerate(matches):
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(day_body)
        place = re.sub(r"[*_`]", "", match.group(3)).strip()
        start_t = _norm_time(match.group(1))
        end_t = _norm_time(match.group(2))
        slots.append(
            {
                "start": start_t,
                "end": end_t,
                "place": place,
                "body": day_body[start_pos:end_pos].strip(),
                "slot_key": f"{start_t}|{place}"[:160],
            }
        )
    return slots


def _norm_time(value: str) -> str:
    parts = value.split(":")
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"


def parse_itinerary_days(
    content: str, start_date: date | None = None
) -> list[dict]:
    """Режет itinerary на дни; добавляет date и slots."""
    if not content.strip():
        return []
    pattern = re.compile(
        r"^##\s*(День\s*\d+[^\n]*)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(content))
    if not matches:
        pattern = re.compile(
            r"^###\s*(День\s*\d+[^\n]*)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        matches = list(pattern.finditer(content))
    if not matches:
        return [
            {
                "title": "План",
                "content": content.strip(),
                "date": start_date.isoformat() if start_date else None,
                "day_index": 0,
                "slots": parse_day_slots(content),
            }
        ]

    days: list[dict] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if re.search(r"^##\s*Запасн", body, re.IGNORECASE | re.MULTILINE):
            body = re.split(
                r"^##\s*Запасн", body, maxsplit=1, flags=re.IGNORECASE | re.MULTILINE
            )[0].strip()
        title = match.group(1).strip()
        day_date = _date_from_title(title)
        if day_date is None and start_date is not None:
            day_date = start_date + timedelta(days=i)
        days.append(
            {
                "title": title,
                "content": body,
                "date": day_date.isoformat() if day_date else None,
                "day_index": i,
                "slots": parse_day_slots(body),
            }
        )
    return days


def _date_from_title(title: str) -> date | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def minutes_between(start: str, end: str) -> int | None:
    try:
        t0 = datetime.strptime(start, "%H:%M")
        t1 = datetime.strptime(end, "%H:%M")
    except ValueError:
        return None
    delta = int((t1 - t0).total_seconds() // 60)
    if delta < 0:
        delta += 24 * 60
    return delta


def extract_place_queries(itinerary: str, destination: str, limit: int = 6) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = re.sub(r"[*_`#]", "", q).strip(" .-–—,:;")
        if len(q) < 3 or len(q) > 80:
            return
        key = q.lower()
        if key in seen:
            return
        seen.add(key)
        queries.append(q)

    add(destination)
    for match in re.finditer(r"\*\*([^*]{3,60})\*\*", itinerary):
        add(f"{match.group(1)}, {destination}")
    for match in re.finditer(
        r"^###\s*\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\s*[—–-]\s*(.+)$",
        itinerary,
        re.MULTILINE,
    ):
        add(f"{match.group(1).strip()}, {destination}")
    for match in re.finditer(r"[—–-]\s*([А-ЯA-Z][^.\n,]{2,50})", itinerary):
        add(f"{match.group(1).strip()}, {destination}")
    return queries[:limit]


def replace_day_in_itinerary(itinerary: str, day_index: int, new_day_markdown: str) -> str:
    """Подменяет тело одного дня (включая заголовок ## День N)."""
    pattern = re.compile(
        r"^##\s*(День\s*\d+[^\n]*)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(itinerary))
    if not matches or day_index < 0 or day_index >= len(matches):
        return itinerary
    start = matches[day_index].start()
    if day_index + 1 < len(matches):
        end = matches[day_index + 1].start()
    else:
        spare = re.search(r"^##\s*Запасн", itinerary[matches[day_index].end() :], re.I | re.M)
        if spare:
            end = matches[day_index].end() + spare.start()
        else:
            end = len(itinerary)
    block = new_day_markdown.strip() + "\n\n"
    return itinerary[:start] + block + itinerary[end:]
