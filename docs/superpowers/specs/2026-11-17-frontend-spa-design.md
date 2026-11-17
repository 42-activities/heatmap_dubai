# Design — Dubai Bus Analytics Full-Stack App

Date: 2026-11-17
Status: approved (2026-11-17) — build the whole stack; owner hosts db+api on their own VPS (include deploy config + notes, no managed cloud provisioning).

## Intent & why

Turn the project into a **proper full-stack web app**: a React frontend, a
backend API, and a **PostgreSQL database in its own container**, orchestrated
with Docker Compose. The owner wants a real website with a real backend, not a
static page. The database is populated now from the **STG reference data we
already have** (stops, communities, routes, coverage) plus the placeholder
monthly-2026 passengers; it becomes fuller when PROD ridership access lands.

## Architecture

```
[ React + Vite SPA ]  --/api-->  [ FastAPI ]  --SQL-->  [ PostgreSQL ]
   served by nginx                  (api)                   (db)
        |                              ^
   (same origin; nginx                | loader (one-shot): seeds schema + data
    reverse-proxies /api)             |   from web/data/*.json (or a fresh DDA export)
```

Four services in `docker-compose.yml`: **db** (Postgres), **api** (FastAPI),
**frontend** (nginx serving the built SPA + reverse-proxying `/api` to the api
service), and a one-shot **loader** that creates the schema and seeds data.

## Goals

- **db** — PostgreSQL 16 container, named volume for persistence. Star-ish
  schema: `dim_stop`, `dim_community`, `dim_route`, `fact_coverage`,
  `fact_passengers_monthly` (placeholder, flagged), with surrogate keys generated
  at load.
- **api** — FastAPI (Python) container reading Postgres: `/stops`,
  `/communities`, `/routes`, `/coverage`, `/passengers?month=&direction=`,
  `/kpis`, `/communities.geojson`, `/health`; pagination + CORS; Pydantic models.
- **loader** — one-shot: applies schema (`sql/`), loads from the committed
  `web/data/*.json` (+ `communities.geojson`), so the stack runs with **no API
  credentials**. A `make refresh` path can re-run the DDA export to update the
  JSON first.
- **frontend** — React 18 + Vite + TS SPA, react-router, **Recharts**,
  **react-leaflet**, built static and served by **nginx**. Views: **Overview**
  (KPI tiles + charts), **Heatmap** (network + placeholder passengers w/ SAMPLE
  badge + coverage choropleth), **Explorer** (searchable/sortable tables: stops,
  communities, routes), **Data & methodology**.
- **Data-source switch** — one `API_BASE` constant: `/api` for the Docker stack,
  or a static `data/` path for the GitHub Pages demo. The same frontend builds
  both ways.
- `docker compose up` brings the whole stack up locally; a `Makefile` wraps
  common commands.

## Non-goals

- No PROD ridership data (placeholder passengers remain, SAMPLE-flagged end to
  end). The stack targets the **owner's own VPS**: include a production compose
  override + nginx config + env template + a deploy README, but no managed-cloud
  provisioning, TLS automation, or CI/CD-to-server is set up here.
- No auth/users, no write endpoints (read-only analytics API), no ORM migrations
  framework beyond plain `sql/` scripts for now.
- The public GitHub Pages demo stays the **static** build — Pages cannot run db/api.

## Anti-goals

- Secrets in the frontend or in git (db credentials via env/`.env`, git-ignored).
- Presenting placeholder passengers as real anywhere (API marks them; UI badges).
- Breaking the existing live static heatmap while the new app is built.

## Constraints

- Reuse `web/data/*.json` as the seed source; **add a `routes.json` export**
  (`scripts/export_web_data.py` → distinct routes from `rta_bus_routes-open-api`).
- Postgres creds from env (`.env`, git-ignored); never committed.
- Frontend for Pages needs Vite `base: '/heatmap_dubai/'`; the Docker/nginx build
  uses base `/`. Build-time env selects base + `API_BASE`.
- New top-level dirs: `frontend/`, `api/`, `db/` (or `sql/`), `docker-compose.yml`,
  `Makefile`. The old vanilla `web/` stays (classic map + Pages seed data).

## Approaches considered

- **A — Full Docker stack: React + FastAPI + Postgres (CHOSEN).** nginx serves
  the SPA and proxies `/api`; loader seeds Postgres from the exported JSON.
  Matches the original plan's production shape; DB usable now with STG data.
  Trades off: much larger surface (3 services + loader + compose) than a static
  SPA, and the DB-backed version isn't free-hostable like Pages.
- **B — Static React SPA, JSON-fed, no backend.** Smaller, deploys free to Pages;
  rejected as the primary target because the owner explicitly wants a database
  container. (Kept as the Pages build mode via the `API_BASE` switch.)
- **C — Backend + DB but no container for the DB (SQLite/file).** Simpler, but
  the owner specifically wants Postgres in a separate container; rejected.

Owner chose the **separate database container** → full stack (A).

## The how (decided)

- **Stack:** frontend React18 + Vite + TS (react-router, Recharts, react-leaflet,
  a light table approach); api FastAPI + SQLAlchemy Core/psycopg + Pydantic;
  db Postgres 16; nginx (frontend + `/api` proxy); Docker Compose.
- **Schema & load:** `sql/01_schema.sql` + a Python loader (`api/` or `scripts/`)
  that reads the JSON and inserts rows, generating surrogate keys; idempotent
  (truncate+load) so re-seeding is safe.
- **Passengers:** `fact_passengers_monthly` carries a `placeholder` boolean; the
  API echoes it; the UI shows the SAMPLE badge whenever it's true.
- **Dual build:** `VITE_API_BASE` + `VITE_BASE` env → Pages build (static JSON)
  vs Docker build (`/api`). CI (GitHub Actions) builds the Pages/static variant.
- **Docs:** root README + a `docker/README` on how to run the stack, env vars,
  and the STG→PROD data refresh.

## Left to the builder

- Visual identity/theme, exact KPI + chart set, table lib choice, API pagination
  shape, loader placement (api vs scripts), nginx config specifics, Makefile
  targets, and how the Pages static build consumes data (copied JSON vs a tiny
  pre-rendered `/api`-shaped JSON).
