"""Дни, точки на карте и погода для страницы поездки."""

from __future__ import annotations

from ..models import Trip
from .geo import geocode
from .parse import (
    extract_days_count,
    extract_destination,
    extract_place_queries,
    parse_itinerary_days,
)
from .weather import fetch_weather


def build_trip_extras(trip: Trip) -> dict:
    arts = {a.phase: a.content for a in trip.artifacts}
    destination = extract_destination(trip.brief, trip.name)
    days_count = extract_days_count(trip.brief)
    itinerary = arts.get("itinerary", "")
    days = parse_itinerary_days(itinerary)

    places: list[dict] = []
    for query in extract_place_queries(itinerary, destination, limit=5):
        hit = geocode(query)
        if hit:
            places.append(hit)

    center = places[0] if places else geocode(destination)
    weather: list[dict] = []
    if center:
        weather = fetch_weather(center["lat"], center["lon"], days_count)

    return {
        "destination": destination,
        "days_count": days_count,
        "days": days,
        "center": center,
        "places": places,
        "weather": weather,
    }
