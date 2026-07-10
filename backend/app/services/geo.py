"""Геокодинг через Nominatim (OpenStreetMap) — без ключа."""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_last_call = 0.0


def geocode(query: str) -> dict | None:
    """Возвращает {name, lat, lon} или None. Соблюдает ~1 req/sec."""
    global _last_call
    query = (query or "").strip()
    if not query:
        return None
    elapsed = time.time() - _last_call
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    try:
        response = httpx.get(
            _NOMINATIM,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "TravelAgent/1.0 (local MVP)"},
            timeout=20,
        )
        _last_call = time.time()
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        item = data[0]
        return {
            "name": item.get("display_name", query).split(",")[0],
            "label": item.get("display_name", query),
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "query": query,
        }
    except Exception as exc:
        logger.warning("Geocode failed for %r: %s", query, exc)
        return None
