#!/usr/bin/env python3
"""Fetch a token, then probe the open dataset endpoints and print one record.

Confirms (or corrects) the assumed bus dataset identifiers and reveals the
real field names, which the PDFs never documented. Stdlib only.

Usage:
    python3 scripts/test_dataset.py                      # probe default guesses
    python3 scripts/test_dataset.py rta/some_dataset ... # probe explicit paths
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from dda import TIMEOUT_SECONDS, fetch_token, get_config, mask

# Entity/dataset guesses carried over from the plan (unverified in the PDFs).
DEFAULT_TARGETS = [
    "rta/rta_bus_routes-open-api",
    "rta/rta_bus_stop_details-open-api",
    "rta/rta_bus_ridership-open-api",
]


def probe(base_url: str, path: str, token: str) -> None:
    url = f"{base_url}/open/{path}?" + urllib.parse.urlencode({"limit": 1})
    print("=" * 66)
    print(f"GET {url}")
    req = urllib.request.Request(
        url, method="GET", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status, payload = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status, payload = exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        print(f"  NETWORK ERROR: {exc.reason}")
        return

    print(f"  HTTP status: {status}")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("  Non-JSON response:")
        print("  " + payload[:800])
        return

    results = data.get("results") if isinstance(data, dict) else None
    if isinstance(results, list) and results:
        record = results[0]
        print(f"  records returned: {len(results)}")
        print(f"  FIELD NAMES: {list(record.keys())}")
        print("  SAMPLE RECORD:")
        print("    " + json.dumps(record, indent=2).replace("\n", "\n    "))
    else:
        # 404s here tend to echo the correct dataset/entity naming.
        print("  Response body:")
        print("    " + json.dumps(data, indent=2)[:1200].replace("\n", "\n    "))


def main() -> int:
    try:
        cfg = get_config()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    if not (cfg.security_id and cfg.client_id and cfg.client_secret):
        print("ERROR: missing SECURITY_APPLICATION_ID / CLIENT_ID / CLIENT_SECRET")
        return 2

    print(f"Environment: {cfg.environment}  base={cfg.base_url}")
    print(f"Credentials: secId={mask(cfg.security_id)} clientId={mask(cfg.client_id)}")
    try:
        token = fetch_token(cfg)
    except Exception as exc:  # noqa: BLE001 - surface any token failure plainly
        print(f"TOKEN ERROR: {exc}")
        return 1
    print(f"Token      : acquired ({mask(token, keep=6)})")

    targets = sys.argv[1:] or DEFAULT_TARGETS
    for path in targets:
        probe(cfg.base_url, path.lstrip("/"), token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
