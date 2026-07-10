"""Deep links на карты / жильё / билеты — сразу в поиск по городу и датам."""

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote_plus, urlencode


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
    # для жилья ищем город; для карты — конкретное место
    hotel_q = dest
    map_q = f"{place_name}, {dest}".strip(", ") if place_name != dest else dest

    start, end = _stay_dates(checkin, nights)
    checkin_iso, checkout_iso = start.isoformat(), end.isoformat()
    checkin_dmy = start.strftime("%d.%m.%Y")
    checkout_dmy = end.strftime("%d.%m.%Y")
    nights_n = (end - start).days

    booking_params = urlencode(
        {
            "ss": hotel_q,
            "ssne": hotel_q,
            "ssne_untouched": hotel_q,
            "lang": "ru",
            "selected_currency": "RUB",
            "checkin": checkin_iso,
            "checkout": checkout_iso,
            "group_adults": 2,
            "no_rooms": 1,
            "group_children": 0,
        },
        quote_via=quote_plus,
    )
    yandex_hotel_params = urlencode(
        {
            "query": hotel_q,
            "adults": 2,
            "checkinDate": checkin_iso,
            "checkoutDate": checkout_iso,
        },
        quote_via=quote_plus,
    )
    sutochno_params = urlencode(
        {
            "query": hotel_q,
            "guests_adults": 2,
            "occupied": f"{checkin_iso};{checkout_iso}",
        },
        quote_via=quote_plus,
    )
    # Островок / ZenHotels — текстовый q + даты DD.MM.YYYY
    ostrovok_params = urlencode(
        {
            "q": hotel_q,
            "dates": f"{checkin_dmy}-{checkout_dmy}",
            "guests": 2,
        },
        quote_via=quote_plus,
    )
    aviasales_params = urlencode(
        {
            "destination_name": dest,
            "depart_date": checkin_iso,
            "return_date": checkout_iso,
            "adults": 1,
            "children": 0,
            "infants": 0,
            "trip_class": 0,
            "currency": "rub",
            "locale": "ru",
            "one_way": "false",
            "with_request": "true",
        },
        quote_via=quote_plus,
    )
    yandex_avia_params = urlencode(
        {
            "toName": dest,
            "when": checkin_iso,
            "return_date": checkout_iso,
            "adults": 1,
        },
        quote_via=quote_plus,
    )
    yandex_train_params = urlencode(
        {
            "toName": dest,
            "when": checkin_iso,
        },
        quote_via=quote_plus,
    )
    tutu_params = urlencode({"to_name": dest, "date": checkin_dmy}, quote_via=quote_plus)

    stay = [
        {
            "id": "booking",
            "label": "Booking",
            "url": f"https://www.booking.com/searchresults.ru.html?{booking_params}",
        },
        {
            "id": "ostrovok",
            "label": "Островок",
            "url": f"https://ostrovok.ru/hotel/search/results/?{ostrovok_params}",
        },
        {
            "id": "yandex_hotels",
            "label": "Я.Путешествия",
            "url": f"https://travel.yandex.ru/hotels/search/?{yandex_hotel_params}",
        },
        {
            "id": "sutochno",
            "label": "Суточно.ру",
            "url": f"https://sutochno.ru/front/searchapp/search?{sutochno_params}",
        },
    ]
    tickets = [
        {
            "id": "aviasales",
            "label": "Aviasales",
            "url": f"https://www.aviasales.ru/search?{aviasales_params}",
        },
        {
            "id": "yandex_avia",
            "label": "Я.Авиа",
            "url": f"https://travel.yandex.ru/avia/search/?{yandex_avia_params}",
        },
        {
            "id": "yandex_trains",
            "label": "Я.Поезда",
            "url": f"https://travel.yandex.ru/trains/search/?{yandex_train_params}",
        },
        {
            "id": "tutu",
            "label": "Туту.ру",
            "url": f"https://www.tutu.ru/poezda/?{tutu_params}",
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
