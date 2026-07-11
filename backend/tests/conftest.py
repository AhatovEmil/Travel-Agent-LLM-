import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test_travel.db"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only"
os.environ["LLM_API_KEY"] = "test-key-for-pytest"
os.environ["ENVIRONMENT"] = "development"
os.environ["REGISTRATION_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, ensure_schema
from app.main import app
from app.services.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def clean_db():
    reset_rate_limits()
    Base.metadata.drop_all(bind=engine)
    ensure_schema()
    yield


@pytest.fixture(autouse=True)
def fast_geocode(monkeypatch):
    """В тестах не ходим в Nominatim; «выдуманные» места остаются пустыми."""

    def fake(q: str):
        low = (q or "").lower()
        if any(x in low for x in ("выдуман", "единорог", "unicorn", "fakeplace", "несуществующ")):
            return None
        return {"name": q.split(",")[0], "label": q, "lat": 41.65, "lon": 41.64, "query": q}

    monkeypatch.setattr("app.services.verify_places.geocode", fake)
    monkeypatch.setattr("app.services.geo.geocode", fake)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/api/auth/register", json={"email": "traveler@test.com", "password": "secret123"}
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
