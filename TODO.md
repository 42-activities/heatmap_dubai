# TODO — Heatmap Dubai

Phased roadmap. Checked items are verified done; see `CLAUDE.md` for the facts
each step established.

## Phase 0 — API verification ✅ (done 2026-11-17)

- [x] Confirm token flow and working token URL on STG (`dubaiai/gatewaytoken`)
- [x] Confirm `.env` variable mapping (`SECURITY_APPLICATION_ID`, `CLIENT_ID`, `CLIENT_SECRET`)
- [x] Discover real schemas for routes, stops, ridership, coverage
- [x] Confirm pagination (`limit`/`offset` **and** `page`/`pageSize`), rate limit, timeout
- [x] Verify the `rta_bus_network_coverage-open-api` dataset (227 STG rows)
- [x] Scripts: `test_token.py`, `test_dataset.py`, `profile_ridership.py`, `join_coverage.py`

## Phase 1 — PROD access & data profiling ⏳ (blocked on PROD credentials)

- [ ] Obtain PROD API key/secret; confirm the PROD token URL
      (`/secure/sdg/ssis/gatewayoauthtoken/...` per portal — test it)
- [ ] Run `profile_ridership.py` on PROD → enumerate the real `txn_type` codes
      (only `CKA` seen so far) and the full `start_zone`/`end_zone` range
- [ ] Run `join_coverage.py` on PROD → measure ridership-location ↔ stop-name
      match rate; decide **coordinate-level vs zone-level** heatmap
- [ ] Record PROD row volumes and `txn_date` span per dataset
- [ ] Write `docs/data_dictionary.md` from verified fields (mark anything still unconfirmed)

## Phase 2 — Ingestion & raw store

- [ ] Token client: in-memory cache + refresh before `expires_in`, env-aware URL
- [ ] One paginated client per dataset; throttle to ≤60 req/min; 30 s timeout; retries w/ backoff
- [ ] Persist immutable raw responses (JSONL/Parquet) under `data/raw/` with
      ingestion metadata (endpoint, params, fetch time, row count, checksum)
- [ ] Reference datasets (routes, stops, coverage) refreshed on a slow cadence;
      ridership incrementally by `txn_date`
- [ ] CLI, e.g. `python -m src.main ingest --dataset ridership --date YYYY-MM-DD`

## Phase 3 — Validation & modeling

- [ ] Validate types, required fields, nulls; dedup stops by `stop_id` (respect `valid_from/until`)
- [ ] `txn_type` CHECK against the **real** enumerated codes (not `Check In`/`Check Out`)
- [ ] Referential checks: ridership `route_name` ∈ routes; location ↔ stop coverage
- [ ] Warehouse (PostgreSQL/DuckDB): `dim_route`, `dim_stop`, `dim_community`,
      `bridge_route_stop` (from the routes dataset), `fact_ridership` (synthetic key),
      `fact_coverage`. No vendor surrogate keys exist — generate them on load.

## Phase 4 — Analytics & heatmap

- [ ] Metrics: ridership by stop/zone/route/hour/day; zone-to-zone flows; peak hours
- [x] Accessibility metrics from coverage (geographic_coverage %, accessible_population)
- [x] **Heatmap** built (`web/`): network stop heat + community coverage
      choropleth + monthly-2026 passengers layer using **placeholder** data
      (swap to real ridership once PROD is available; coordinate- vs zone-level
      still depends on Phase 1)
- [x] Read-only FastAPI + Postgres backend serving stops, coverage, passengers, KPIs, GeoJSON (`api/`)
- [x] Dashboard: React SPA (`frontend/`) with map, explorer tables, charts, data page; nginx container + Pages deploy
- [ ] Data-quality panel / route-zone trend views

## Cross-cutting

- [x] Ensure `.env` is git-ignored (add `.gitignore` if missing) before any commit
- [ ] Separate raw / staging / curated so reprocessing never re-hits the API
- [ ] Log request metadata only — never secrets or full payloads
- [x] Add `requirements.txt` once a non-stdlib dependency is introduced
