import time

from app.services.engine import LLMGenerationError, TravelEngine

TRIP = {
    "name": "Батуми",
    "brief": "Батуми, 5 дней, бюджет 50000 рублей, море и еда",
}
PHASES = ["brief", "itinerary", "budget", "checklist"]


def _mock_engine(monkeypatch):
    engine = TravelEngine()

    def fake_complete(prompt, temperature=0.5):
        if "Составь подробный Itinerary" in prompt:
            return "# Itinerary\n\n## День 1\nПляж и набережная."
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
