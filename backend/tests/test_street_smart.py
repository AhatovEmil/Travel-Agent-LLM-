from types import SimpleNamespace

from app.services.street_smart import (
    build_arrival,
    build_quest_fallback,
    build_survival,
    build_taste,
    build_traps,
    detect_region,
    parse_json_list,
)


def _trip(name, brief, itinerary=""):
    arts = []
    if itinerary:
        arts.append(SimpleNamespace(phase="itinerary", content=itinerary))
    return SimpleNamespace(
        name=name,
        brief=brief,
        start_date=None,
        artifacts=arts,
    )


def test_detect_region_batumi_paris():
    assert detect_region("Батуми") == "ge"
    assert detect_region("Париж") == "eu"


def test_detect_region_russian_cities():
    assert detect_region("Ноябрьск") == "ru"
    assert detect_region("Тюмень") == "ru"
    assert detect_region("Сочи") == "ru"
    assert detect_region("Алтай") == "ru"


def test_survival_batumi_has_georgian_phrases():
    trip = _trip("Батуми, 3 дн.", "Направление: Батуми. Длительность: 3 дн.")
    data = build_survival(trip)
    assert data["region"] == "ge"
    assert data["emergency"]
    assert len(data["phrases"]) >= 6
    assert any("გამარჯობა" in p["local"] or "gamarjoba" in p["latin"] for p in data["phrases"])


def test_traps_and_taste_paris():
    trip = _trip("Париж", "Направление: Париж. Длительность: 4 дн.")
    traps = build_traps(trip)
    taste = build_taste(trip)
    assert traps["region"] == "eu"
    assert len(traps["traps"]) >= 4
    assert taste["items"]
    assert all("dish" in x and "where" in x for x in taste["items"])


def test_arrival_steps():
    trip = _trip("Стамбул", "Направление: Стамбул.")
    arrival = build_arrival(trip)
    assert arrival["region"] == "tr"
    assert len(arrival["steps"]) >= 4


def test_quest_fallback_uses_places():
    itinerary = (
        "## День 1 — обзор\n\n"
        "### 10:00–12:00 — Батумский бульвар\nПрогулка.\n\n"
        "### 13:00–14:00 — Кафе\nОбед.\n"
    )
    trip = _trip("Батуми", "Направление: Батуми.", itinerary)
    quest = build_quest_fallback(trip, 0)
    assert len(quest["missions"]) == 3
    assert "бульвар" in quest["missions"][0]["text"].lower() or "Батум" in quest["missions"][0]["text"]


def test_parse_json_list():
    raw = '```json\n{"phrases":[{"local":"A","latin":"a","ru":"А"}]}\n```'
    assert parse_json_list(raw, "phrases")[0]["local"] == "A"


def test_street_smart_api(client, auth_headers, monkeypatch):
    from app.services.engine import TravelEngine

    monkeypatch.setattr("app.services.engine.settings.llm_api_key", "test-key")
    engine = TravelEngine()

    def fake_complete(prompt, temperature=0.5):
        if "микромиссии" in prompt:
            return '{"missions":["A","B","C"]}'
        if "ловушек" in prompt.lower() or "traps" in prompt:
            return '{"traps":[{"title":"X","how":"Y"}]}'
        if "фраз" in prompt.lower() or "phrases" in prompt:
            return '{"phrases":[{"local":"Hi","latin":"hi","ru":"Привет"}]}'
        return "{}"

    monkeypatch.setattr(engine, "_complete", fake_complete)
    monkeypatch.setattr("app.routers.trips.get_engine", lambda: engine)

    trip_id = client.post(
        "/api/trips",
        json={
            "name": "Батуми",
            "brief": "Направление: Батуми. Длительность: 3 дн. Дата начала: 2026-07-12.",
            "start_date": "2026-07-12",
        },
        headers=auth_headers,
    ).json()["id"]

    surv = client.get(f"/api/trips/{trip_id}/street-smart/survival", headers=auth_headers)
    assert surv.status_code == 200
    assert surv.json()["region"] == "ge"

    traps = client.get(f"/api/trips/{trip_id}/street-smart/traps", headers=auth_headers)
    assert traps.status_code == 200
    assert traps.json()["traps"]

    taste = client.get(f"/api/trips/{trip_id}/street-smart/taste", headers=auth_headers)
    assert taste.status_code == 200
    assert taste.json()["items"]

    arrival = client.get(f"/api/trips/{trip_id}/street-smart/arrival", headers=auth_headers)
    assert arrival.status_code == 200
    assert arrival.json()["steps"]

    quest = client.post(
        f"/api/trips/{trip_id}/street-smart/quest",
        json={"day_index": 0},
        headers=auth_headers,
    )
    assert quest.status_code == 200
    body = quest.json()
    assert len(body["missions"]) == 3
