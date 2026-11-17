from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200_with_status():
    with TestClient(app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "db" in r.json()
