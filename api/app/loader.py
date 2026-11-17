"""Apply schema and (re)seed Postgres from web/data JSON. Idempotent."""
import json
import os
from pathlib import Path

from sqlalchemy import text

from app.rows import community_rows, passenger_rows, route_rows, stop_rows

TABLES = ["fact_passengers_monthly", "fact_coverage", "dim_route",
          "dim_community", "dim_stop"]


def _read(data_dir, name):
    with open(Path(data_dir) / name, encoding="utf-8") as f:
        return json.load(f)


def _insert(conn, sql, rows):
    if rows:
        conn.execute(text(sql), rows)


def load(engine, data_dir, schema_path=None):
    if schema_path is None:
        schema_path = os.environ.get("SCHEMA_PATH") or str(
            Path(__file__).resolve().parents[2] / "sql" / "01_schema.sql")
    schema = Path(schema_path).read_text(encoding="utf-8")

    stops = stop_rows(_read(data_dir, "stops.json"))
    communities = community_rows(_read(data_dir, "coverage.json"))
    routes = route_rows(_read(data_dir, "routes.json"))
    passengers = passenger_rows(_read(data_dir, "passengers.json"))

    known = {s["stop_id"] for s in stops}
    kept = [p for p in passengers if p["stop_id"] in known]
    orphans = len(passengers) - len(kept)
    print(f"skipped {orphans} orphan passenger rows (stop_id not in dim_stop)")

    with engine.begin() as conn:  # single transaction
        conn.exec_driver_sql(schema)
        conn.execute(text(
            "TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE"))
        _insert(conn, "INSERT INTO dim_stop (stop_id, stop_name, lat, lon) "
                "VALUES (:stop_id, :stop_name, :lat, :lon) "
                "ON CONFLICT (stop_id) DO NOTHING", stops)
        _insert(conn, "INSERT INTO dim_route (route_name, route_type, stop_count) "
                "VALUES (:route_name, :route_type, :stop_count) "
                "ON CONFLICT (route_name) DO NOTHING", routes)
        _insert(conn, "INSERT INTO dim_community (community_num, community_name) "
                "VALUES (:community_num, :community_name) "
                "ON CONFLICT (community_num) DO NOTHING", communities)
        _insert(conn, "INSERT INTO fact_coverage (community_num, population, "
                "accessible_population, geographic_coverage) VALUES "
                "(:community_num, :population, :accessible_population, "
                ":geographic_coverage) ON CONFLICT (community_num) DO NOTHING",
                communities)
        _insert(conn, "INSERT INTO fact_passengers_monthly (stop_id, month, "
                "direction, count, placeholder) VALUES (:stop_id, :month, "
                ":direction, :count, :placeholder) "
                "ON CONFLICT (stop_id, month, direction) DO NOTHING", kept)

    print(f"loaded: {len(stops)} stops, {len(communities)} communities, "
          f"{len(routes)} routes, {len(kept)} passenger rows")


if __name__ == "__main__":
    from app.db import engine

    load(engine(), os.environ.get("DATA_DIR", "/data"))
