from datetime import date, timedelta
from types import SimpleNamespace

from app.services.trip_os import (
    build_morning_briefing,
    parse_done_slots,
    serialize_done_slots,
    trip_day_window,
)


def _trip(name, brief, itinerary="", start_date=None):
    arts = []
    if itinerary:
        arts.append(SimpleNamespace(phase="itinerary", content=itinerary))
    return SimpleNamespace(
        name=name,
        brief=brief,
        start_date=start_date,
        artifacts=arts,
    )


ITIN = (
    "## День 1 — обзор\n\n"
    "### 10:00–12:00 — Бульвар\nПрогулка.\n\n"
    "### 13:00–14:00 — Кафе\nОбед.\n\n"
    "## День 2 — море\n\n"
    "### 11:00–13:00 — Пляж\nКупание.\n"
)


def test_window_plan_before_start():
    start = date.today() + timedelta(days=10)
    trip = _trip("Батуми", "Направление: Батуми. Длительность: 2 дн.", ITIN, start)
    w = trip_day_window(trip)
    assert w["phase"] == "plan"
    assert w["day_index"] == 0


def test_window_onsite_today():
    start = date.today()
    trip = _trip("Батуми", "Направление: Батуми. Длительность: 2 дн.", ITIN, start)
    w = trip_day_window(trip)
    assert w["phase"] == "onsite"
    assert w["day_index"] == 0


def test_window_memories_after_end():
    start = date.today() - timedelta(days=20)
    trip = _trip("Батуми", "Направление: Батуми. Длительность: 2 дн.", ITIN, start)
    w = trip_day_window(trip)
    assert w["phase"] == "memories"


def test_morning_briefing_has_slots():
    start = date.today()
    trip = _trip("Батуми", "Направление: Батуми.", ITIN, start)
    b = build_morning_briefing(trip, 0)
    assert b["day_index"] == 0
    assert len(b["slots_preview"]) >= 1
    assert b["tip"]
    assert b["emergency"]


def test_done_slots_roundtrip():
    raw = serialize_done_slots(["a", "b", ""])
    assert parse_done_slots(raw) == ["a", "b"]


def test_journal_and_evening_api(client, auth_headers):
    r = client.post(
        "/api/trips",
        headers=auth_headers,
        json={
            "name": "Батуми OS",
            "brief": "Направление: Батуми. Длительность: 2 дн.",
            "start_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 201
    trip_id = r.json()["id"]

    # seed itinerary artifact via DB would be heavy — briefing still works without
    win = client.get(f"/api/trips/{trip_id}/os/window", headers=auth_headers)
    assert win.status_code == 200
    assert win.json()["phase"] in ("plan", "onsite", "memories")

    brief = client.get(f"/api/trips/{trip_id}/os/briefing", headers=auth_headers)
    assert brief.status_code == 200
    assert "day_title" in brief.json()

    note = client.post(
        f"/api/trips/{trip_id}/journal",
        headers=auth_headers,
        json={"day_index": 0, "kind": "note", "content": "Кофе у моря"},
    )
    assert note.status_code == 201
    assert note.json()["content"] == "Кофе у моря"

    eve = client.post(
        f"/api/trips/{trip_id}/os/evening",
        headers=auth_headers,
        json={
            "day_index": 0,
            "mood": "great",
            "content": "День огонь",
            "done_slots": ["d0-s0"],
        },
    )
    assert eve.status_code == 200
    assert eve.json()["kind"] == "evening"
    assert eve.json()["done_slots"] == ["d0-s0"]

    eve2 = client.post(
        f"/api/trips/{trip_id}/os/evening",
        headers=auth_headers,
        json={"day_index": 0, "mood": "ok", "content": "Обновил", "done_slots": []},
    )
    assert eve2.status_code == 200
    assert eve2.json()["id"] == eve.json()["id"]
    assert eve2.json()["mood"] == "ok"

    listed = client.get(f"/api/trips/{trip_id}/journal", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    deleted = client.delete(
        f"/api/trips/{trip_id}/journal/{note.json()['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204
