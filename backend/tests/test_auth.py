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
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "a@test.com", "password": "secret123"})
    response = client.post("/api/auth/login", json={"email": "a@test.com", "password": "wrong!"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
