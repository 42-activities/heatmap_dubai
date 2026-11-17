"""Shared DDA iPaaS API client: config, OAuth token, paginated fetch.

Stdlib only. Secrets are never printed; use mask() for any display.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple
from pathlib import Path
from typing import Callable

TIMEOUT_SECONDS = 30  # documented request timeout (OpenAPI spec, p.8)

TOKEN_PATH = "/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken"
BASE_URLS = {
    "STG": "https://stg-apis.data.dubai",
    "PROD": "https://apis.data.dubai",
}

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

Config = namedtuple("Config", "environment base_url security_id client_id client_secret")


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


def get_config() -> Config:
    """Load .env (without overriding real env vars) and build a Config.

    Raises ValueError for an unknown ENVIRONMENT.
    """
    load_env(ENV_PATH)
    environment = os.environ.get("ENVIRONMENT", "STG").upper()
    base_url = BASE_URLS.get(environment)
    if base_url is None:
        raise ValueError(f"ENVIRONMENT={environment!r} is not STG or PROD")
    return Config(
        environment,
        base_url,
        os.environ.get("SECURITY_APPLICATION_ID", ""),
        os.environ.get("CLIENT_ID", ""),
        os.environ.get("CLIENT_SECRET", ""),
    )


def request_token(cfg: Config) -> tuple[int, str]:
    """POST client_credentials; return (HTTP status, raw body). HTTP errors
    are returned, not raised; network errors propagate."""
    body = json.dumps(
        {
            "grant_type": "client_credentials",
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        cfg.base_url + TOKEN_PATH,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-DDA-SecurityApplicationIdentifier": cfg.security_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def fetch_token(cfg: Config) -> str:
    status, payload = request_token(cfg)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON token response (HTTP {status})") from None
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise RuntimeError(f"no access_token in response (HTTP {status}): {data}")
    return token


def make_getter(base_url: str, token: str) -> Callable[[str, dict], dict]:
    """Return get_json(path, params) doing an authenticated GET of /open/<path>."""

    def get_json(path: str, params: dict) -> dict:
        url = f"{base_url}/open/{path.lstrip('/')}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, method="GET", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    return get_json


def fetch_records(
    get_json: Callable[[str, dict], dict],
    path: str,
    total: int,
    page_size: int = 1000,
    min_interval: float = 0.0,
) -> list[dict]:
    """Paginate via page/pageSize, concatenating `results`.

    Stops at `total` rows, on an empty page, on a short page, or on HTTP error
    (reported, partial rows returned).
    """
    records: list[dict] = []
    page = 1
    last_req = None
    while len(records) < total:
        if min_interval > 0 and last_req is not None:
            wait = min_interval - (time.monotonic() - last_req)
            if wait > 0:
                time.sleep(wait)
        last_req = time.monotonic()
        want = min(page_size, total - len(records))
        try:
            data = get_json(path, {"page": page, "pageSize": want})
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
