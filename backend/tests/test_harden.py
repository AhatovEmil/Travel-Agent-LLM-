"""Тесты пакета harden: recover, rate limit, geocode cache, ensure slots, live mode."""

from datetime import date, timedelta

from app.services.engine import TravelEngine
from app.services.geo import clear_geocode_cache, geocode
from app.services.rate_limit import reset_rate_limits
from app.services.recover import STUCK_MESSAGE, fail_stuck_running_trips


def test_fail_stuck_running_on_demand(client, auth_headers, monkeypatch):
    from app.database import SessionLocal
    from app.models import Trip

    trip_id = client.post(
        "/api/trips",
        json={"name": "X", "brief": "Направление: Тест. Длительность: 3 дн. достаточно текста."},
        headers=auth_headers,
    ).json()["id"]

    db = SessionLocal()
    trip = db.get(Trip, trip_id)
    trip.status = "running"
    trip.current_phase = "brief"
    db.commit()
    db.close()

    n = fail_stuck_running_trips()
    assert n >= 1
    trip = client.get(f"/api/trips/{trip_id}", headers=auth_headers).json()
    assert trip["status"] == "failed"
    assert STUCK_MESSAGE in trip["error"]


def test_recover_endpoint(client, auth_headers):
    from app.database import SessionLocal
    from app.models import Trip

    trip_id = client.post(
        "/api/trips",
        json={"name": "Y", "brief": "Направление: Тест. Длительность: 3 дн. достаточно текста."},
        headers=auth_headers,
    ).json()["id"]
    db = SessionLocal()
    trip = db.get(Trip, trip_id)
    trip.status = "running"
    db.commit()
    db.close()

    res = client.post(f"/api/trips/{trip_id}/recover", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "failed"


def test_llm_rate_limit_429(client, auth_headers, monkeypatch):
    reset_rate_limits()
    monkeypatch.setattr("app.config.settings.llm_rate_limit_per_hour", 2)
    monkeypatch.setattr("app.services.rate_limit.settings.llm_rate_limit_per_hour", 2)

    trip_id = client.post(
        "/api/trips",
        json={
            "name": "Z",
            "brief": "Направление: Батуми. Длительность: 3 дн. Дата начала: 2026-07-12.",
        },
        headers=auth_headers,
    ).json()["id"]

    # mock pipeline so run doesn't need real LLM long path — but rate limit hits before task
    monkeypatch.setattr("app.routers.trips.run_pipeline", lambda *a, **k: None)

    r1 = client.post(f"/api/trips/{trip_id}/run", headers=auth_headers)
    assert r1.status_code == 202
    # reset status so second run allowed by idle check
    from app.database import SessionLocal
    from app.models import Trip

    db = SessionLocal()
    t = db.get(Trip, trip_id)
    t.status = "completed"
    db.commit()
    db.close()

    r2 = client.post(f"/api/trips/{trip_id}/run", headers=auth_headers)
    assert r2.status_code == 202
    db = SessionLocal()
    t = db.get(Trip, trip_id)
    t.status = "completed"
    db.commit()
    db.close()

    r3 = client.post(f"/api/trips/{trip_id}/run", headers=auth_headers)
    assert r3.status_code == 429


def test_geocode_cache_hit(monkeypatch, tmp_path):
    clear_geocode_cache()
    calls = {"n": 0}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"display_name": "Batumi, Georgia", "lat": "41.65", "lon": "41.64"}]

    def fake_get(*a, **k):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr("app.services.geo.httpx.get", fake_get)
    monkeypatch.setattr("app.services.geo._CACHE_PATH", tmp_path / "cache.json")
    # force reload
    import app.services.geo as geo_mod

    geo_mod._loaded = False
    geo_mod._memory.clear()

    a = geocode("Batumi")
    b = geocode("Batumi")
    assert a["lat"] == 41.65
    assert b["lat"] == 41.65
    assert calls["n"] == 1


def test_ensure_structured_itinerary(monkeypatch):
    engine = TravelEngine()
    calls = []

    def fake_complete(prompt, temperature=0.5):
        calls.append(prompt)
        return (
            "## День 1 — 2026-07-12 — обзор\n\n"
            "### 09:00–11:00 — Бульвар\nПрогулка.\n\n"
            "## Запасной план на плохую погоду\nКафе."
        )

    monkeypatch.setattr(engine, "_complete", fake_complete)
    bad = "## День 1\nПросто текст без слотов.\n\n## День 2\nЕщё текст."
    assert engine.itinerary_needs_structure(bad)
    fixed = engine.ensure_structured_itinerary(bad)
    assert "###" in fixed
    assert "09:00" in fixed
    assert len(calls) == 1
    # already structured — no second call
    again = engine.ensure_structured_itinerary(fixed)
    assert again == fixed
    assert len(calls) == 1


def test_live_preview_mode(client, auth_headers, monkeypatch):
    from app.services.engine import TravelEngine

    engine = TravelEngine()
    future = (date.today() + timedelta(days=10)).isoformat()

    def fake_complete(prompt, temperature=0.5):
        if "Составь подробный Itinerary" in prompt or "Перепиши план ниже" in prompt:
            return (
                f"## День 1 — {future} — обзор\n\n"
                "### 09:00–11:00 — Бульвар\nПрогулка.\n\n"
                f"## День 2 — {future}\n\n"
                "### 10:00–12:00 — Кафе\nОбед.\n\n"
                "## Запасной план на плохую погоду\nДом."
            )
        if "Составь Budget" in prompt:
            return "# Budget\nok"
        if "Составь Checklist" in prompt:
            return "# Checklist\n- [ ] x"
        if "Составь документ Brief" in prompt:
            return "# Brief\nok"
        return "# Doc\nok"

    monkeypatch.setattr(engine, "_complete", fake_complete)
    monkeypatch.setattr("app.services.pipeline.get_engine", lambda: engine)
    monkeypatch.setattr(
        "app.services.extras.geocode",
        lambda q: {"name": "X", "lat": 41.0, "lon": 41.0, "label": "X", "query": q},
    )
    monkeypatch.setattr("app.services.extras.fetch_weather", lambda *a, **k: [])

    trip_id = client.post(
        "/api/trips",
        json={
            "name": "Future",
            "brief": f"Направление: Батуми. Длительность: 2 дн. Дата начала: {future}.",
            "start_date": future,
        },
        headers=auth_headers,
    ).json()["id"]

    import time

    assert client.post(f"/api/trips/{trip_id}/run", headers=auth_headers).status_code == 202
    deadline = time.time() + 30
    while time.time() < deadline:
        st = client.get(f"/api/trips/{trip_id}", headers=auth_headers).json()["status"]
        if st in ("completed", "failed"):
            break
        time.sleep(0.2)
    assert st == "completed"

    live = client.get(f"/api/trips/{trip_id}/live", headers=auth_headers).json()
    assert live["mode"] == "preview"
    assert "Демо" in live["notice"] or "начинается" in live["notice"]
