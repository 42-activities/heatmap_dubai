#!/usr/bin/env python3
"""Profile a sample of ridership rows: distinct codes, zones, null counts.

Pins down the real validation rules the PDFs never documented — especially
the txn_type code set and the zone value range. Stdlib only.

Usage:
    python3 scripts/profile_ridership.py [sample_size]   # default 5000
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from test_token import BASE_URLS, load_env, mask
from test_dataset import fetch_token

TIMEOUT_SECONDS = 30
PAGE_SIZE = 1000
DATASET = "rta/rta_bus_ridership-open-api"


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
            print(f"  HTTP {exc.code} at page {page}: {exc.read()[:300]!r}")
            break
        batch = data.get("results") if isinstance(data, dict) else None
        if not batch:
            break
        records.extend(batch)
        page += 1
        if len(batch) < want:  # no more rows available
            break
    return records


def show_counter(label: str, counter: Counter, top: int = 20) -> None:
    print(f"\n{label} ({len(counter)} distinct):")
    for value, count in counter.most_common(top):
        print(f"  {value!r:40} {count}")
    if len(counter) > top:
        print(f"  ... and {len(counter) - top} more")


def main() -> int:
    load_env(Path(__file__).resolve().parent.parent / ".env")
    environment = os.environ.get("ENVIRONMENT", "STG").upper()
    base_url = BASE_URLS[environment]
    sec = os.environ.get("SECURITY_APPLICATION_ID", "")
    cid = os.environ.get("CLIENT_ID", "")
    secret = os.environ.get("CLIENT_SECRET", "")

    total = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Environment: {environment}  sample target: {total} rows")
    token = fetch_token(base_url, sec, cid, secret)
    print(f"Token      : acquired ({mask(token, keep=6)})")

    rows = fetch_records(base_url, DATASET, token, total)
    print(f"\nRows retrieved: {len(rows)}")
    if not rows:
        return 1

    fields = list(rows[0].keys())
    print(f"Fields: {fields}")

    # Null / empty counts per field
    print("\nNull-or-empty counts per field:")
    for f in fields:
        empties = sum(1 for r in rows if r.get(f) in (None, "", "null"))
        print(f"  {f:28} {empties}/{len(rows)}")

    show_counter("txn_type values", Counter(r.get("txn_type") for r in rows))
    show_counter("start_zone values", Counter(r.get("start_zone") for r in rows))
    show_counter("end_zone values", Counter(r.get("end_zone") for r in rows))

    dates = [r.get("txn_date") for r in rows if r.get("txn_date")]
    if dates:
        print(f"\ntxn_date range: {min(dates)} .. {max(dates)}")

    routes = Counter(r.get("route_name") for r in rows)
    print(f"\ndistinct route_name in sample: {len(routes)}")
    print(f"top routes: {routes.most_common(5)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
