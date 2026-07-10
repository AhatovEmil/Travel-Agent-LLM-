"""Дни, слоты, карта, погода, deep links и успеваемость."""

from __future__ import annotations

import math
from datetime import date as date_cls
from datetime import datetime

from ..models import Trip
from .geo import geocode
from .links import destination_links, place_links
from .parse import (
    extract_days_count,
    extract_destination,
    extract_place_queries,
    extract_start_date,
    minutes_between,
    parse_itinerary_days,
)
from .weather import fetch_weather

WALK_KMH = 4.5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _feasibility(gap_min: int | None, walk_min: float | None) -> str:
    if gap_min is None or walk_min is None:
        return "unknown"
    if walk_min <= gap_min and walk_min <= 45:
        return "feasible"
    if walk_min <= gap_min + 15 or walk_min <= 90:
        return "tight"
    return "impossible"


def build_trip_extras(trip: Trip, geocode_limit: int = 5) -> dict:
    arts = {a.phase: a.content for a in trip.artifacts}
    destination = extract_destination(trip.brief, trip.name)
    days_count = extract_days_count(trip.brief)
    start = trip.start_date or extract_start_date(trip.brief)
    itinerary = arts.get("itinerary", "")
    days = parse_itinerary_days(itinerary, start_date=start)
    link_kwargs = {"checkin": start, "nights": days_count}

    place_cache: dict[str, dict | None] = {}

    def resolve(place: str) -> dict | None:
        key = place.lower().strip()
        if key in place_cache:
            return place_cache[key]
        hit = geocode(f"{place}, {destination}") if place else None
        place_cache[key] = hit
        return hit

    for day in days:
        for slot in day.get("slots") or []:
            if len(place_cache) >= geocode_limit + 3:
                break
            resolve(slot["place"])

    for query in extract_place_queries(itinerary, destination, limit=geocode_limit):
        if query.lower() not in place_cache:
            place_cache[query.lower()] = geocode(query)

    places: list[dict] = []
    seen_coords: set[tuple[float, float]] = set()
    for hit in place_cache.values():
        if not hit:
            continue
        coord = (round(hit["lat"], 4), round(hit["lon"], 4))
        if coord in seen_coords:
            continue
        seen_coords.add(coord)
        item = {
            **hit,
            "links": place_links(
                hit.get("name") or hit.get("query", ""), destination, **link_kwargs
            ),
        }
        places.append(item)

    center = places[0] if places else geocode(destination)
    if center and "links" not in center:
        center = {**center, "links": destination_links(destination, **link_kwargs)}

    weather: list[dict] = []
    if center:
        weather = fetch_weather(center["lat"], center["lon"], days_count, start=start)
    weather_by_date = {w["date"]: w for w in weather}

    for day in days:
        day["weather"] = weather_by_date.get(day.get("date") or "")
        day["links"] = destination_links(destination, **link_kwargs)
        slots = day.get("slots") or []
        enriched = []
        for i, slot in enumerate(slots):
            geo = resolve(slot["place"])
            item = {
                **slot,
                "links": place_links(slot["place"], destination, **link_kwargs),
                "lat": geo["lat"] if geo else None,
                "lon": geo["lon"] if geo else None,
            }
            if i + 1 < len(slots):
                nxt = slots[i + 1]
                gap = minutes_between(slot["end"], nxt["start"])
                nxt_geo = resolve(nxt["place"])
                walk_min = None
                dist_km = None
                if geo and nxt_geo:
                    dist_km = round(
                        haversine_km(geo["lat"], geo["lon"], nxt_geo["lat"], nxt_geo["lon"]),
                        2,
                    )
                    walk_min = round(dist_km / WALK_KMH * 60)
                item["transfer"] = {
                    "to": nxt["place"],
                    "gap_min": gap,
                    "distance_km": dist_km,
                    "walk_min": walk_min,
                    "feasibility": _feasibility(
                        gap, float(walk_min) if walk_min is not None else None
                    ),
                }
            enriched.append(item)
        day["slots"] = enriched

    return {
        "destination": destination,
        "days_count": days_count,
        "start_date": start.isoformat() if start else None,
        "days": days,
        "center": center,
        "places": places,
        "weather": weather,
        "links": destination_links(destination, **link_kwargs),
    }


def build_live_status(trip: Trip, lat: float | None, lon: float | None) -> dict:
    extras = build_trip_extras(trip, geocode_limit=4)
    today = date_cls.today().isoformat()
    days = extras["days"]
    day = next((d for d in days if d.get("date") == today), None)
    mode = "active"
    notice = ""

    if day is None:
        if not days:
            mode = "empty"
            notice = "План ещё пуст — сначала сгенерируйте поездку."
        else:
            dates = [d.get("date") for d in days if d.get("date")]
            if dates and today < min(dates):
                mode = "preview"
                day = days[0]
                notice = (
                    f"Демо: показываем день 1. Поездка начинается {min(dates)}."
                )
            elif dates and today > max(dates):
                mode = "ended"
                day = days[-1]
                notice = f"Поездка уже закончилась ({max(dates)}). Показан последний день."
            else:
                mode = "off_plan"
                day = days[0]
                notice = "Сегодня нет в плане. Показан ближайший день для ориентира."

    now = datetime.now().strftime("%H:%M")
    slots = (day or {}).get("slots") or []
    current = None
    nxt = None
    if mode == "active":
        for slot in slots:
            if slot["start"] <= now <= slot["end"]:
                current = slot
            elif slot["start"] > now and nxt is None:
                nxt = slot
        if current is None and nxt is None and slots:
            nxt = slots[0]
    elif slots:
        nxt = slots[0]

    distance_to_next = None
    if lat is not None and lon is not None and nxt and nxt.get("lat") is not None:
        distance_to_next = round(haversine_km(lat, lon, nxt["lat"], nxt["lon"]), 2)

    return {
        "now": now,
        "today": today,
        "mode": mode,
        "notice": notice,
        "day": day,
        "current_slot": current,
        "next_slot": nxt,
        "distance_km_to_next": distance_to_next,
        "weather": (day or {}).get("weather"),
        "destination": extras["destination"],
        "can_adjust": mode in ("active", "preview", "off_plan", "ended") and bool(day),
    }
