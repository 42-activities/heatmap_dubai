#!/usr/bin/env python3
"""Minimal token-acquisition test against the DDA iPaaS OAuth gateway.

Reads credentials from the environment (falling back to the project .env),
POSTs a client_credentials request to the STG/PROD token endpoint documented
in docs/api_docs/, and reports the HTTP status and whether an access_token
came back. The token value itself is masked; secrets are never printed.

Stdlib only — no third-party dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT_SECONDS = 30  # documented request timeout (OpenAPI spec, p.8)

TOKEN_PATH = "/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken"
BASE_URLS = {
    "STG": "https://stg-apis.data.dubai",
    "PROD": "https://apis.data.dubai",
}


def load_env(path: Path) -> None:
    """Load KEY=VALUE lines from .env without overriding real env vars."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def mask(secret: str, keep: int = 4) -> str:
    if not secret:
        return "<empty>"
    if len(secret) <= keep:
        return "*" * len(secret)
    return secret[:keep] + "*" * (len(secret) - keep)


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

    missing = [
        name
        for name, val in (
            ("SECURITY_APPLICATION_ID", security_id),
            ("CLIENT_ID", client_id),
            ("CLIENT_SECRET", client_secret),
        )
        if not val
    ]
    if missing:
        print(f"ERROR: missing required variables: {', '.join(missing)}")
        return 2

    url = base_url + TOKEN_PATH
    print(f"Environment : {environment}")
    print(f"Token URL   : {url}")
    print(f"SecurityAppId : {mask(security_id)}")
    print(f"ClientId    : {mask(client_id)}")
    print(f"ClientSecret: {mask(client_secret)}")
    print("-" * 60)

    body = json.dumps(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-DDA-SecurityApplicationIdentifier": security_id,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status = resp.status
            payload = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"NETWORK ERROR: {exc.reason}")
        return 1
    except TimeoutError:
        print(f"TIMEOUT: no response within {TIMEOUT_SECONDS}s")
        return 1

    print(f"HTTP status : {status}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("Response (non-JSON):")
        print(payload[:1000])
        return 0 if status == 200 else 1

    token = data.get("access_token")
    if token:
        print("access_token: RECEIVED ->", mask(token, keep=6))
        print(f"token_type  : {data.get('token_type')}")
        print(f"expires_in  : {data.get('expires_in')}")
        print(f"scope       : {data.get('scope')}")
        print("\nRESULT: SUCCESS — credentials and token URL are valid.")
        return 0

    # No token: show the error body (safe — it holds no secret of ours)
    print("access_token: NOT PRESENT")
    print("Response body:")
    print(json.dumps(data, indent=2)[:1500])
    print("\nRESULT: FAILED — see response above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
