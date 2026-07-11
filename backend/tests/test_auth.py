def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "Travel Agent"


def test_register_and_login(client):
    payload = {"email": "user@test.com", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201

    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@test.com"


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 400


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "a@test.com", "password": "secret123"})
    response = client.post("/api/auth/login", json={"email": "a@test.com", "password": "wrong!"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_register_short_password(client):
    res = client.post(
        "/api/auth/register", json={"email": "short@test.com", "password": "1234567"}
    )
    assert res.status_code == 422


def test_auth_rate_limit(client, monkeypatch):
    from app.services.rate_limit import reset_rate_limits

    reset_rate_limits()
    monkeypatch.setattr("app.config.settings.auth_rate_limit_per_minute", 3)
    monkeypatch.setattr("app.services.rate_limit.settings.auth_rate_limit_per_minute", 3)
    for i in range(3):
        r = client.post(
            "/api/auth/login",
            json={"email": f"x{i}@test.com", "password": "wrongpass"},
        )
        assert r.status_code == 401
    r = client.post(
        "/api/auth/login",
        json={"email": "x@test.com", "password": "wrongpass"},
    )
    assert r.status_code == 429


def test_registration_disabled(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.registration_enabled", False)
    monkeypatch.setattr("app.routers.auth.settings.registration_enabled", False)
    res = client.post(
        "/api/auth/register",
        json={"email": "blocked@test.com", "password": "secret123"},
    )
    assert res.status_code == 403
