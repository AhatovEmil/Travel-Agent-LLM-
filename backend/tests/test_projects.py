IDEA = {"name": "Cloth Market", "idea": "Хочу сделать маркетплейс одежды с заказами"}


def test_create_and_list_projects(client, auth_headers):
    created = client.post("/api/projects", json=IDEA, headers=auth_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["name"] == "Cloth Market"

    listing = client.get("/api/projects", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_project_requires_auth(client):
    assert client.post("/api/projects", json=IDEA).status_code == 401
    assert client.get("/api/projects").status_code == 401


def test_project_isolation_between_users(client, auth_headers):
    project_id = client.post("/api/projects", json=IDEA, headers=auth_headers).json()["id"]

    other = client.post(
        "/api/auth/register", json={"email": "other@test.com", "password": "secret123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other}"}

    assert client.get(f"/api/projects/{project_id}", headers=other_headers).status_code == 404
    assert client.get("/api/projects", headers=other_headers).json() == []


def test_delete_project(client, auth_headers):
    project_id = client.post("/api/projects", json=IDEA, headers=auth_headers).json()["id"]
    assert client.delete(f"/api/projects/{project_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/projects/{project_id}", headers=auth_headers).status_code == 404


def test_idea_validation(client, auth_headers):
    response = client.post(
        "/api/projects", json={"name": "X", "idea": "short"}, headers=auth_headers
    )
    assert response.status_code == 422
