# Backend: API + Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Dockerized read-only analytics backend — PostgreSQL seeded from the exported STG data, behind a FastAPI service — that the React frontend (Plan 2) will consume.

**Architecture:** A one-shot loader applies a SQL schema and seeds Postgres from `web/data/*.json` (+ `communities.geojson`), so the stack runs with no DDA credentials. FastAPI reads Postgres and exposes read-only JSON endpoints. `docker-compose.yml` runs `db`, the one-shot `loader`, and `api`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy Core + psycopg3, Pydantic v2, PostgreSQL 16, pytest, Docker Compose. (The existing `scripts/` stay stdlib-only; the new `api/` has its own pinned `requirements.txt`.)

**Spec:** `docs/superpowers/specs/2026-11-17-frontend-spa-design.md`

## Global Constraints

- Read-only API (no write/auth endpoints). CORS allows the frontend origin(s).
- DB credentials come from env (`.env`, git-ignored) — never committed; no secrets in code, logs, or images.
- Loader is **idempotent** (truncate + load) and seeds only from `web/data/*.json` + `communities.geojson` — no DDA API calls, no credentials.
- Placeholder passengers carry a `placeholder` boolean through DB → API; the API never presents them as real.
- Python deps pinned to exact versions in `api/requirements.txt`; tests are `pytest`.
- `docker compose up` brings up `db` → `loader` (runs once) → `api`; `api` waits for a healthy `db`.
- Surrogate keys are generated at load (`dim_*` tables); joins to source data are by natural keys (`stop_id`, `community_num`, `route_name`).

## Review Focus

- **Loader run twice** (re-seed): must not duplicate rows or hit PK/unique violations — truncate-then-load, verified by row counts equal after two runs. → Task 3.
- **Pagination bounds**: `limit`/`offset` out of range, zero, negative, or very large must clamp/validate, never 500. → Task 5.
- **Passenger query for a month with no rows** (e.g. a non-2026 month) → empty list + 200, not an error. → Task 5.
- **Community without a coverage row or without geometry** (community 301 has no polygon; one geojson feature may lack a coverage row) → endpoints handle the gap, no crash, null/neutral as appropriate. → Tasks 3 & 5.
- **api starts before db is ready** (compose race) → `db` healthcheck + `api` `depends_on: service_healthy`, and a short connection retry on startup; verified by a cold `compose up`. → Tasks 4 & 6.

---

### Task 1: Routes export (`routes.json`)

**Files:**
- Modify: `scripts/export_web_data.py`
- Test: `scripts/tests/test_export.py`

**Interfaces:**
- Consumes: `dda.fetch_records` (existing).
- Produces: `summarize_routes(records: list[dict]) -> list[dict]` → one row per distinct `route_name`: `{route_name, route_type, stop_count}` (stop_count = count of distinct `stop_number` or rows for that route). `main()` also fetches `rta/rta_bus_routes-open-api` and writes `web/data/routes.json`; `meta.json` counts gain `routes`.

- [ ] **Step 1: Write failing tests**
```python
def test_summarize_routes_dedupes_and_counts():
    rows = [
      {"route_name": "F22", "route_type": "EK", "stop_number": 1},
      {"route_name": "F22", "route_type": "EK", "stop_number": 2},
      {"route_name": "GE95B", "route_type": "EK", "stop_number": 1}]
    out = {r["route_name"]: r for r in export_web_data.summarize_routes(rows)}
    assert set(out) == {"F22", "GE95B"}
    assert out["F22"]["stop_count"] == 2 and out["F22"]["route_type"] == "EK"
```
- [ ] **Step 2: Run tests, verify they fail** — `cd scripts && python3 -m unittest discover -s tests -v` → FAIL
- [ ] **Step 3: Implement `summarize_routes` + wire into `main()`** (fetch routes with `total=200000`, pageSize 1000, `min_interval=1.05`; it's ~14.6k rows). Write `web/data/routes.json`; add `routes` to `meta.json` counts.
- [ ] **Step 4: Run unit tests → PASS**
- [ ] **Step 5: Regenerate routes only** — a short invocation that fetches just routes and writes `routes.json` (don't force a 15-min stops re-fetch; if `main()` always refetches everything, add a `--only routes` flag or a guard). Verify `web/data/routes.json` non-empty (~hundreds of routes) and valid JSON.
- [ ] **Step 6: Commit** — `git add scripts/export_web_data.py scripts/tests/test_export.py web/data/routes.json web/data/meta.json && git commit -m "feat: export distinct routes to routes.json"`

---

### Task 2: SQL schema + pure row-builders

**Files:**
- Create: `sql/01_schema.sql`, `api/app/__init__.py`, `api/app/rows.py`
- Test: `api/tests/test_rows.py`, `api/requirements.txt` (pytest pinned)

**Interfaces:**
- Produces pure functions (no DB) in `api/app/rows.py`:
  - `stop_rows(stops_json) -> list[dict]` → `dim_stop` rows `{stop_id, stop_name, lat, lon}`
  - `community_rows(coverage_json) -> list[dict]` → `dim_community` rows (all coverage fields, numerics coerced)
  - `route_rows(routes_json) -> list[dict]`
  - `passenger_rows(passengers_json) -> list[dict]` → `fact_passengers_monthly` rows `{stop_id, month, direction, count, placeholder}` (un-pivots the `{in,out}` per month into two rows)
- `sql/01_schema.sql` defines `dim_stop`, `dim_community`, `dim_route`, `fact_coverage`, `fact_passengers_monthly` (+ indexes); surrogate PKs `*_id serial`, natural keys unique.

- [ ] **Step 1: Write failing tests** for the four row-builders — assert shapes and the passenger un-pivot:
```python
def test_passenger_rows_unpivots_in_out():
    data = {"placeholder": True, "stations": {"5": [{"month":"2026-01","in":10,"out":3}]}}
    rows = rows_mod.passenger_rows(data)
    assert {"stop_id":5,"month":"2026-01","direction":"in","count":10,"placeholder":True} in rows
    assert any(r["direction"]=="out" and r["count"]==3 for r in rows)
```
- [ ] **Step 2: Run tests, verify fail** — `cd api && python3 -m pytest -q` (after `pip install -r requirements.txt`) → FAIL
- [ ] **Step 3: Write `sql/01_schema.sql`** and implement `api/app/rows.py` (coerce numerics like the exporter's `_num`; `stop_id`/`community_num` as int).
- [ ] **Step 4: Run tests → PASS**
- [ ] **Step 5: Commit** — `git add sql/ api/app/ api/tests/test_rows.py api/requirements.txt && git commit -m "feat: SQL schema + pure DB row-builders"`

---

### Task 3: Loader (apply schema + seed) + `db` compose service

**Files:**
- Create: `api/app/loader.py`, `api/app/db.py`, `docker-compose.yml` (db + loader services), `.env.example`
- Test: `api/tests/test_loader_integration.py`

**Interfaces:**
- Consumes: `api/app/rows.py` (Task 2), `sql/01_schema.sql`.
- Produces: `api/app/db.py` → `engine()` (SQLAlchemy Engine from env `DATABASE_URL`); `api/app/loader.py` → `load(engine, data_dir)` that applies the schema, truncates, and bulk-inserts all `dim_*`/`fact_*` from the JSON in `data_dir`; a `__main__` entry so the loader container runs it.

- [ ] **Step 1: Write a failing integration test** (`test_loader_integration.py`) that skips unless `DATABASE_URL` is set, loads a tiny fixture dir, then asserts row counts in each table, and asserts **running `load` twice yields identical counts** (idempotent).
- [ ] **Step 2: Run it** — `cd api && DATABASE_URL=... python3 -m pytest -q test_loader_integration.py` against a scratch Postgres (`docker compose up -d db`). Expected: FAIL (loader not implemented).
- [ ] **Step 3: Implement `db.py` + `loader.py`**; write `docker-compose.yml` with `db` (postgres:16, healthcheck, named volume, env creds) and a one-shot `loader` (builds the api image, runs `python -m app.loader`, `depends_on: db service_healthy`, mounts `web/data`). Add `.env.example` (`POSTGRES_*`, `DATABASE_URL`).
- [ ] **Step 4: Verify** — `docker compose up -d db`, then run the loader (`docker compose run --rm loader`); the integration test passes; `psql` shows expected counts (stops 4220, communities 227, routes ~N, passenger rows = stations×12×2).
- [ ] **Step 5: Commit** — `git add api/app/loader.py api/app/db.py docker-compose.yml .env.example api/tests/test_loader_integration.py && git commit -m "feat: idempotent Postgres loader + db compose service"`

---

### Task 4: FastAPI app + DB wiring + `/health`

**Files:**
- Create: `api/app/main.py`, `api/app/settings.py`, `api/Dockerfile`
- Modify: `docker-compose.yml` (add `api` service), `api/requirements.txt` (fastapi, uvicorn, sqlalchemy, psycopg pinned)
- Test: `api/tests/test_health.py`

**Interfaces:**
- Consumes: `api/app/db.py`.
- Produces: `app = FastAPI(...)` in `api/app/main.py` with CORS, a startup DB-connection retry, and `GET /health` → `{"status":"ok","db":true}` (db=false if unreachable, still 200). `settings.py` reads env (DATABASE_URL, CORS origins).

- [ ] **Step 1: Write failing test** — `TestClient(app).get("/health").status_code == 200` and body has `status`.
- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: Implement `main.py` (+ settings, Dockerfile)**; add `api` service to compose (`depends_on: db service_healthy`, env `DATABASE_URL`, port 8000, `uvicorn app.main:app`).
- [ ] **Step 4: Tests → PASS**; `docker compose up` cold-starts cleanly and `curl :8000/health` → ok.
- [ ] **Step 5: Commit** — `git add api/app/main.py api/app/settings.py api/Dockerfile docker-compose.yml api/requirements.txt api/tests/test_health.py && git commit -m "feat: FastAPI app + health + api compose service"`

---

### Task 5: Read endpoints + Pydantic models

**Files:**
- Create: `api/app/models.py`, `api/app/routers/datasets.py`
- Modify: `api/app/main.py` (include router)
- Test: `api/tests/test_endpoints.py`

**Interfaces:**
- Consumes: `api/app/db.py`, models.
- Produces endpoints (all read-only, JSON): `GET /stops`, `/communities`, `/routes` (paginated: `limit` default 100 ≤1000, `offset` ≥0, returns `{results, total}`); `/coverage`; `/passengers?month=YYYY-MM&direction=in|out` (→ per-stop counts, `placeholder` flag included); `/kpis` (totals + coverage avg/median + population sums); `/communities.geojson` (serves the stored geometry joined to coverage). Pydantic models for each.

- [ ] **Step 1: Write failing endpoint tests** (TestClient against the seeded test DB): `/stops?limit=5` returns 5 + a `total`; `/passengers?month=2099-01` returns an empty list + 200; `/kpis` returns expected keys; out-of-range `limit=0`/`limit=100000` is clamped/422 (pick one, assert it); `/communities.geojson` is a FeatureCollection.
- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: Implement models + router**; validate pagination params (clamp or 422 consistently — Review Focus); passengers month-filter returns empty (not error) when no rows; kpis computed in SQL.
- [ ] **Step 4: Tests → PASS**
- [ ] **Step 5: Commit** — `git add api/app/models.py api/app/routers/ api/app/main.py api/tests/test_endpoints.py && git commit -m "feat: read-only dataset + kpi + geojson endpoints"`

---

### Task 6: Compose polish, Makefile, docs, cold-start smoke

**Files:**
- Create: `Makefile`, `api/README.md`
- Modify: `docker-compose.yml` (final wiring), root `README.md`, `TODO.md`, `.gitignore` (ensure `.env` ignored — it is)

**Interfaces:** consumes the finished services.

- [ ] **Step 1:** `Makefile` targets: `up`, `down`, `logs`, `seed` (re-run loader), `test` (unit + integration against compose db), `refresh` (re-run the DDA export to update `web/data`, then `seed`).
- [ ] **Step 2:** Finalize `docker-compose.yml` ordering (`db` healthy → `loader` once → `api`); add a `docker-compose.prod.yml` override for the owner's VPS (no host port-publish for `db`, restart policies, `api` behind the frontend later); `api/README.md` documents env vars, endpoints, `make` targets, the STG→PROD refresh, and a short **VPS deploy** section (`.env` from `.env.example`, `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`).
- [ ] **Step 3:** Update root `README.md` (new backend section + architecture) and tick `TODO.md` Phase-2/4 items the API satisfies.
- [ ] **Step 4: Cold-start smoke** — from a clean state (`docker compose down -v`), `docker compose up`: `db` seeds, `api` serves; `curl` `/health`, `/stops?limit=3`, `/kpis`, `/passengers?month=2026-06&direction=in`, `/communities.geojson` all 200 with sane bodies. Record outputs.
- [ ] **Step 5: Commit** — `git add Makefile api/README.md docker-compose.yml README.md TODO.md && git commit -m "chore: compose wiring, Makefile, backend docs"`
