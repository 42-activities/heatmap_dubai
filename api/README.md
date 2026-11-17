# Heatmap Dubai API

Read-only FastAPI service over a Postgres star schema (`sql/01_schema.sql`).
Data is seeded from `web/data/*.json` by an idempotent loader; the API never writes.

```
web/data/*.json --(loader, one-shot)--> Postgres <--(read-only)-- FastAPI :8000 <-- React
```

## Quick start

```bash
cp .env.example .env     # then edit values
make up                  # db -> loader (seeds once) -> api on :8000
curl localhost:8000/health
```

## Environment variables (`.env`, git-ignored)

| Var | Used by | Meaning |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | db | Credentials + database name created on first start |
| `DATABASE_URL` | api, loader, tests | SQLAlchemy URL, e.g. `postgresql+psycopg://USER:PASS@db:5432/DBNAME` (host is `db` inside compose) |
| `CORS_ORIGINS` | api | Comma-separated allowed origins (default `*`; **required** in the prod override) |
| `DATA_DIR` | api, loader | Folder with `*.json` / `communities.geojson` (compose mounts `./web/data` at `/data`) |
| `SCHEMA_PATH` | loader | Path to `01_schema.sql` (compose mounts `./sql` at `/sql`) |
| `TEST_DATABASE_URL` | tests | Throwaway DB for the destructive loader test; set by `make test`, never equal to `DATABASE_URL` |

The DDA credentials (`ENVIRONMENT`, `SECURITY_APPLICATION_ID`, `CLIENT_ID`, `CLIENT_SECRET`) in `.env` are used only by `make refresh`.

## Endpoints (all GET, JSON)

List endpoints return `{"results": [...], "total": N}`; `limit`/`offset` where noted.

| Endpoint | Notes |
|---|---|
| `/health` | `{"status": "ok", "db": true}`; `db:false` if Postgres is unreachable |
| `/stops?limit=&offset=` | `stop_id, stop_name, lat, lon` |
| `/communities?limit=&offset=` | `community_num, community_name` |
| `/routes?limit=&offset=` | `route_name, route_type, stop_count` |
| `/coverage` | per-community population, accessible population, geographic coverage |
| `/passengers?month=YYYY-MM&direction=in\|out&limit=&offset=` | monthly counts per stop; `placeholder: true` until PROD ridership |
| `/kpis` | totals, coverage avg/median, population, `passengers_placeholder` |
| `/communities.geojson` | community polygons with coverage properties merged in |

```bash
curl 'localhost:8000/stops?limit=3'
curl 'localhost:8000/passengers?month=2026-06&direction=in&limit=5'
curl localhost:8000/kpis
curl localhost:8000/communities.geojson | head -c 300
```

Interactive docs: `http://localhost:8000/docs`.

## Make targets (run from the repo root)

| Target | What it does |
|---|---|
| `make up` | Build + start `db`, run `loader` once (seeds), start `api` |
| `make down` | Stop containers, keep the data volume (`docker compose down -v` wipes it) |
| `make logs` | Follow logs |
| `make seed` | Re-run the idempotent loader against the current `web/data` |
| `make test` | Run all tests in a container. The destructive loader test uses a throwaway `<POSTGRES_DB>_test` database (`TEST_DATABASE_URL`, dropped afterwards); read-only endpoint tests use the seeded `DATABASE_URL`, which is never truncated |
| `make refresh` | Re-run `scripts/export_web_data.py` (DDA fetch, rewrites `web/data`), then `make seed` |

## Data refresh (STG to PROD)

`scripts/export_web_data.py` reads `ENVIRONMENT` from `.env`:

1. Set `ENVIRONMENT=STG` (current) or `PROD` plus the matching credentials.
2. `make refresh` fetches stops/coverage/routes, rewrites `web/data/*.json`, and reloads Postgres.
3. Passenger data is a **placeholder** until PROD ridership access; `placeholder` flags in the API flip off once real data is loaded.

## VPS deploy

```bash
git clone <repo> && cd heatmap_dubai
cp .env.example .env     # set a strong POSTGRES_PASSWORD, matching DATABASE_URL, CORS_ORIGINS=https://your-frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The prod override: `db` has no published port (internal network only), `db`/`api`
use `restart: unless-stopped`, `api` binds `127.0.0.1:8000` (put Caddy/nginx in
front for TLS and the frontend), adds a healthcheck and log rotation, and
refuses to start without `CORS_ORIGINS`. Reseed with
`docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm loader`.
