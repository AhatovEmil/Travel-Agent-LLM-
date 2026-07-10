from app.services.parse import (
    extract_days_count,
    extract_destination,
    extract_place_queries,
    parse_itinerary_days,
)


def test_extract_destination_and_days():
    brief = "Направление: Батуми.\nДлительность: 5 дн.\nБюджет: 50000"
    assert extract_destination(brief) == "Батуми"
    assert extract_days_count(brief) == 5


def test_parse_itinerary_days():
    text = (
        "## День 1 — пляж\nУтро: море.\n\n"
        "## День 2 — город\nМузей.\n\n"
        "## Запасной план на плохую погоду\nКафе."
    )
    days = parse_itinerary_days(text)
    assert len(days) == 2
    assert "День 1" in days[0]["title"]
    assert "море" in days[0]["content"]
    assert "Запасной" not in days[1]["content"]


def test_extract_place_queries():
    queries = extract_place_queries("Посетите **Батумский бульвар** утром.", "Батуми", limit=3)
    assert any("Батуми" in q for q in queries)
    assert any("бульвар" in q.lower() for q in queries)
