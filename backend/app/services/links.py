"""Deep links на карты / жильё / билеты (без API-ключей)."""

from __future__ import annotations

from urllib.parse import quote_plus


def place_links(place: str, destination: str) -> dict[str, str]:
    query = f"{place}, {destination}".strip(", ")
    dest = destination.strip() or place
    return {
        "maps": f"https://yandex.ru/maps/?text={quote_plus(query)}",
        "booking": f"https://www.booking.com/searchresults.ru.html?ss={quote_plus(dest)}",
        "tickets": f"https://www.aviasales.ru/search?destination={quote_plus(dest)}",
    }


def destination_links(destination: str) -> dict[str, str]:
    return place_links(destination, destination)
