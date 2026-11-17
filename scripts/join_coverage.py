#!/usr/bin/env python3
"""Measure how well ridership locations match bus-stop names.

Determines whether the heatmap can use precise stop coordinates (via a
name join) or must fall back to zone-level aggregation. Stdlib only.

Usage:
    python3 scripts/join_coverage.py [ridership_sample] [stops_sample]
"""
from __future__ import annotations

import re
import sys

import dda
from dda import fetch_token, get_config, mask

RIDERSHIP = "rta/rta_bus_ridership-open-api"
STOPS = "rta/rta_bus_stop_details-open-api"


def norm(name: str) -> str:
    """Loose normalization for matching: lowercase, collapse non-alphanumerics."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def main() -> int:
    cfg = get_config()
    base_url = cfg.base_url

    rid_n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    stop_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10000

    token = fetch_token(cfg)
    print(f"Token: acquired ({mask(token, keep=6)})")

    stops = dda.fetch_records(dda.make_getter(base_url, token), STOPS, stop_n)
    rides = dda.fetch_records(dda.make_getter(base_url, token), RIDERSHIP, rid_n)
    print(f"stops fetched: {len(stops)}   ridership fetched: {len(rides)}")
    if not stops or not rides:
        return 1

    exact_stop = {s.get("stop_name") for s in stops if s.get("stop_name")}
    norm_stop = {norm(s.get("stop_name")) for s in stops if s.get("stop_name")}

    rid_locs = set()
    for r in rides:
        for key in ("start_location", "end_location"):
            v = r.get(key)
            if v:
                rid_locs.add(v)

    exact_hits = sum(1 for loc in rid_locs if loc in exact_stop)
    norm_hits = sum(1 for loc in rid_locs if norm(loc) in norm_stop)

    print(f"\ndistinct ridership locations: {len(rid_locs)}")
    print(f"distinct stop names         : {len(exact_stop)}")
    print(
        f"exact-match coverage : {exact_hits}/{len(rid_locs)} "
        f"({100*exact_hits/len(rid_locs):.1f}%)"
    )
    print(
        f"normalized coverage  : {norm_hits}/{len(rid_locs)} "
        f"({100*norm_hits/len(rid_locs):.1f}%)"
    )

    unmatched = [loc for loc in sorted(rid_locs) if norm(loc) not in norm_stop]
    print(f"\nsample UNMATCHED ridership locations ({len(unmatched)} total):")
    for loc in unmatched[:15]:
        print(f"  {loc!r}")
    print("\nsample stop names for comparison:")
    for s in sorted(exact_stop)[:10]:
        print(f"  {s!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
