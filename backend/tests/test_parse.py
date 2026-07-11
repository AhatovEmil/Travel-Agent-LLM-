from datetime import date

from app.services.links import destination_links, place_links
from app.services.parse import (
    extract_start_date,
    minutes_between,
    parse_day_slots,
    parse_itinerary_days,
    replace_day_in_itinerary,
)


def test_parse_slots_and_dates():
    text = (
        "## День 1 — 2026-07-12 — обзор\n\n"
        "### 09:00–11:00 — Батумский бульвар\n"
        "Прогулка.\n\n"
        "### 11:30–13:00 — Кафе на набережной\n"
        "Обед.\n\n"
        "## День 2 — 2026-07-13 — море\n\n"
        "### 10:00–14:00 — Пляж\n"
        "Купание.\n"
    )
    days = parse_itinerary_days(text, start_date=date(2026, 7, 12))
    assert len(days) == 2
    assert days[0]["date"] == "2026-07-12"
    assert len(days[0]["slots"]) == 2
    assert days[0]["slots"][0]["place"] == "Батумский бульвар"
    assert days[0]["slots"][0]["start"] == "09:00"
    assert minutes_between("11:00", "11:30") == 30


def test_extract_start_date():
    assert extract_start_date("Дата начала: 2026-08-01. Длительность: 3 дн.") == date(2026, 8, 1)


def test_replace_day():
    original = "## День 1 — A\n\nold\n\n## День 2 — B\n\nkeep\n"
    updated = replace_day_in_itinerary(original, 0, "## День 1 — A\n\nnew")
    assert "new" in updated
    assert "keep" in updated
    assert "old" not in updated


def test_links_shape():
    from datetime import date

    links = place_links("Бульвар", "Батуми", checkin=date(2026, 7, 12), nights=5)
    assert "yandex.ru/maps" in links["maps"]
    assert "Батуми" in links["maps"] or "%D0%91" in links["maps"]
    assert links["booking"] == "https://www.booking.com/"
    assert links["checkin"] == "2026-07-12"
    assert links["checkout"] == "2026-07-17"
    assert links["nights"] == 5
    by_id = {s["id"]: s["url"] for s in links["stay"]}
    assert by_id["ostrovok"] == "https://ostrovok.ru/"
    assert by_id["yandex_hotels"] == "https://travel.yandex.ru/hotels/"
    assert by_id["sutochno"] == "https://sutochno.ru/"
    tickets = {t["id"]: t["url"] for t in links["tickets"]}
    assert tickets["aviasales"] == "https://www.aviasales.ru/"
    assert tickets["yandex_avia"] == "https://travel.yandex.ru/avia/"
    assert tickets["yandex_trains"] == "https://travel.yandex.ru/trains/"
    assert tickets["tutu"] == "https://www.tutu.ru/"
    assert destination_links("Батуми", checkin=date(2026, 7, 12))["maps"]
