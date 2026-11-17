import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set"
)

GEOJSON = os.path.join(
    os.path.dirname(__file__), "..", "..", "web", "data", "communities.geojson"
)


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("COMMUNITIES_GEOJSON", GEOJSON)
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_stops_limit(client):
    r = client.get("/stops?limit=5")
    assert r.status_code == 200
    j = r.json()
    assert len(j["results"]) == 5
    assert j["total"] >= 5


@pytest.mark.parametrize("path", ["/stops", "/communities", "/routes"])
def test_paginated_validation(client, path):
    assert client.get(path + "?limit=0").status_code == 422
    assert client.get(path + "?limit=100000").status_code == 422
    assert client.get(path + "?offset=-1").status_code == 422
    assert client.get(path).status_code == 200


def test_communities_and_routes_shape(client):
    assert "total" in client.get("/communities?limit=2").json()
    assert len(client.get("/routes?limit=2").json()["results"]) == 2


def test_coverage(client):
    j = client.get("/coverage").json()
    assert j["results"] and "geographic_coverage" in j["results"][0]


def test_passengers_empty_month(client):
    r = client.get("/passengers?month=2099-01&direction=in")
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_passengers_validation(client):
    assert client.get("/passengers?month=2099-01&direction=sideways").status_code == 422
    assert client.get("/passengers?month=bogus&direction=in").status_code == 422


def test_passengers_real_month(client):
    r = client.get("/passengers?month=2099-01&direction=in")
    assert r.status_code == 200
    import sqlalchemy as sa
    from app.db import engine

    with engine().connect() as c:
        m = c.execute(sa.text("select min(month) from fact_passengers_monthly")).scalar()
    j = client.get(f"/passengers?month={m}&direction=out&limit=3").json()
    assert j["results"] and "placeholder" in j["results"][0]


def test_kpis(client):
    j = client.get("/kpis").json()
    for k in [
        "stops", "communities", "routes", "coverage_avg", "coverage_median",
        "population", "accessible_population", "passengers_placeholder",
    ]:
        assert k in j
    assert isinstance(j["passengers_placeholder"], bool)


def test_geojson(client):
    r = client.get("/communities.geojson")
    assert r.status_code == 200
    j = r.json()
    assert j["type"] == "FeatureCollection"
    assert j["features"]
    p = j["features"][0]["properties"]
    for k in ["population", "accessible_population", "geographic_coverage"]:
        assert k in p
