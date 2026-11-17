"""Pure functions: exported web/data JSON -> DB row dicts. No DB, no I/O."""


def _num(v):
    """Return float for numeric-like value, else None (blank/None/NaN/inf/bool)."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def _int0(v):
    f = _num(v)
    return 0 if f is None else int(f)


def _float0(v):
    f = _num(v)
    return 0.0 if f is None else f


def stop_rows(stops_json):
    return [
        {"stop_id": int(_num(s["stop_id"])), "stop_name": s.get("stop_name"),
         "lat": _num(s.get("lat")), "lon": _num(s.get("lon"))}
        for s in stops_json
    ]


def community_rows(coverage_json):
    return [
        {"community_num": int(_num(c["community_num"])),
         "community_name": c.get("community_name"),
         "population": _int0(c.get("population")),
         "accessible_population": _int0(c.get("accessible_population")),
         "geographic_coverage": _float0(c.get("geographic_coverage"))}
        for c in coverage_json
    ]


def route_rows(routes_json):
    return [
        {"route_name": r["route_name"], "route_type": r.get("route_type"),
         "stop_count": _int0(r.get("stop_count"))}
        for r in routes_json
    ]


def passenger_rows(passengers_json):
    placeholder = bool(passengers_json.get("placeholder", False))
    out = []
    for sid, months in passengers_json.get("stations", {}).items():
        stop_id = int(sid)
        for m in months:
            for direction in ("in", "out"):
                out.append({"stop_id": stop_id, "month": m["month"],
                            "direction": direction, "count": _int0(m.get(direction)),
                            "placeholder": placeholder})
    return out
