"""Геокодинг через Nominatim (OpenStreetMap) — без ключа, с дисковым кэшем."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_last_call = 0.0
_lock = threading.Lock()
_memory: dict[str, dict | None] = {}
_CACHE_PATH = Path(__file__).resolve().parents[2] / ".geocode_cache.json"
_loaded = False


def _norm(query: str) -> str:
    return " ".join(query.lower().split())


def _load_cache() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    if not _CACHE_PATH.is_file():
        return
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key, value in data.items():
                _memory[key] = value
    except Exception as exc:
        logger.warning("Geocode cache load failed: %s", exc)


def _save_cache() -> None:
    try:
        serializable = {k: v for k, v in _memory.items() if v is not None}
        _CACHE_PATH.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=0),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Geocode cache save failed: %s", exc)


def clear_geocode_cache() -> None:
    """Для тестов."""
    global _loaded
    with _lock:
        _memory.clear()
        _loaded = True
        if _CACHE_PATH.is_file():
            try:
                _CACHE_PATH.unlink()
            except OSError:
                pass


def geocode(query: str) -> dict | None:
    """Возвращает {name, lat, lon} или None. Кэш + ~1 req/sec на miss."""
    global _last_call
    query = (query or "").strip()
    if not query:
        return None
    key = _norm(query)
    with _lock:
        _load_cache()
        if key in _memory:
            return dict(_memory[key]) if _memory[key] else None

    with _lock:
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
                hit = None
            else:
                item = data[0]
                hit = {
                    "name": item.get("display_name", query).split(",")[0],
                    "label": item.get("display_name", query),
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "query": query,
                }
            _memory[key] = hit
            _save_cache()
            return dict(hit) if hit else None
        except Exception as exc:
            logger.warning("Geocode failed for %r: %s", query, exc)
            return None
