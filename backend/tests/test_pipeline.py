import time

from app.services.engine import LLMGenerationError, TravelEngine

TRIP = {
    "name": "Батуми",
    "brief": "Направление: Батуми. Длительность: 5 дн. Дата начала: 2026-07-12. Бюджет: 50000.",
    "start_date": "2026-07-12",
}
PHASES = ["brief", "itinerary", "budget", "checklist"]


def _mock_engine(monkeypatch):
    engine = TravelEngine()

    def fake_complete(prompt, temperature=0.5):
        if "Вопрос пользователя:" in prompt:
            return "На еду ориентировочно 2000–3000 ₽ в день. Цены нужно уточнять на месте."
        if "Голоса спутников:" in prompt or "Перепиши Itinerary целиком с учётом голосов" in prompt:
            return (
                "## День 1 — 2026-07-12 — пляжи\n\n"
                "### 10:00–14:00 — Пляж\nТолько море.\n\n"
                "## Запасной план на плохую погоду\nКафе."
            )
        if "Перепиши ТОЛЬКО этот день" in prompt:
            return (
                "## День 1 — 2026-07-12 — сжатый\n\n"
                "### 12:00–14:00 — Кафе\nУкрытие от дождя."
            )
        if "Перепиши Itinerary" in prompt:
            return (
                "## День 1 — 2026-07-12 — пляжи\n\n"
                "### 10:00–14:00 — Пляж\nТолько море.\n\n"
                "## День 2 — 2026-07-13\n\n"
                "### 11:00–13:00 — Ещё пляж\nОк."
            )
        if "Составь подробный Itinerary" in prompt:
            return (
                "## День 1 — 2026-07-12 — обзор\n\n"
                "### 09:00–11:00 — Батумский бульвар\nПрогулка.\n\n"
                "### 11:30–13:00 — Кафе на набережной\nОбед.\n\n"
                "## День 2 — 2026-07-13 — город\n\n"
                "### 10:00–12:00 — Музей\nВыставка.\n\n"
                "## Запасной план на плохую погоду\nКафе."
            )
        if "Составь Budget" in prompt:
            return "# Budget\n\nИтого ~50 000 ₽."
        if "Составь Checklist" in prompt:
            return "# Checklist\n\n- [ ] Паспорт"
        if "Составь документ Brief" in prompt:
            return "# Brief\n\nБатуми, 5 дней, море и еда."
        return "# Doc\n\nok"

    monkeypatch.setattr(engine, "_complete", fake_complete)
    monkeypatch.setattr("app.services.pipeline.get_engine", lambda: engine)
    return engine


def _run_to_completion(client, headers, trip_id, timeout=30):
    response = client.post(f"/api/trips/{trip_id}/run", headers=headers)
    assert response.status_code == 202, response.text
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/trips/{trip_id}", headers=headers).json()["status"]
        if status in ("completed", "failed"):
            return status
        time.sleep(0.2)
    raise AssertionError("Pipeline did not finish in time")


def test_engine_raises_without_key(monkeypatch):
    monkeypatch.setattr("app.services.engine.settings.llm_api_key", "")
    from app.services.engine import get_engine

    try:
        get_engine()
        assert False, "expected LLMGenerationError"
    except LLMGenerationError as exc:
        assert "LLM_API_KEY" in str(exc)


def test_full_pipeline(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]

    status = _run_to_completion(client, auth_headers, trip_id)
    assert status == "completed"

    artifacts = client.get(f"/api/trips/{trip_id}/artifacts", headers=auth_headers).json()
    assert [a["phase"] for a in artifacts] == PHASES
    assert "Батуми" in artifacts[0]["content"]
    assert "День 1" in artifacts[1]["content"]


def test_run_without_llm_key_fails(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.config.settings.llm_api_key", "")
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    response = client.post(f"/api/trips/{trip_id}/run", headers=auth_headers)
    assert response.status_code == 503


def test_pipeline_marks_failed_on_llm_error(client, auth_headers, monkeypatch):
    engine = TravelEngine()

    def boom(prompt, temperature=0.5):
        raise LLMGenerationError("DeepSeek offline", phase="brief")

    monkeypatch.setattr(engine, "_complete", boom)
    monkeypatch.setattr("app.services.pipeline.get_engine", lambda: engine)

    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    status = _run_to_completion(client, auth_headers, trip_id)
    assert status == "failed"
    trip = client.get(f"/api/trips/{trip_id}", headers=auth_headers).json()
    assert "DeepSeek offline" in trip["error"]


def test_export_markdown(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    response = client.get(f"/api/trips/{trip_id}/export", headers=auth_headers)
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    text = response.content.decode("utf-8")
    assert "# Батуми" in text
    assert "Itinerary" in text or "День 1" in text


def test_export_before_completion_conflict(client, auth_headers):
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert client.get(f"/api/trips/{trip_id}/export", headers=auth_headers).status_code == 409


def test_export_pdf(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    response = client.get(f"/api/trips/{trip_id}/export.pdf", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF"


def test_ask_question_saves_history(client, auth_headers, monkeypatch):
    engine = _mock_engine(monkeypatch)
    monkeypatch.setattr("app.routers.trips.get_engine", lambda: engine)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    response = client.post(
        f"/api/trips/{trip_id}/ask",
        json={"message": "сколько примерно на еду в день?"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "2000" in body["reply"] or "еду" in body["reply"].lower()
    assert len(body["messages"]) >= 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"

    listed = client.get(f"/api/trips/{trip_id}/messages", headers=auth_headers).json()
    assert len(listed) >= 2


def test_rerun_single_phase(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    response = client.post(
        f"/api/trips/{trip_id}/phases/rerun",
        json={"phase": "budget"},
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert _wait_status(client, auth_headers, trip_id) == "completed"
    arts = client.get(f"/api/trips/{trip_id}/artifacts", headers=auth_headers).json()
    assert any(a["phase"] == "budget" for a in arts)


def test_chat_revises_itinerary(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    response = client.post(
        f"/api/trips/{trip_id}/chat",
        json={"message": "убери музеи, добавь пляжи"},
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert _wait_status(client, auth_headers, trip_id) == "completed"
    arts = {a["phase"]: a["content"] for a in client.get(f"/api/trips/{trip_id}/artifacts", headers=auth_headers).json()}
    assert "пляж" in arts["itinerary"].lower()


def test_extras_parses_days(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    monkeypatch.setattr(
        "app.services.extras.geocode",
        lambda q: {"name": "Batumi", "lat": 41.65, "lon": 41.64, "label": "Batumi", "query": q},
    )
    monkeypatch.setattr(
        "app.services.extras.fetch_weather",
        lambda lat, lon, days=5, start=None: [
            {
                "date": "2026-07-12",
                "temp_max": 28,
                "temp_min": 20,
                "code": 0,
                "label": "Ясно",
            }
        ],
    )
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    extras = client.get(f"/api/trips/{trip_id}/extras", headers=auth_headers).json()
    assert extras["destination"]
    assert len(extras["days"]) >= 2
    assert extras["days"][0]["title"].lower().startswith("день")
    assert extras["days"][0]["slots"]
    assert extras["days"][0]["slots"][0]["links"]["maps"]
    assert extras["center"]["lat"] == 41.65
    assert extras["weather"][0]["label"] == "Ясно"
    assert extras["start_date"] == "2026-07-12"


def test_share_and_vote_and_rebuild(client, auth_headers, monkeypatch):
    engine = _mock_engine(monkeypatch)
    monkeypatch.setattr("app.routers.trips.get_engine", lambda: engine)
    monkeypatch.setattr(
        "app.services.extras.geocode",
        lambda q: {"name": "Batumi", "lat": 41.65, "lon": 41.64, "label": "Batumi", "query": q},
    )
    monkeypatch.setattr("app.services.extras.fetch_weather", lambda *a, **k: [])

    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    share = client.post(f"/api/trips/{trip_id}/share", headers=auth_headers).json()
    token = share["share_token"]
    assert token

    public = client.get(f"/api/share/{token}")
    assert public.status_code == 200
    days = public.json()["days"]
    slot_key = days[0]["slots"][0]["slot_key"]

    vote = client.post(
        f"/api/share/{token}/votes",
        json={
            "voter": "Аня",
            "day_index": 0,
            "slot_key": slot_key,
            "value": "skip",
        },
    )
    assert vote.status_code == 200, vote.text

    rebuild = client.post(f"/api/trips/{trip_id}/rebuild-from-votes", headers=auth_headers)
    assert rebuild.status_code == 202
    assert _wait_status(client, auth_headers, trip_id) == "completed"


def test_live_endpoint(client, auth_headers, monkeypatch):
    _mock_engine(monkeypatch)
    monkeypatch.setattr(
        "app.services.extras.geocode",
        lambda q: {"name": "Batumi", "lat": 41.65, "lon": 41.64, "label": "Batumi", "query": q},
    )
    monkeypatch.setattr("app.services.extras.fetch_weather", lambda *a, **k: [])
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert _run_to_completion(client, auth_headers, trip_id) == "completed"

    live = client.get(
        f"/api/trips/{trip_id}/live?lat=41.65&lon=41.64", headers=auth_headers
    )
    assert live.status_code == 200
    body = live.json()
    assert "now" in body
    assert body.get("next_slot") or body.get("current_slot") or body.get("day")

    adj = client.post(
        f"/api/trips/{trip_id}/live/adjust",
        json={"reason": "rain"},
        headers=auth_headers,
    )
    assert adj.status_code == 202
    assert _wait_status(client, auth_headers, trip_id) == "completed"


def _wait_status(client, headers, trip_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/trips/{trip_id}", headers=headers).json()["status"]
        if status in ("completed", "failed"):
            return status
        time.sleep(0.2)
    raise AssertionError("Job did not finish in time")
