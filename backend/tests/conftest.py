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
