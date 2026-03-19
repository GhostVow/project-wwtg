"""Test health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # In test env (no real DB/Redis), status may be degraded — that's fine
    assert data["status"] in ("ok", "degraded")


def test_chat_history_returns_empty() -> None:
    response = client.get("/api/v1/chat/history/test-session")
    assert response.status_code == 200
    assert response.json() == []
