import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set"
)


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "stops.json").write_text(json.dumps([
        {"stop_id": 1, "stop_name": "A", "lat": 25.1, "lon": 55.1},
        {"stop_id": 2, "stop_name": "B", "lat": 25.2, "lon": 55.2},
    ]))
    (tmp_path / "coverage.json").write_text(json.dumps([
        {"community_num": 10, "community_name": "X", "population": 100,
         "accessible_population": 50, "geographic_coverage": 0.5},
        {"community_num": 11, "community_name": "Y", "population": 200,
         "accessible_population": 20, "geographic_coverage": 0.1},
        {"community_num": 12, "community_name": "Z", "population": 0,
         "accessible_population": 0, "geographic_coverage": 0},
    ]))
    (tmp_path / "routes.json").write_text(json.dumps([
        {"route_name": "R1", "route_type": "bus", "stop_count": 5},
    ]))
    # stop 1: 2 months; stop 99 is an orphan (not in stops.json)
    (tmp_path / "passengers.json").write_text(json.dumps({
        "placeholder": True, "year": 2026,
        "stations": {
            "1": [{"month": "2026-01", "in": 5, "out": 6},
                  {"month": "2026-02", "in": 7, "out": 8}],
            "99": [{"month": "2026-01", "in": 1, "out": 1}],
        }}))
    return tmp_path


def _counts(engine):
    from sqlalchemy import text
    tables = ["dim_stop", "dim_community", "dim_route", "fact_coverage",
              "fact_passengers_monthly"]
    with engine.connect() as c:
        return {t: c.execute(text(f"select count(*) from {t}")).scalar()
                for t in tables}


def test_load_counts_and_idempotent(data_dir, capsys):
    from app.db import engine
    from app.loader import load
    eng = engine()
    load(eng, str(data_dir))
    first = _counts(eng)
    assert first == {"dim_stop": 2, "dim_community": 3, "dim_route": 1,
                     "fact_coverage": 3, "fact_passengers_monthly": 4}
    assert "orphan" in capsys.readouterr().out.lower()
    load(eng, str(data_dir))
    assert _counts(eng) == first
