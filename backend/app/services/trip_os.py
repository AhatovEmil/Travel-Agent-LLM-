"""Утренний брифинг и хелперы режима «на месте»."""

from __future__ import annotations

import json
from datetime import date as date_cls
from datetime import timedelta

from .extras import extract_days_count, extract_destination, extract_start_date
from .parse import parse_itinerary_days
from .street_smart import build_quest_fallback, build_survival


MOODS = ("great", "ok", "tired", "wow", "meh")


def _arts(trip) -> dict[str, str]:
    return {a.phase: a.content for a in (trip.artifacts or [])}


def _trip_days(trip) -> list[dict]:
    arts = _arts(trip)
    start = trip.start_date or extract_start_date(trip.brief or "")
    return parse_itinerary_days(arts.get("itinerary", "") or "", start_date=start)


def trip_day_window(trip) -> dict:
    """Which calendar day of the trip is 'today' relative to start_date."""
    days = _trip_days(trip)
    today = date_cls.today()
    start = trip.start_date or extract_start_date(trip.brief or "")
    if start is None and days:
        raw = days[0].get("date")
        try:
            start = date_cls.fromisoformat(raw) if raw else None
        except ValueError:
            start = None

    days_count = len(days) or extract_days_count(trip.brief or "") or 1
    end = start + timedelta(days=max(days_count - 1, 0)) if start is not None else None

    phase = "plan"
    day_index = 0
    if start and end:
        if today < start:
            phase = "plan"
            day_index = 0
        elif today > end:
            phase = "memories"
            day_index = max(len(days) - 1, 0) if days else max(days_count - 1, 0)
        else:
            phase = "onsite"
            day_index = (today - start).days
            if days and day_index >= len(days):
                day_index = len(days) - 1
            elif not days and day_index >= days_count:
                day_index = days_count - 1

    return {
        "phase": phase,
        "today": today.isoformat(),
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "day_index": max(day_index, 0),
        "days_count": days_count,
        "destination": extract_destination(trip.brief or "", trip.name or ""),
        "days": days,
    }


def build_morning_briefing(trip, day_index: int | None = None) -> dict:
    window = trip_day_window(trip)
    days = window.get("days") or []
    idx = window["day_index"] if day_index is None else day_index
    if idx < 0:
        idx = 0
    if days and idx >= len(days):
        idx = len(days) - 1

    day = days[idx] if days else None
    survival = build_survival(trip)
    quest = build_quest_fallback(trip, idx)
    tip = survival["tips"][idx % len(survival["tips"])] if survival.get("tips") else ""
    phrase = survival["phrases"][0] if survival.get("phrases") else None

    slots = (day or {}).get("slots") or []
    return {
        "mode_hint": window["phase"],
        "today": window["today"],
        "day_index": idx,
        "day_title": (day or {}).get("title") or f"День {idx + 1}",
        "day_date": (day or {}).get("date"),
        "weather": (day or {}).get("weather"),
        "slots_preview": [
            {
                "start": s.get("start"),
                "end": s.get("end"),
                "place": s.get("place"),
                "slot_key": s.get("slot_key"),
            }
            for s in slots[:4]
        ],
        "slots_total": len(slots),
        "tip": tip,
        "phrase": phrase,
        "quest_teaser": (quest.get("missions") or [{}])[0].get("text", ""),
        "destination": window.get("destination") or survival.get("destination"),
        "emergency": (survival.get("emergency") or [{}])[0],
    }


def serialize_done_slots(keys: list[str]) -> str:
    return json.dumps([str(k) for k in keys if k], ensure_ascii=False)


def parse_done_slots(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        if isinstance(data, list):
            return [str(x) for x in data]
    except json.JSONDecodeError:
        pass
    return []
