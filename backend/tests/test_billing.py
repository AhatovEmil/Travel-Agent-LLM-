"""Тесты месячной квоты генераций и админ-начисления."""


def _auth(client, email="quota@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_trip(client, headers, name="Trip"):
    r = client.post(
        "/api/trips",
        headers=headers,
        json={
            "name": name,
            "brief": "Направление: Батуми. Длительность: 3 дн. Интересы: море.",
            "start_date": "2026-08-01",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_me_includes_quota(client, auth_headers):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["free_limit"] == 5
    assert body["free_left"] == 5
    assert body["free_used"] == 0
    assert body["credit_balance"] == 0
    assert body["period"]


def test_packages_endpoint(client):
    r = client.get("/api/billing/packages")
    assert r.status_code == 200
    body = r.json()
    assert len(body["packages"]) >= 1
    assert body["free_generations_per_month"] == 5
    assert "telegram" in body["telegram_url"] or body["telegram_url"].startswith("http")


def test_five_free_runs_then_402(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.free_generations_per_month", 5)
    monkeypatch.setattr("app.services.billing.settings.free_generations_per_month", 5)

    def fake_pipeline(trip_id: int):
        from app.database import SessionLocal
        from app.models import Trip

        db = SessionLocal()
        try:
            trip = db.get(Trip, trip_id)
            if trip:
                trip.status = "completed"
                trip.current_phase = "checklist"
                db.commit()
        finally:
            db.close()

    monkeypatch.setattr("app.routers.trips.run_pipeline", fake_pipeline)

    headers = _auth(client, "five@test.com")
    for i in range(5):
        tid = _create_trip(client, headers, f"T{i}")
        r = client.post(f"/api/trips/{tid}/run", headers=headers)
        assert r.status_code == 202, r.text

    me = client.get("/api/auth/me", headers=headers).json()
    assert me["free_left"] == 0
    assert me["free_used"] == 5

    tid = _create_trip(client, headers, "T6")
    r = client.post(f"/api/trips/{tid}/run", headers=headers)
    assert r.status_code == 402, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "quota_exceeded"
    assert detail["free_left"] == 0
    assert "packages" in detail


def test_credits_allow_run_after_free(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.free_generations_per_month", 1)
    monkeypatch.setattr("app.services.billing.settings.free_generations_per_month", 1)
    monkeypatch.setattr("app.config.settings.admin_credit_token", "secret-admin")
    monkeypatch.setattr("app.routers.billing.settings.admin_credit_token", "secret-admin")

    def fake_pipeline(trip_id: int):
        from app.database import SessionLocal
        from app.models import Trip

        db = SessionLocal()
        try:
            trip = db.get(Trip, trip_id)
            if trip:
                trip.status = "completed"
                db.commit()
        finally:
            db.close()

    monkeypatch.setattr("app.routers.trips.run_pipeline", fake_pipeline)

    headers = _auth(client, "credit@test.com")
    tid = _create_trip(client, headers, "A")
    assert client.post(f"/api/trips/{tid}/run", headers=headers).status_code == 202

    tid2 = _create_trip(client, headers, "B")
    assert client.post(f"/api/trips/{tid2}/run", headers=headers).status_code == 402

    admin = client.post(
        "/api/admin/credits",
        headers={"X-Admin-Token": "secret-admin"},
        json={"email": "credit@test.com", "amount": 2},
    )
    assert admin.status_code == 200, admin.text
    assert admin.json()["credit_balance"] == 2

    tid3 = _create_trip(client, headers, "C")
    assert client.post(f"/api/trips/{tid3}/run", headers=headers).status_code == 202
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["credit_balance"] == 1


def test_admin_credits_requires_token(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.admin_credit_token", "")
    monkeypatch.setattr("app.routers.billing.settings.admin_credit_token", "")
    r = client.post(
        "/api/admin/credits",
        headers={"X-Admin-Token": "x"},
        json={"email": "a@b.com", "amount": 1},
    )
    assert r.status_code == 503


def test_month_rollover_resets_free(client, monkeypatch):
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import User
    from app.services import billing as billing_svc

    monkeypatch.setattr("app.config.settings.free_generations_per_month", 5)
    monkeypatch.setattr("app.services.billing.settings.free_generations_per_month", 5)

    headers = _auth(client, "month@test.com")
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "month@test.com"))
        assert user is not None
        user.free_used_month = "2020-01"
        user.free_used_count = 5
        db.commit()
        db.refresh(user)
        assert billing_svc.free_left(user) == 5
        assert user.free_used_count == 0
        assert user.free_used_month == billing_svc.current_period()
    finally:
        db.close()
