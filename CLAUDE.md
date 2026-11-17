# CLAUDE.md — working notes for this repo

Guidance for Claude Code (and humans) working in `heatmap_dubai`. Read this
before touching the API layer. It records facts **verified against the live DDA
gateway**, because the vendor PDFs in `docs/api_docs/` are generic and contain
several inaccuracies.

## What this project is

Ingest Dubai RTA bus data (routes, stops, ridership) from the Dubai Data (DDA
iPaaS) open APIs and build a ridership **heatmap** + analytics. Greenfield:
only the auth/data layer is verified so far; see `TODO.md`.

## Credentials & environment

`.env` (project root, git-ignored) holds real secrets. Variables:

- `ENVIRONMENT` — `STG` or `PROD`; selects the base URL. **Do not** hardcode URLs.
- `SECURITY_APPLICATION_ID` → sent as the `x-DDA-SecurityApplicationIdentifier` header.
- `CLIENT_ID`, `CLIENT_SECRET` → token request body.
- `EMAIL`, `APPLICATION_ID` — present from portal registration, **not used** in any API call.

Never print, log, or commit secret values. Scripts mask them; keep it that way.
Reading `.env` with the Read tool / `cat` is blocked by permission settings —
load it in-process (Python) instead, as the scripts do.

## Verified API facts (live STG, 2026-11-17)

Base URLs: STG `https://stg-apis.data.dubai`, PROD `https://apis.data.dubai`.

**Token (STG, verified):** `POST {base}/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken`
- Headers: `Content-Type: application/json`, `x-DDA-SecurityApplicationIdentifier: <id>`
- Body: `{"grant_type":"client_credentials","client_id":"...","client_secret":"..."}`
- Returns `{access_token, token_type:"Bearer", expires_in:3600, scope:"authz"}`.
- Cache the token; refresh a little before 3600 s. `x-gateway-apikey` is **not** required.
- ⚠️ **Token URL differs by environment.** The PROD data portal documents
  `/secure/sdg/ssis/gatewayoauthtoken/1.0.0/getAccessToken`, which returns **403
  on STG**; only `dubaiai/gatewaytoken` works on STG. Derive the path per
  `ENVIRONMENT` and confirm the PROD path on first PROD call. (The portal also
  says "token valid ~30 min" generically — the live response is 3600 s; trust it.)

**Data:** `GET {base}/open/<entity>/<dataset>` with `Authorization: Bearer <token>`.
- Envelope: `{"results":[ ... ]}`.
- **Pagination: both `limit`/`offset` and `page`/`pageSize` work; default page
  size ~1000.** (Verified on routes. An earlier note calling `limit`/`offset`
  unreliable was wrong — it came from testing the 1-row ridership set.)
- Query params: `column` (comma-separated attribute allow-list), `filter`
  (supports `AND`/`OR`, e.g. `filter=col1=223 AND col2=2`), `page`, `pageSize`,
  `limit`, `offset`, `order_by`, `order_dir` (**underscores**).
- **Rate limit: 60 req/min. Timeout: 30 s.** Throttle ingestion accordingly.

## Datasets (entity = `rta`)

| Dataset | STG rows | Role |
|---|---|---|
| `rta_bus_routes-open-api` | 14,620 | route→stop **sequence** / bridge |
| `rta_bus_stop_details-open-api` | 20,000+ | stop master (coords, amenities, validity) |
| `rta_bus_ridership-open-api` | **1** | tap transactions — **real data only in PROD** |
| `rta_bus_network_coverage-open-api` | 227 | community-level bus accessibility |

Verified fields:

```
routes:    route_name, route_type, direction, stop_name, stop_number, load_timestamp
stops:     report_date, stop_name, stop_id, street_name, route_name,
           stop_location_longitude, stop_location_latitude, bus_stop_type,
           time_table_panel, mupi_available, rtpi_available,
           last_survey_date, valid_from, valid_until
ridership: txn_type, txn_date, txn_time, start_location, end_location,
           route_name, start_zone, end_zone, load_timestamp
coverage:  report_date, community_num (PK), community_name, community_area_size,
           makani_points, population, nume_of_bus_stops, accessible_population,
           geographic_coverage, load_timestamp
```

`coverage` is community-level (not per-stop): `geographic_coverage` is a %,
`accessible_population` = people within 400 m of a stop. Source updates weekly;
platform refresh is annual. Good for an **accessibility** heatmap by community.

## Gotchas (read before modeling data)

- **STG ridership has 1 row.** Any ridership profiling/join analysis must run on
  PROD. Don't conclude anything about txn codes, zones, or volume from STG.
- **`txn_type` is a code** (`CKA` observed), not `Check In`/`Check Out`. Enumerate
  the real set on PROD before writing validation/CHECK constraints.
- **No surrogate keys.** No `route_id`, no `stop_id` on routes, no
  `transaction_id`. Joins are by `route_name` and by location **strings** —
  expect messy matching. Synthesize surrogate keys at load time.
- **`routes` is already the route↔stop bridge** (`direction`, `stop_number`).
  A `dim_route` is just `route_name` + `route_type` (distinct).
- **Stop coordinates** are `stop_location_latitude` / `stop_location_longitude`
  (not `latitude`/`longitude`). There is **no `district`** — closest is `street_name`.
- **Stops are per-route rows** with `valid_from`/`valid_until`; dedup by `stop_id`
  (and respect validity) to build a clean `dim_stop`.
- **Heatmap join risk:** ridership `start_location`/`end_location` are free-text
  (e.g. `"Al Nahda 1, DEWA-1"`) and may not match `stop_name`. If coverage is
  low on PROD, aggregate the heatmap by **zone** instead of exact coordinates.

## Source-doc accuracy (PDFs + portal)

The PDFs in `docs/api_docs/` are generic DDA interface-control docs. Accurate:
OAuth flow, token response shape, 60 req/min + 30 s, base URLs, the
`/open/<entity>/<dataset>` pattern. **Absent:** they document no bus
dataset/schema at all (their sample data is trade-license records), so every bus
schema here comes from live responses or the data portal, not the PDFs.

Known conflicts, resolved by live testing:
- **Token URL:** PDFs say `/secure/ssis/dubaiai/gatewaytoken/...` (works on STG);
  the PROD portal says `/secure/sdg/ssis/gatewayoauthtoken/...` (403 on STG).
  Environment-specific — verify per environment, don't assume one is "wrong."
- **Sort params** are `order_by`/`order_dir` **with underscores** (PDF + portal
  agree); the original project plan wrote them without underscores.
- `txn_type` codes, zone ranges, and primary keys are **not** in the PDFs — the
  plan asserted them; confirm against live data.

Rule of thumb: **trust live responses first, then the portal page, then the PDFs.**

## Conventions

- Scripts live in `scripts/`, are **stdlib-only** so far, and import shared
  helpers from `test_token.py` / `test_dataset.py`. If adding dependencies,
  introduce `requirements.txt` and note it in the README.
- Respect the 60 req/min limit in anything that loops over pages.
- Keep raw API responses separate from any cleaned/derived data (raw → staging →
  curated) so reprocessing never needs to re-hit the API.

## Commands

```bash
cd scripts
python3 test_token.py          # auth smoke test
python3 test_dataset.py        # one record per dataset
python3 profile_ridership.py   # txn_type/zone profiling   (point ENVIRONMENT at PROD)
python3 join_coverage.py       # ridership↔stop join rate   (point ENVIRONMENT at PROD)
```
