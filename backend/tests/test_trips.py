TRIP = {
    "name": "Батуми",
    "brief": "Батуми, 5 дней, бюджет 50000 рублей, море и еда",
}


def test_create_and_list_trips(client, auth_headers):
    created = client.post("/api/trips", json=TRIP, headers=auth_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["name"] == "Батуми"

    listing = client.get("/api/trips", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_trip_requires_auth(client):
    assert client.post("/api/trips", json=TRIP).status_code == 401
    assert client.get("/api/trips").status_code == 401


def test_trip_isolation_between_users(client, auth_headers):
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]

    other = client.post(
        "/api/auth/register", json={"email": "other@test.com", "password": "secret123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other}"}

    assert client.get(f"/api/trips/{trip_id}", headers=other_headers).status_code == 404
    assert client.get("/api/trips", headers=other_headers).json() == []


def test_delete_trip(client, auth_headers):
    trip_id = client.post("/api/trips", json=TRIP, headers=auth_headers).json()["id"]
    assert client.delete(f"/api/trips/{trip_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/trips/{trip_id}", headers=auth_headers).status_code == 404


def test_brief_validation(client, auth_headers):
    response = client.post(
        "/api/trips", json={"name": "X", "brief": "short"}, headers=auth_headers
    )
    assert response.status_code == 422
