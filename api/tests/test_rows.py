import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import rows as rows_mod  # noqa: E402


def test_stop_rows_shape_and_int_id():
    out = rows_mod.stop_rows([{"stop_id": "7", "stop_name": "A", "lat": "25.1", "lon": 55.2}])
    assert out == [{"stop_id": 7, "stop_name": "A", "lat": 25.1, "lon": 55.2}]


def test_community_rows_coerces_numerics():
    out = rows_mod.community_rows([
        {"community_num": "246", "community_name": "X", "population": "2838",
         "accessible_population": None, "geographic_coverage": float("nan")},
    ])
    r = out[0]
    assert r["community_num"] == 246 and isinstance(r["community_num"], int)
    assert r["population"] == 2838 and isinstance(r["population"], int)
    assert r["accessible_population"] == 0
    assert r["geographic_coverage"] == 0.0
    assert r["community_name"] == "X"


def test_route_rows_shape():
    out = rows_mod.route_rows([{"route_name": "GK2", "route_type": "EK", "stop_count": "38"}])
    assert out == [{"route_name": "GK2", "route_type": "EK", "stop_count": 38}]


def test_passenger_rows_unpivots_in_out():
    data = {"placeholder": True, "stations": {"5": [{"month": "2026-01", "in": 10, "out": 3}]}}
    rows = rows_mod.passenger_rows(data)
    assert {"stop_id": 5, "month": "2026-01", "direction": "in", "count": 10, "placeholder": True} in rows
    assert any(r["direction"] == "out" and r["count"] == 3 for r in rows)


def test_passenger_rows_count_and_coercion():
    months = [{"month": "2026-%02d" % m, "in": m, "out": None} for m in range(1, 13)]
    data = {"placeholder": False, "stations": {"1": months, "2": months}}
    rows = rows_mod.passenger_rows(data)
    assert len(rows) == 2 * 12 * 2
    assert all(isinstance(r["count"], int) and r["placeholder"] is False for r in rows)
    assert all(r["count"] == 0 for r in rows if r["direction"] == "out")
