from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_200_with_status():
    with TestClient(app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "db" in r.json()


def test_health_db_unreachable_is_200_db_false(monkeypatch):
    import app.main as m

    monkeypatch.setattr(m, "wait_for_db", lambda *a, **k: True)
    monkeypatch.setattr(m, "_engine", None)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:1/nodb"
    )
    with TestClient(m.app) as c:
        r = c.get("/health")
    monkeypatch.setattr(m, "_engine", None)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": False}
