"""Проверка мест itinerary через геокодинг (Nominatim) — отсев выдуманных точек."""

from __future__ import annotations

import logging
import re
from typing import Any

from .geo import geocode
from .parse import extract_destination, parse_itinerary_days

logger = logging.getLogger(__name__)

# Мягкие формулировки — не требуют точного POI на карте
_SOFT_START = re.compile(
    r"^(кафе|ресторан|кофейн|столов|парк\b|набереж|пляж|рынок|базар|"
    r"прогулк|обед|ужин|завтрак|отель|жиль|"
    r"трансфер|аэропорт|вокзал|автовокзал|"
    r"местн|локальн|свободн|уютн)",
    re.I,
)
_SOFT_ONLY = re.compile(
    r"^(центр( города)?|набережная|пляж|рынок|парк|сквер|площадь|"
    r"бульвар|музей|галерея)$",
    re.I,
)
_MARK = "· уточнить на месте"


def is_soft_place(place: str) -> bool:
    """Общие формулировки без конкретного имени — ок без геокода."""
    p = (place or "").strip()
    if len(p) < 3:
        return True
    low = p.lower()
    if _MARK in low or "уточнить" in low:
        return True
    if _SOFT_ONLY.match(p):
        return True
    if _SOFT_START.match(p) and len(p) <= 56:
        return True
    return False


def _queries(place: str, destination: str) -> list[str]:
    place = place.strip()
    dest = (destination or "").strip()
    out: list[str] = []
    if dest:
        out.append(f"{place}, {dest}")
        out.append(f"{place} {dest}")
    out.append(place)
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for q in out:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(q)
    return uniq


def check_place(place: str, destination: str) -> dict[str, Any]:
    """Проверяет одно место. ok=True если soft или найден геокод."""
    place = (place or "").strip()
    if not place:
        return {"ok": True, "soft": True, "place": place, "hit": None}
    if is_soft_place(place):
        return {"ok": True, "soft": True, "place": place, "hit": None}
    for q in _queries(place, destination):
        hit = geocode(q)
        if hit:
            return {"ok": True, "soft": False, "place": place, "hit": hit, "query": q}
    return {"ok": False, "soft": False, "place": place, "hit": None}


def collect_slot_places(itinerary: str, destination: str = "") -> list[dict]:
    days = parse_itinerary_days(itinerary)
    rows: list[dict] = []
    for day in days:
        for slot in day.get("slots") or []:
            rows.append(
                {
                    "day_index": day.get("day_index", 0),
                    "day_title": day.get("title", ""),
                    "start": slot.get("start"),
                    "end": slot.get("end"),
                    "place": slot.get("place", ""),
                    "slot_key": slot.get("slot_key"),
                }
            )
    return rows


def verify_itinerary_places(
    itinerary: str,
    destination: str = "",
) -> dict[str, Any]:
    """
    Геопроверка всех слотов.
    Возвращает {destination, checked, unverified: [...], verified_count, soft_count}.
    """
    dest = (destination or "").strip() or extract_destination(itinerary, "")
    slots = collect_slot_places(itinerary, dest)
    unverified: list[dict] = []
    verified = 0
    soft = 0
    # дедуп по месту — один геокод на уникальное название
    cache_ok: dict[str, dict] = {}
    for row in slots:
        place = row["place"]
        key = place.lower()
        if key in cache_ok:
            result = cache_ok[key]
        else:
            result = check_place(place, dest)
            cache_ok[key] = result
        if result.get("soft"):
            soft += 1
        elif result.get("ok"):
            verified += 1
        else:
            unverified.append({**row, **result})
    return {
        "destination": dest,
        "checked": len(slots),
        "verified_count": verified,
        "soft_count": soft,
        "unverified": unverified,
        "unverified_places": sorted({u["place"] for u in unverified}),
    }


def mark_unverified_in_text(itinerary: str, bad_places: list[str]) -> str:
    """Помечает неподтверждённые места в заголовках слотов."""
    text = itinerary
    for place in sorted({p.strip() for p in bad_places if p.strip()}, key=len, reverse=True):
        if _MARK in place:
            continue
        # только в строках слотов ### HH:MM–HH:MM — Place
        pattern = re.compile(
            r"(###\s*\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\s*[—–-]\s*)"
            + re.escape(place)
            + r"(?=\s*$)",
            re.MULTILINE,
        )
        text = pattern.sub(rf"\1{place} {_MARK}", text)
    return text


def harden_itinerary(
    itinerary: str,
    destination: str,
    *,
    fix_fn=None,
) -> tuple[str, dict[str, Any]]:
    """
    Полный цикл: проверить → (опционально) LLM-замена → снова проверить → пометить остаток.
    fix_fn(itinerary, destination, bad_places) -> str | None
    """
    report = verify_itinerary_places(itinerary, destination)
    text = itinerary
    if report["unverified_places"] and fix_fn is not None:
        try:
            fixed = fix_fn(text, report["destination"], report["unverified_places"])
            if fixed and fixed.strip():
                text = fixed.strip()
                report = verify_itinerary_places(text, destination)
                report["llm_fix_applied"] = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM place fix failed: %s", exc)
            report["llm_fix_error"] = str(exc)

    if report["unverified_places"]:
        text = mark_unverified_in_text(text, report["unverified_places"])
        report["marked"] = True
        # после пометки soft/marked — пересчёт для отчёта
        report = {
            **verify_itinerary_places(text, destination),
            "marked": True,
            "originally_unverified": report["unverified_places"],
            "llm_fix_applied": report.get("llm_fix_applied", False),
        }
    else:
        report["marked"] = False
        report["llm_fix_applied"] = report.get("llm_fix_applied", False)

    logger.info(
        "Place verify %s: checked=%s verified=%s soft=%s left=%s marked=%s",
        report.get("destination"),
        report.get("checked"),
        report.get("verified_count"),
        report.get("soft_count"),
        len(report.get("unverified_places") or []),
        report.get("marked"),
    )
    return text, report
