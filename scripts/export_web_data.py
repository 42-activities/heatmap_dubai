"""Export DDA STG data to static JSON for the website (web/data/)."""
import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dda  # noqa: E402

STOPS_PATH = "rta/rta_bus_stop_details-open-api"
COVERAGE_PATH = "rta/rta_bus_network_coverage-open-api"
ROUTES_PATH = "rta/rta_bus_routes-open-api"
STOPS_TOTAL_CAP = 500000
SECTIONS = ("stops", "coverage", "routes")
OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "data"


def _num(v):
    """Return float for numeric-like value, else None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def dedupe_stops(records):
    best = {}
    for r in records:
        lat = _num(r.get("stop_location_latitude"))
        lon = _num(r.get("stop_location_longitude"))
        sf = _num(r.get("stop_id"))
        if lat is None or lon is None or sf is None:
            continue
        if lat == 25.0 and lon == 55.0:  # source sentinel, not a real location
            continue
        sid = int(sf)
        vf = str(r.get("valid_from") or "")
        cur = best.get(sid)
        if cur is None or vf >= cur[0]:
            best[sid] = (vf, {"stop_id": sid, "stop_name": r.get("stop_name"),
                              "lat": lat, "lon": lon})
    return [v[1] for v in best.values()]


def build_placeholder_passengers(stops, year=2026, seed=20260101):
    stations = {}
    for s in stops:
        sid = s["stop_id"]
        try:
            base = int(sid)
        except (TypeError, ValueError):
            base = sum(ord(c) for c in str(sid))
        rng = random.Random(seed + base)
        scale = rng.randint(2000, 30000)
        months = []
        for m in range(1, 13):
            months.append({
                "month": f"{year}-{m:02d}",
                "in": min(50000, int(scale * rng.uniform(0.6, 1.4))),
                "out": min(50000, int(scale * rng.uniform(0.6, 1.4))),
            })
        stations[str(sid)] = months
    return {"placeholder": True, "year": year, "stations": stations}


def _int0(v):
    f = _num(v)
    return 0 if f is None else int(f)


def _float0(v):
    f = _num(v)
    return 0 if f is None else f


def summarize_coverage(records):
    return [{
        "community_num": r.get("community_num"),
        "community_name": r.get("community_name"),
        "population": _int0(r.get("population")),
        "accessible_population": _int0(r.get("accessible_population")),
        "geographic_coverage": _float0(r.get("geographic_coverage")),
    } for r in records]


def write_json(out_dir, name, obj):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False),
                    encoding="utf-8")
    return path


def summarize_routes(records):
    routes = {}
    for r in records:
        name = r.get("route_name")
        if name is None or name == "":
            continue
        cur = routes.get(name)
        if cur is None:
            routes[name] = {"route_name": name, "route_type": r.get("route_type"),
                            "stop_count": 1}
        else:
            cur["stop_count"] += 1
    return list(routes.values())


def parse_only(value):
    if not value:
        return set(SECTIONS)
    parts = {p.strip() for p in value.split(",") if p.strip()}
    bad = parts - set(SECTIONS)
    if bad:
        raise ValueError(f"unknown --only section(s): {sorted(bad)}")
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma list of: " + ",".join(SECTIONS) + " (default all)")
    try:
        only = parse_only(ap.parse_args(argv).only)
    except ValueError as e:
        ap.error(str(e))
    cfg = dda.get_config()
    token = dda.fetch_token(cfg)
    get_json = dda.make_getter(cfg.base_url, token)
    meta_path = OUT_DIR / "meta.json"
    counts = {}
    if only != set(SECTIONS) and meta_path.exists():
        counts = json.loads(meta_path.read_text(encoding="utf-8")).get("counts", {})
    msg = []
    if "stops" in only:
        # Probe the server's honored page size (fetch_records treats short pages as last).
        probe = get_json(STOPS_PATH, {"page": 1, "pageSize": 5000}).get("results") or []
        page_size = 5000 if len(probe) == 5000 else 1000
        print(f"probe returned {len(probe)} rows -> page_size={page_size}")
        raw_stops = dda.fetch_records(get_json, STOPS_PATH, total=STOPS_TOTAL_CAP,
                                      page_size=page_size, min_interval=1.05)
        if len(raw_stops) >= STOPS_TOTAL_CAP:
            raise RuntimeError("stops fetch hit the cap; data may be truncated")
        stops = dedupe_stops(raw_stops)
        passengers = build_placeholder_passengers(stops)
        write_json(OUT_DIR, "stops.json", stops)
        write_json(OUT_DIR, "passengers.json", passengers)
        counts["stops"] = len(stops)
        msg.append(f"raw stops={len(raw_stops)} stops={len(stops)}")
    if "coverage" in only:
        coverage = summarize_coverage(dda.fetch_records(get_json, COVERAGE_PATH, total=2000))
        write_json(OUT_DIR, "coverage.json", coverage)
        counts["coverage"] = len(coverage)
        msg.append(f"coverage={len(coverage)}")
    if "routes" in only:
        raw_routes = dda.fetch_records(get_json, ROUTES_PATH, total=200000,
                                       page_size=1000, min_interval=1.05)
        routes = summarize_routes(raw_routes)
        write_json(OUT_DIR, "routes.json", routes)
        counts["routes"] = len(routes)
        msg.append(f"raw routes={len(raw_routes)} routes={len(routes)}")
    write_json(OUT_DIR, "meta.json", {
        "environment": cfg.environment,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": counts,
        "placeholder": {"passengers": True},
    })
    print(" ".join(msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
