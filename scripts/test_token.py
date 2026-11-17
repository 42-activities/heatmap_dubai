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
import sys
import urllib.error

from dda import TIMEOUT_SECONDS, TOKEN_PATH, get_config, mask, request_token

def main() -> int:
    try:
        cfg = get_config()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    missing = [
        name
        for name, val in (
            ("SECURITY_APPLICATION_ID", cfg.security_id),
            ("CLIENT_ID", cfg.client_id),
            ("CLIENT_SECRET", cfg.client_secret),
        )
        if not val
    ]
    if missing:
        print(f"ERROR: missing required variables: {', '.join(missing)}")
        return 2

    print(f"Environment : {cfg.environment}")
    print(f"Token URL   : {cfg.base_url + TOKEN_PATH}")
    print(f"SecurityAppId : {mask(cfg.security_id)}")
    print(f"ClientId    : {mask(cfg.client_id)}")
    print(f"ClientSecret: {mask(cfg.client_secret)}")
    print("-" * 60)

    try:
        status, payload = request_token(cfg)
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
