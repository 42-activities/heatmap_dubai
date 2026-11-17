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
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from test_token import BASE_URLS, TOKEN_PATH, load_env, mask

TIMEOUT_SECONDS = 30

# Entity/dataset guesses carried over from the plan (unverified in the PDFs).
DEFAULT_TARGETS = [
    "rta/rta_bus_routes-open-api",
    "rta/rta_bus_stop_details-open-api",
    "rta/rta_bus_ridership-open-api",
]


def fetch_token(base_url: str, security_id: str, client_id: str, client_secret: str) -> str:
    body = json.dumps(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base_url + TOKEN_PATH,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-DDA-SecurityApplicationIdentifier": security_id,
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"no access_token in response: {data}")
    return token


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
    load_env(Path(__file__).resolve().parent.parent / ".env")
    environment = os.environ.get("ENVIRONMENT", "STG").upper()
    base_url = BASE_URLS.get(environment)
    if base_url is None:
        print(f"ERROR: ENVIRONMENT={environment!r} is not STG or PROD")
        return 2

    security_id = os.environ.get("SECURITY_APPLICATION_ID", "")
    client_id = os.environ.get("CLIENT_ID", "")
    client_secret = os.environ.get("CLIENT_SECRET", "")
    if not (security_id and client_id and client_secret):
        print("ERROR: missing SECURITY_APPLICATION_ID / CLIENT_ID / CLIENT_SECRET")
        return 2

    print(f"Environment: {environment}  base={base_url}")
    print(f"Credentials: secId={mask(security_id)} clientId={mask(client_id)}")
    try:
        token = fetch_token(base_url, security_id, client_id, client_secret)
    except Exception as exc:  # noqa: BLE001 - surface any token failure plainly
        print(f"TOKEN ERROR: {exc}")
        return 1
    print(f"Token      : acquired ({mask(token, keep=6)})")

    targets = sys.argv[1:] or DEFAULT_TARGETS
    for path in targets:
        probe(base_url, path.lstrip("/"), token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
