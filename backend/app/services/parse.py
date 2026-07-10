"""Парсинг brief / itinerary для карточек дней, карты и погоды."""

from __future__ import annotations

import re


def extract_destination(brief: str, name: str = "") -> str:
    match = re.search(r"Направление:\s*([^.\n]+)", brief, re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(".")
    # «Батуми, 5 дн.» из авто-имени
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


def parse_itinerary_days(content: str) -> list[dict[str, str]]:
    """Режет itinerary на карточки по заголовкам «День N»."""
    if not content.strip():
        return []
    pattern = re.compile(
        r"^##\s*(День\s*\d+[^\n]*)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(content))
    if not matches:
        # запасной вариант: ### День
        pattern = re.compile(
            r"^###\s*(День\s*\d+[^\n]*)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        matches = list(pattern.finditer(content))
    if not matches:
        return [{"title": "План", "content": content.strip()}]

    days: list[dict[str, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        # обрезаем блок «запасной план», если он после дней
        if re.search(r"^##\s*Запасн", body, re.IGNORECASE | re.MULTILINE):
            body = re.split(r"^##\s*Запасн", body, maxsplit=1, flags=re.IGNORECASE | re.MULTILINE)[0].strip()
        days.append({"title": match.group(1).strip(), "content": body})
    return days


def extract_place_queries(itinerary: str, destination: str, limit: int = 6) -> list[str]:
    """Грубые кандидаты мест для геокодинга (без LLM)."""
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
    # **Место** или строки вида «— Название»
    for match in re.finditer(r"\*\*([^*]{3,60})\*\*", itinerary):
        add(f"{match.group(1)}, {destination}")
    for match in re.finditer(r"[—–-]\s*([А-ЯA-Z][^.\n,]{2,50})", itinerary):
        add(f"{match.group(1).strip()}, {destination}")
    return queries[:limit]
