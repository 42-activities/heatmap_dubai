#!/usr/bin/env python3
"""Profile a sample of ridership rows: distinct codes, zones, null counts.

Pins down the real validation rules the PDFs never documented — especially
the txn_type code set and the zone value range. Stdlib only.

Usage:
    python3 scripts/profile_ridership.py [sample_size]   # default 5000
"""
from __future__ import annotations

import sys
from collections import Counter

import dda
from dda import fetch_token, get_config, mask

DATASET = "rta/rta_bus_ridership-open-api"


def show_counter(label: str, counter: Counter, top: int = 20) -> None:
    print(f"\n{label} ({len(counter)} distinct):")
    for value, count in counter.most_common(top):
        print(f"  {value!r:40} {count}")
    if len(counter) > top:
        print(f"  ... and {len(counter) - top} more")


def main() -> int:
    cfg = get_config()
    base_url = cfg.base_url

    total = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Environment: {cfg.environment}  sample target: {total} rows")
    token = fetch_token(cfg)
    print(f"Token      : acquired ({mask(token, keep=6)})")

    rows = dda.fetch_records(dda.make_getter(base_url, token), DATASET, total)
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
