from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import create_app


def test_health_check_returns_project_status(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "library-system",
        "environment": "test",
    }
    get_settings.cache_clear()
