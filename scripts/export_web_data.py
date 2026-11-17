"""Export DDA data to static JSON for the website (web/data/).

Reference datasets (stops/coverage/routes) come from whichever environment the
credentials target. Passenger data is placeholder by default; `--passengers real`
aggregates the ridership dataset into per-station monthly in/out totals (needs a
PROD grant for `rta_bus_ridership-open-api` — STG has only a sample row).
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dda  # noqa: E402

STOPS_PATH = "rta/rta_bus_stop_details-open-api"
COVERAGE_PATH = "rta/rta_bus_network_coverage-open-api"
ROUTES_PATH = "rta/rta_bus_routes-open-api"
RIDERSHIP_PATH = "rta/rta_bus_ridership-open-api"
STOPS_TOTAL_CAP = 500000
SECTIONS = ("stops", "coverage", "routes", "passengers")
OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "data"

# txn_type code -> travel direction. Only 'CKA' is seen in STG's single sample
# row (assumed a check-in / boarding); the check-out code is a convention guess.
# VERIFY on PROD with scripts/profile_ridership.py and update this map before
# trusting the numbers — aggregate_ridership reports any unmapped codes it meets.
TXN_TYPE_DIRECTION = {"CKA": "in", "CKO": "out"}


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


def _norm_name(s):
    """Loose normalization for matching location names to stop names."""
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def aggregate_ridership(records, year=2026, type_direction=TXN_TYPE_DIRECTION):
    """Aggregate ridership transactions into per-location monthly in/out totals.

    Each row is one tap: a check-in (``in``) counts at ``start_location`` and a
    check-out (``out``) at ``end_location``, by ``txn_type``. Only rows whose
    ``txn_date`` falls in ``year`` are counted. ``records`` may be a generator
    (single pass). Returns ``(agg, report)`` where
    ``agg = {location: {'YYYY-MM': {'in': n, 'out': n}}}``.
    """
    agg = {}
    types, unmapped = Counter(), Counter()
    total_rows = year_rows = 0
    prefix = f"{year}-"
    for r in records:
        total_rows += 1
        txn_type = r.get("txn_type")
        types[txn_type] += 1
        date = str(r.get("txn_date") or "")
        if not date.startswith(prefix):
            continue
        year_rows += 1
        direction = type_direction.get(txn_type)
        if direction is None:
            unmapped[txn_type] += 1
            continue
        loc = r.get("start_location") if direction == "in" else r.get("end_location")
        if not loc:
            continue
        slot = agg.setdefault(loc, {}).setdefault(date[:7], {"in": 0, "out": 0})
        slot[direction] += 1
    report = {"rows": total_rows, "year_rows": year_rows,
              "txn_types": dict(types), "unmapped_types": dict(unmapped)}
    return agg, report


def passengers_from_agg(agg, stops, year=2026):
    """Key a per-location aggregate by stop_id (via stop-name matching) and emit
    the passengers payload shape, with all 12 months per matched station.
    Returns ``(payload, report)``."""
    by_norm = {}
    for s in stops:
        by_norm.setdefault(_norm_name(s.get("stop_name")), s.get("stop_id"))
    per_stop, matched, unmatched = {}, 0, 0
    for loc, months in agg.items():
        sid = by_norm.get(_norm_name(loc))
        if sid is None:
            unmatched += 1
            continue
        matched += 1
        dst = per_stop.setdefault(sid, {})
        for month, io in months.items():
            d = dst.setdefault(month, {"in": 0, "out": 0})
            d["in"] += io["in"]
            d["out"] += io["out"]
    labels = [f"{year}-{m:02d}" for m in range(1, 13)]
    stations = {
        str(sid): [{"month": m, "in": md.get(m, {}).get("in", 0),
                    "out": md.get(m, {}).get("out", 0)} for m in labels]
        for sid, md in per_stop.items()
    }
    payload = {"placeholder": False, "year": year, "stations": stations}
    report = {"locations": len(agg), "matched_locations": matched,
              "unmatched_locations": unmatched, "stations": len(stations)}
    return payload, report


def stream_ridership(get_json, page_size=1000, min_interval=1.05, columns=None, max_pages=100000):
    """Yield ridership rows page by page (so millions of rows aren't held in
    memory), throttled to respect the rate limit. ``columns`` limits the fetched
    fields to cut payload."""
    base = {"column": ",".join(columns)} if columns else {}
    last = 0.0
    for page in range(1, max_pages + 1):
        if min_interval and page > 1:
            wait = min_interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        last = time.monotonic()
        batch = (get_json(RIDERSHIP_PATH, {**base, "page": page, "pageSize": page_size})
                 or {}).get("results") or []
        yield from batch
        if len(batch) < page_size:
            return


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
    # stop_count is the number of source rows for a route (route-stop sequence
    # entries across directions), NOT the number of distinct stops.
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
    return sorted(routes.values(), key=lambda r: r["route_name"])


def parse_only(value):
    if not value:
        return set(SECTIONS)
    parts = {p.strip() for p in value.split(",") if p.strip()}
    bad = parts - set(SECTIONS)
    if bad:
        raise ValueError(f"unknown --only section(s): {sorted(bad)}")
    return parts


def _load_stops():
    sp = OUT_DIR / "stops.json"
    if not sp.exists():
        raise SystemExit("passengers needs web/data/stops.json — run the 'stops' section first")
    return json.loads(sp.read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma list of: " + ",".join(SECTIONS) + " (default all)")
    ap.add_argument("--passengers", choices=("placeholder", "real"), default="placeholder",
                    help="passenger source: 'placeholder' (SAMPLE, default) or 'real' "
                         "(aggregate ridership into monthly in/out per station)")
    args = ap.parse_args(argv)
    try:
        only = parse_only(args.only)
    except ValueError as e:
        ap.error(str(e))
    cfg = dda.get_config()
    token = dda.fetch_token(cfg)
    get_json = dda.make_getter(cfg.base_url, token)
    meta_path = OUT_DIR / "meta.json"
    counts, placeholder_flag = {}, True
    if only != set(SECTIONS) and meta_path.exists():
        prev = json.loads(meta_path.read_text(encoding="utf-8"))
        counts = prev.get("counts", {})
        placeholder_flag = prev.get("placeholder", {}).get("passengers", True)
    msg, stops = [], None
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
        write_json(OUT_DIR, "stops.json", stops)
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
    if "passengers" in only:
        if stops is None:
            stops = _load_stops()
        if args.passengers == "real":
            agg, agg_report = aggregate_ridership(stream_ridership(
                get_json, columns=["txn_type", "txn_date", "start_location", "end_location"]))
            payload, match_report = passengers_from_agg(agg, stops)
            print(f"ridership {agg_report}")
            print(f"station match {match_report}")
            if payload["stations"]:
                placeholder_flag = False
            else:
                payload = build_placeholder_passengers(stops)
                placeholder_flag = True
                print("no real 2026 ridership reached -> wrote labeled placeholder passengers")
        else:
            payload = build_placeholder_passengers(stops)
            placeholder_flag = True
        write_json(OUT_DIR, "passengers.json", payload)
        counts["passenger_stations"] = len(payload["stations"])
        msg.append(f"passenger stations={len(payload['stations'])} placeholder={placeholder_flag}")
    write_json(OUT_DIR, "meta.json", {
        "environment": cfg.environment,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": counts,
        "placeholder": {"passengers": placeholder_flag},
    })
    print(" ".join(msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
