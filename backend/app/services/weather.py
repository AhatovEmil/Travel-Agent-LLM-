"""Погода через Open-Meteo — без API-ключа."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

# Упрощённые коды Open-Meteo → текст
_WEATHER_LABELS = {
    0: "Ясно",
    1: "В основном ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Туман",
    51: "Морось",
    61: "Дождь",
    63: "Дождь",
    65: "Сильный дождь",
    71: "Снег",
    80: "Ливень",
    95: "Гроза",
}


def _label(code: int) -> str:
    if code in _WEATHER_LABELS:
        return _WEATHER_LABELS[code]
    if code >= 90:
        return "Гроза"
    if code >= 70:
        return "Снег"
    if code >= 60:
        return "Дождь"
    if code >= 50:
        return "Морось"
    return "Облачно"


def fetch_weather(lat: float, lon: float, days: int = 5) -> list[dict]:
    days = max(1, min(int(days), 16))
    start = date.today()
    end = start + timedelta(days=days - 1)
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=20,
        )
        response.raise_for_status()
        daily = response.json().get("daily") or {}
        dates = daily.get("time") or []
        codes = daily.get("weathercode") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        out = []
        for i, d in enumerate(dates):
            code = int(codes[i]) if i < len(codes) else 0
            out.append(
                {
                    "date": d,
                    "temp_max": round(float(tmax[i]), 1) if i < len(tmax) else None,
                    "temp_min": round(float(tmin[i]), 1) if i < len(tmin) else None,
                    "code": code,
                    "label": _label(code),
                }
            )
        return out
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return []
