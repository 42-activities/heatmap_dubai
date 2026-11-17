# Heatmap Dubai — Bus Network Analytics

A data platform that ingests Dubai RTA bus data (routes, stops, ridership, and
community coverage) from the **Dubai Data (DDA iPaaS) open APIs** and turns it
into a ridership/accessibility **heatmap** and supporting analytics — where
demand concentrates by stop and zone, when it peaks, how the network connects,
and which communities are well or poorly served.

> Status: early. Auth and all four source datasets are **verified against the
> live STG gateway** (2026-11-17), and a static **heatmap web app** is built
> (see [`web/`](./web/)) — network + community-coverage layers use real STG
> data; the monthly-2026 passenger layer is **placeholder** until PROD ridership
> access. The ingestion pipeline/warehouse are not built yet — see
> [`TODO.md`](./TODO.md). Working-notes and gotchas for contributors (human or
> AI) live in [`CLAUDE.md`](./CLAUDE.md).

## Data source

Dubai Data platform (DDA iPaaS). OAuth2 client-credentials token, then
Bearer-authenticated GET calls to open datasets. All facts below are confirmed
live, not just from the PDFs in `docs/api_docs/` (several PDF claims were wrong —
see `CLAUDE.md`).

| Environment | Base URL |
|---|---|
| STG | `https://stg-apis.data.dubai` |
| PROD | `https://apis.data.dubai` |

**Token (STG, verified):** `POST {base}/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken`
— header `x-DDA-SecurityApplicationIdentifier`, JSON body with `grant_type=client_credentials`, `client_id`, `client_secret`. Returns a Bearer token, `expires_in: 3600`.

> ⚠️ The **PROD** data portal documents a *different* token path —
> `/secure/sdg/ssis/gatewayoauthtoken/1.0.0/getAccessToken`. That path returns
> **403 on STG** (only `dubaiai/gatewaytoken` works there). Treat the token URL
> as environment-specific and verify both when PROD access is granted.

**Datasets:** `GET {base}/open/<entity>/<dataset>` with `Authorization: Bearer <token>`.
Response envelope is `{"results": [ ... ]}`.

| Dataset (entity `rta`) | Rows in STG | What it is |
|---|---|---|
| `rta_bus_routes-open-api` | 14,620 | Route → stop **sequence** (acts as the route/stop bridge) |
| `rta_bus_stop_details-open-api` | 20,000+ | Stop master: names, coordinates, amenities, validity |
| `rta_bus_ridership-open-api` | **1 (sample only)** | Tap transactions — real volume is in PROD |
| `rta_bus_network_coverage-open-api` | 227 | Community-level bus accessibility (coverage %, pop. within 400 m) |

**Pagination:** both `limit`/`offset` **and** `page`/`pageSize` work; default page
size is ~1000. (Earlier doubt about `limit`/`offset` was an artifact of testing the
1-row ridership set.) **Rate limit: 60 req/min. Timeout: 30 s.** `filter` supports
`AND`/`OR` (e.g. `?filter=col1=223 AND col2=2`); `column=a,b,c` limits attributes.

### Verified field schemas

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

- `txn_type` is a **code** (e.g. `CKA`), **not** `Check In`/`Check Out`. Full code
  set still to be enumerated against PROD.
- `start_zone`/`end_zone` are strings like `"Zone 5"`.
- There are **no surrogate keys** (`route_id`, `transaction_id`): routes/stops
  join to ridership by `route_name` / location **strings**.

## Setup

Requires Python 3.9+ (scripts are **stdlib-only** so far — no `pip install`
needed yet). Create a `.env` in the project root:

```env
ENVIRONMENT=STG                # STG or PROD
SECURITY_APPLICATION_ID=...    # -> x-DDA-SecurityApplicationIdentifier header
CLIENT_ID=...
CLIENT_SECRET=...
# EMAIL / APPLICATION_ID may exist from portal registration but are NOT used in API calls
```

`.env` holds real credentials — it is git-ignored and must never be committed.

## Scripts

Run from the `scripts/` directory (they import each other locally):

```bash
cd scripts
python3 test_token.py            # verify credentials + token URL
python3 test_dataset.py          # fetch 1 record per dataset (field discovery)
python3 profile_ridership.py     # distinct txn_type/zones + null counts  (run on PROD)
python3 join_coverage.py         # ridership-location ↔ stop-name match rate (run on PROD)
```

Secrets are masked in all script output; only HTTP status and (masked) token
previews are printed.

## Repository layout

```
heatmap_dubai/
├── README.md              # this file
├── CLAUDE.md              # working notes + verified API facts + gotchas
├── TODO.md                # phased roadmap
├── api/                   # FastAPI + Postgres loader (see api/README.md)
├── sql/                   # Postgres schema
├── docker-compose.yml     # db + loader + api (docker-compose.prod.yml = VPS override)
├── Makefile               # up/down/logs/seed/test/refresh
├── web/                   # Leaflet heatmap page + web/data/*.json (see web/README.md)
├── .env                   # credentials (git-ignored, not committed)
├── docs/
│   └── api_docs/          # DDA PDFs (generic ICDs; partially inaccurate — see CLAUDE.md)
└── scripts/               # stdlib-only verification/profiling scripts
    ├── dda.py             # shared auth/fetch helpers
    ├── export_web_data.py # builds web/data/
    ├── test_token.py
    ├── test_dataset.py
    ├── profile_ridership.py
    └── join_coverage.py
```

## Heatmap web app

A static Leaflet page in [`web/`](./web/) visualises the network: stop heat,
monthly-2026 passengers in/out (**placeholder** until PROD data), and a
population/coverage choropleth by community. Run it with
`cd web && python3 -m http.server 8000`; data regeneration, the STG→PROD swap
and attribution are in [`web/README.md`](./web/README.md).

**Live (GitHub Pages):** https://42-activities.github.io/heatmap_dubai/ — full map with basemap (the page needs OSM tiles, so it runs on Pages rather than inside a sandboxed Artifact).

## Backend (API + Postgres)

A read-only **FastAPI** service backed by **Postgres** serves the same data the
static page uses. Architecture: `React/Leaflet frontend -> FastAPI (:8000) -> Postgres`,
with a one-shot loader seeding Postgres from `web/data/*.json`.

```bash
cp .env.example .env && make up      # db -> loader -> api on :8000
curl localhost:8000/kpis
make test                            # isolated; never truncates the seeded db
```

Endpoints, env vars, `make` targets, the STG->PROD refresh and VPS deploy are in
[`api/README.md`](./api/README.md).

## Roadmap

See [`TODO.md`](./TODO.md). Short version: enumerate ridership codes on PROD →
build the ingestion + raw store → star-schema warehouse → heatmap dashboard.
