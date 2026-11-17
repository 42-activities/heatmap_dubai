import json
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from .. import settings
from ..models import (Community, Coverage, Kpis, Page, PassengerRow, Route,
                      Stop)

router = APIRouter()


def _conn():
    from .. import main  # lazy: shared engine, avoids import cycle

    return main._get_engine().connect()


def _page(table: str, cols: str, order: str, model, limit: int, offset: int):
    # table/cols/order are internal constants; values are bound parameters.
    with _conn() as c:
        total = c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        rows = c.execute(
            text(f"SELECT {cols} FROM {table} ORDER BY {order} LIMIT :l OFFSET :o"),
            {"l": limit, "o": offset},
        ).mappings().all()
    return {"results": [model(**r) for r in rows], "total": total}


Limit = Query(100, ge=1, le=1000)
Offset = Query(0, ge=0)


@router.get("/stops", response_model=Page[Stop])
def stops(limit: int = Limit, offset: int = Offset):
    return _page("dim_stop", "stop_id, stop_name, lat, lon", "stop_id", Stop, limit, offset)


@router.get("/communities", response_model=Page[Community])
def communities(limit: int = Limit, offset: int = Offset):
    return _page("dim_community", "community_num, community_name", "community_num",
                 Community, limit, offset)


@router.get("/routes", response_model=Page[Route])
def routes(limit: int = Limit, offset: int = Offset):
    return _page("dim_route", "route_name, route_type, stop_count", "route_name",
                 Route, limit, offset)


_COVERAGE_SQL = """
SELECT c.community_num, c.community_name, f.population,
       f.accessible_population, f.geographic_coverage
FROM dim_community c JOIN fact_coverage f USING (community_num)
ORDER BY c.community_num
"""


@router.get("/coverage", response_model=Page[Coverage])
def coverage():
    with _conn() as c:
        rows = c.execute(text(_COVERAGE_SQL)).mappings().all()
    return {"results": [Coverage(**r) for r in rows], "total": len(rows)}


@router.get("/passengers", response_model=Page[PassengerRow])
def passengers(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    direction: Literal["in", "out"] = Query(...),
    limit: int = Query(5000, ge=1, le=10000),
    offset: int = Offset,
):
    p = {"m": month, "d": direction}
    with _conn() as c:
        total = c.execute(
            text("SELECT count(*) FROM fact_passengers_monthly WHERE month=:m AND direction=:d"),
            p,
        ).scalar_one()
        rows = c.execute(
            text("SELECT stop_id, month, direction, count, placeholder "
                 "FROM fact_passengers_monthly WHERE month=:m AND direction=:d "
                 "ORDER BY stop_id LIMIT :l OFFSET :o"),
            {**p, "l": limit, "o": offset},
        ).mappings().all()
    return {"results": [PassengerRow(**r) for r in rows], "total": total}


_KPI_SQL = """
SELECT
  (SELECT count(*) FROM dim_stop) AS stops,
  (SELECT count(*) FROM dim_community) AS communities,
  (SELECT count(*) FROM dim_route) AS routes,
  (SELECT coalesce(avg(geographic_coverage), 0) FROM fact_coverage) AS coverage_avg,
  (SELECT coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY geographic_coverage), 0)
     FROM fact_coverage) AS coverage_median,
  (SELECT coalesce(sum(population),0) FROM fact_coverage) AS population,
  (SELECT coalesce(sum(accessible_population),0) FROM fact_coverage) AS accessible_population,
  (SELECT coalesce(bool_or(placeholder), false) FROM fact_passengers_monthly)
     AS passengers_placeholder
"""


@router.get("/kpis", response_model=Kpis)
def kpis():
    with _conn() as c:
        row = c.execute(text(_KPI_SQL)).mappings().one()
    return Kpis(**row)


@router.get("/communities.geojson")
def communities_geojson():
    path = os.environ.get("COMMUNITIES_GEOJSON") or os.path.join(
        settings.data_dir(), "communities.geojson"
    )
    try:
        with open(path, encoding="utf-8") as fh:
            gj = json.load(fh)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="communities.geojson not available")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="communities.geojson is malformed")
    with _conn() as c:
        rows = c.execute(text(
            "SELECT community_num, population, accessible_population, geographic_coverage "
            "FROM fact_coverage")).mappings().all()
    by_num = {r["community_num"]: r for r in rows}
    for feat in gj.get("features", []):
        props = feat.setdefault("properties", {})
        r = by_num.get(props.get("community_num"))
        if r:
            props["population"] = r["population"]
            props["accessible_population"] = r["accessible_population"]
            props["geographic_coverage"] = r["geographic_coverage"]
        else:
            props.setdefault("population", None)
            props.setdefault("accessible_population", None)
            props.setdefault("geographic_coverage", None)
    return gj
