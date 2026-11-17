# Dubai Bus Heatmap (web)

A self-contained [Leaflet](https://leafletjs.com/) page that maps the Dubai RTA
bus network. It is static: `index.html` + `app.js` + `style.css` read
pre-exported JSON from `data/`.

## Layers

| Layer | Data | Status |
|---|---|---|
| Network | Heat of bus stops (`data/stops.json`, 4,220 unique stops) | **Real** (STG) |
| Passengers in/out | Monthly 2026 check-ins/outs per station (`data/passengers.json`) | **PLACEHOLDER** — shows a "SAMPLE DATA" badge |
| Population / coverage | Choropleth of `geographic_coverage` per community (`data/coverage.json` + `data/communities.geojson`) | **Real** (STG) |

The passengers layer is synthetic because the STG ridership dataset holds only
1 sample row; real volume exists only in PROD.

## Open locally

```bash
cd web
python3 -m http.server 8000
# then browse http://localhost:8000/
```

(Serve over HTTP; opening `index.html` via `file://` will block the JSON fetches.)

## Regenerate the data

From the repo root (needs a `.env`, see the root [`README.md`](../README.md)):

```bash
cd scripts && python3 export_web_data.py
```

This writes `web/data/{stops,coverage,passengers,meta}.json`. Expect **~15
minutes**: it pulls the full ~452k-row stops dataset and is throttled by the API
rate limit (60 req/min). `ENVIRONMENT` in `.env` selects STG or PROD.
`communities.geojson` is a static third-party file and is not regenerated.

## STG to PROD swap (making passengers real)

1. Obtain PROD credentials and set `ENVIRONMENT=PROD` in `.env`.
2. Re-run `python3 export_web_data.py`. `passengers.json` is then replaced by the
   real monthly-2026 aggregation of ridership check-ins/outs per matched
   station, and `meta.json` no longer flags `placeholder.passengers`, so the
   "SAMPLE DATA" badge goes away.
3. Verify the real `txn_type` codes (only `CKA` seen on STG) and the
   ridership-location to stop-name match rate before trusting the numbers.

## Data sources and attribution

- **Dubai Data (DDA iPaaS) open APIs, entity `rta`**: `rta_bus_stop_details-open-api`
  (stops), `rta_bus_network_coverage-open-api` (community coverage/population),
  `rta_bus_routes-open-api` and `rta_bus_ridership-open-api` (ridership, PROD
  only for real volume). Data (c) Roads and Transport Authority / Dubai Digital
  Authority, via Dubai Data.
- **`data/communities.geojson`**: Dubai community polygons (226 features),
  attributed to **Dubai Municipality / Dubai Pulse open data** (the boundaries
  match the `dm_community` administrative level). Obtained via a third-party
  GitHub mirror (`Krishna99008594/MapFiles`) that states **no license of its
  own**; the underlying Dubai Municipality open data carries an attribution
  requirement and "not specified" reuse terms (verified 2026-11-17). The map and
  this README credit the source accordingly. For commercial reuse, confirm terms
  with Dubai Municipality / Dubai Pulse directly, or substitute an
  explicitly-licensed boundary source (e.g. OpenStreetMap / ODbL).
- Basemap tiles and Leaflet are loaded from their public providers; respect
  their attribution requirements (shown on the map).
