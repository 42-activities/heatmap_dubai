#!/usr/bin/env python3
"""Measure how well ridership locations match bus-stop names.

Determines whether the heatmap can use precise stop coordinates (via a
name join) or must fall back to zone-level aggregation. Stdlib only.

Usage:
    python3 scripts/join_coverage.py [ridership_sample] [stops_sample]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from test_token import BASE_URLS, load_env, mask
from test_dataset import fetch_token

TIMEOUT_SECONDS = 30
PAGE_SIZE = 1000
RIDERSHIP = "rta/rta_bus_ridership-open-api"
STOPS = "rta/rta_bus_stop_details-open-api"


def fetch_records(base_url: str, path: str, token: str, total: int) -> list[dict]:
    # NOTE: both page/pageSize and limit/offset work on this gateway; default
    # page size is ~1000 (verified against STG routes, 2026-11-17).
    records: list[dict] = []
    page = 1
    while len(records) < total:
        want = min(PAGE_SIZE, total - len(records))
        url = f"{base_url}/open/{path}?" + urllib.parse.urlencode(
            {"page": page, "pageSize": want}
        )
        req = urllib.request.Request(
            url, method="GET", headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code} at page {page}")
            break
        batch = data.get("results") if isinstance(data, dict) else None
        if not batch:
            break
        records.extend(batch)
        page += 1
        if len(batch) < want:
            break
    return records


def norm(name: str) -> str:
    """Loose normalization for matching: lowercase, collapse non-alphanumerics."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def main() -> int:
    load_env(Path(__file__).resolve().parent.parent / ".env")
    environment = os.environ.get("ENVIRONMENT", "STG").upper()
    base_url = BASE_URLS[environment]
    sec = os.environ.get("SECURITY_APPLICATION_ID", "")
    cid = os.environ.get("CLIENT_ID", "")
    secret = os.environ.get("CLIENT_SECRET", "")

    rid_n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    stop_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10000

    token = fetch_token(base_url, sec, cid, secret)
    print(f"Token: acquired ({mask(token, keep=6)})")

    stops = fetch_records(base_url, STOPS, token, stop_n)
    rides = fetch_records(base_url, RIDERSHIP, token, rid_n)
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
