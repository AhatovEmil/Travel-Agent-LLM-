"""Ссылки на карты / жильё / билеты — главные страницы сервисов."""

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote_plus


def _stay_dates(
    checkin: date | None, nights: int
) -> tuple[date, date]:
    start = checkin or (date.today() + timedelta(days=7))
    nights = max(1, min(int(nights or 5), 30))
    return start, start + timedelta(days=nights)


def place_links(
    place: str,
    destination: str,
    *,
    checkin: date | None = None,
    nights: int = 5,
) -> dict:
    dest = (destination.strip() or place).strip() or "путешествие"
    place_name = (place or dest).strip()
    map_q = f"{place_name}, {dest}".strip(", ") if place_name != dest else dest

    start, end = _stay_dates(checkin, nights)
    checkin_iso, checkout_iso = start.isoformat(), end.isoformat()
    nights_n = (end - start).days

    stay = [
        {
            "id": "booking",
            "label": "Booking",
            "url": "https://www.booking.com/",
        },
        {
            "id": "ostrovok",
            "label": "Островок",
            "url": "https://ostrovok.ru/",
        },
        {
            "id": "yandex_hotels",
            "label": "Я.Путешествия",
            "url": "https://travel.yandex.ru/hotels/",
        },
        {
            "id": "sutochno",
            "label": "Суточно.ру",
            "url": "https://sutochno.ru/",
        },
    ]
    tickets = [
        {
            "id": "aviasales",
            "label": "Aviasales",
            "url": "https://www.aviasales.ru/",
        },
        {
            "id": "yandex_avia",
            "label": "Я.Авиа",
            "url": "https://travel.yandex.ru/avia/",
        },
        {
            "id": "yandex_trains",
            "label": "Я.Поезда",
            "url": "https://travel.yandex.ru/trains/",
        },
        {
            "id": "tutu",
            "label": "Туту.ру",
            "url": "https://www.tutu.ru/",
        },
    ]
    return {
        "maps": f"https://yandex.ru/maps/?text={quote_plus(map_q)}",
        "stay": stay,
        "tickets": tickets,
        "booking": stay[0]["url"],
        "tickets_url": tickets[0]["url"],
        "checkin": checkin_iso,
        "checkout": checkout_iso,
        "nights": nights_n,
        "destination": dest,
    }


def destination_links(
    destination: str,
    *,
    checkin: date | None = None,
    nights: int = 5,
) -> dict:
    return place_links(destination, destination, checkin=checkin, nights=nights)
