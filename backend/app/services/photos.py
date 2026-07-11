"""Фото направления через Wikimedia Commons — без API-ключа, с дисковым кэшем."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_COMMONS = "https://commons.wikimedia.org/w/api.php"
_UA = "TravelAgent/1.0 (https://ai-travel-assistant.ru; trip photos)"
_CACHE_PATH = Path(__file__).resolve().parents[2] / ".photos_cache.json"
_lock = threading.Lock()
_memory: dict[str, list[dict]] = {}
_loaded = False

_SKIP_TITLE = re.compile(
    r"(map|plan|flag|coat|logo|icon|diagram|chart|svg|signature|stamp|"
    r"карта|флаг|герб|логотип|схема|диаграмм|иконк)",
    re.I,
)


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
                if isinstance(value, list):
                    _memory[key] = value
    except Exception as exc:
        logger.warning("Photos cache load failed: %s", exc)


def _save_cache() -> None:
    try:
        _CACHE_PATH.write_text(
            json.dumps(_memory, ensure_ascii=False, indent=0),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Photos cache save failed: %s", exc)


def clear_photos_cache() -> None:
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


def _credit_from_meta(meta: dict) -> str:
    artist = (meta.get("Artist") or {}).get("value") or ""
    # strip HTML tags from Artist field
    artist = re.sub(r"<[^>]+>", "", artist).strip()
    license_short = (meta.get("LicenseShortName") or {}).get("value") or ""
    parts = [p for p in (artist, license_short) if p]
    return " · ".join(parts)[:160] if parts else "Wikimedia Commons"


def _fetch_commons(destination: str, limit: int = 10) -> list[dict]:
    query = (destination or "").strip()
    if not query:
        return []
    # Prefer city/landscape photos; Commons search is free-text
    search = f"{query} city OR {query} skyline OR {query}"
    params = {
        "action": "query",
        "format": "json",
        "origin": "*",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": search,
        "gsrlimit": min(24, max(limit * 3, 12)),
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": 1600,
    }
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": _UA}) as client:
            resp = client.get(_COMMONS, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("Commons photos fetch failed for %r: %s", query, exc)
        return []

    pages = (payload.get("query") or {}).get("pages") or {}
    photos: list[dict] = []
    for page in pages.values():
        title = page.get("title") or ""
        if _SKIP_TITLE.search(title):
            continue
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = (info.get("mime") or "").lower()
        if not mime.startswith("image/") or mime in ("image/svg+xml", "image/gif"):
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        width = info.get("thumbwidth") or info.get("width") or 0
        height = info.get("thumbheight") or info.get("height") or 0
        # skip tiny / very tall icons
        if width and height and (width < 400 or height / max(width, 1) > 2.2):
            continue
        meta = info.get("extmetadata") or {}
        photos.append(
            {
                "url": url,
                "full_url": info.get("url") or url,
                "title": title.replace("File:", "").rsplit(".", 1)[0][:120],
                "credit": _credit_from_meta(meta),
                "source": "wikimedia",
            }
        )
        if len(photos) >= limit:
            break
    return photos


def destination_photos(destination: str, limit: int = 8) -> list[dict]:
    """Список фото для направления (кэш на диск)."""
    query = (destination or "").strip()
    if not query:
        return []
    key = _norm(query)
    with _lock:
        _load_cache()
        if key in _memory:
            return list(_memory[key])[:limit]

    photos = _fetch_commons(query, limit=limit)
    with _lock:
        _memory[key] = photos
        _save_cache()
    return list(photos)[:limit]
