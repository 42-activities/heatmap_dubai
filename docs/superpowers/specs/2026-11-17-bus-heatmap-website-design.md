# Design — Dubai Bus Heatmap Website

Date: 2026-11-17
Status: approved (2026-11-17)

## Intent & why

A shareable web **heatmap** of the Dubai bus network. For each bus station it
shows (1) monthly passengers boarding and alighting and (2) the population
density around it, over a real map of Dubai. Purpose stated by the owner:
"preparation" — a working, shareable skeleton built now from the data we can
reach (STG), honest about what is real vs. placeholder, that becomes fully real
by swapping a data file once PROD ridership access is granted.

## Goals

- A single, self-contained web page that renders a Leaflet map of Dubai with
  toggleable heat layers.
- **Layer 1 — Network (real):** all unique bus stops plotted from real STG
  coordinates; a density heat layer of the physical network.
- **Layer 2 — Passengers in/out (placeholder, labeled):** per-station
  **monthly** boardings and alightings for **2026** (one total in + one total
  out per calendar month, Jan–Dec 2026), driven by a data file. The UI has a
  **month selector** (Jan–Dec 2026) and an in/out toggle. Values are
  clearly-labeled sample data until PROD ridership exists; the UI carries a
  visible "SAMPLE DATA" badge whenever a placeholder layer is active.
- **Layer 3 — Population / accessibility (real numbers):** community population,
  `accessible_population`, and `geographic_coverage` from the Bus Network
  Coverage dataset, shown on the map where boundaries can be sourced.
- A Python export step that pulls STG data and writes the static JSON the page
  loads. Re-pointing it at PROD (via `ENVIRONMENT`) is the only change needed
  for real passenger data later.

## Non-goals

- No live API calls from the browser (no secrets in the page). The page loads
  pre-exported static JSON only.
- No backend/server, database, or warehouse for this deliverable (those remain
  in TODO.md Phases 2–4).
- No real passenger numbers yet (STG ridership has 1 row; PROD not available).
- Not a routing/journey planner; stations and aggregates only.

## Anti-goals (what would make this a failure)

- Placeholder data that looks real / isn't labeled — would mislead a viewer.
- Secrets or `.env` values shipped into the page or committed.
- A page that only works with a live token (it must open from static files).

## Constraints

- **Data reality:** passengers in/out = ridership dataset (PROD only; free-text
  `start_location`/`end_location`, not stop IDs → station matching unproven).
  Population = coverage dataset at **community** level, **no coordinates**.
- **Community geometry is not guaranteed.** `dm_community-open` (Dubai Pulse)
  exists but format/access is unconfirmed (sectors parent is KML; may need an
  access key or KML→GeoJSON conversion).
- Stop coordinates are real and plentiful (STG, 20k+ rows; dedupe by `stop_id`).
  A separate GIS dataset `rta_bus_stops_gis-open-api` (KML geometry) exists but
  **404s on STG** (likely PROD-only) — optional future enhancement, not relied on;
  stop-details lat/long is the coordinate source.
- API limits for the export: 60 req/min, 30 s timeout, `page`/`pageSize`
  pagination (see CLAUDE.md).

## Approaches considered

- **A — Shareable static heatmap now (CHOSEN).** Python export of real STG data
  (stops + coverage) → static JSON; self-contained Leaflet page with the three
  layers; passenger layer fed by labeled placeholder values. Trades off: real
  passenger numbers wait for PROD, but the whole UI exists now and goes real via
  one file swap.
- **B — Full local pipeline + served app.** Faithful to the TODO architecture,
  version-controlled end-to-end; slower, not instantly shareable, same
  placeholder caveat. Deferred to later phases.
- **C — Data layer only, no UI until PROD.** No throwaway work, but nothing to
  see; rejected — defeats the "preparation / something shareable" goal.

Owner picked **A**, with the passenger layer shown as **labeled placeholder
values**.

## The how (decided)

- **Deliverable:** `web/index.html` in the repo — a self-contained page that
  opens locally (full map-tile access). Also published as a shareable Artifact;
  if the Artifact sandbox blocks external map tiles, fall back to a tile-free
  styled basemap (Dubai outline GeoJSON + heat), noted as a build detail.
- **Libraries (CDN, pinned):** Leaflet + Leaflet.heat for the map/heat layers,
  loaded from cdnjs. No build tooling; plain HTML/CSS/JS.
- **Export script:** `scripts/export_web_data.py` (extends existing stdlib
  scripts). Reads `.env`, pulls stops + coverage from the env in `ENVIRONMENT`,
  dedupes stops by `stop_id`, writes `web/data/*.json`. Never writes secrets.
- **Placeholder convention:** placeholder records carry `"placeholder": true`;
  values are deterministic (seeded) so they're stable across runs; the UI shows
  a persistent "SAMPLE DATA" badge while any placeholder layer is on.
- **Layers & interaction:** layer toggle (Network / Passengers in / Passengers
  out / Population); per-station tooltip (name, coords, placeholder passengers);
  community tooltip (real population / accessible_population / coverage %).
- **Population placement:** join coverage to a Dubai community-boundaries GeoJSON
  by `community_num`/name and render a choropleth. **Fallback** if boundaries
  can't be sourced cleanly: show population as labeled placeholder-positioned
  markers + a ranked side panel, same "SAMPLE" labeling rule.
- **Passenger data shape:** `passengers.json` keyed by station → 12 months of
  `{month: "2026-MM", in: N, out: N}`. Placeholder generates all 12 months ×
  in/out per station deterministically. The future PROD aggregation filters
  ridership `txn_date` to 2026, groups by (matched station, month, direction),
  counting check-ins as `in` and check-outs as `out` (txn_type code→direction
  map resolved once PROD codes are enumerated; only `CKA` seen so far).
- **Env:** export runs against STG now; `ENVIRONMENT=PROD` + the ridership
  aggregation above replaces the placeholder file later. Color ramps follow the
  `dataviz` skill at build time.

## Left to the builder

- Page layout, styling, and exact color ramps (apply `dataviz` / `artifact-design`).
- Basemap/tile choice and the Artifact-CSP tile fallback.
- Stop dedupe details and the placeholder value distribution (plausible ranges).
- Whether population ships as real choropleth or labeled fallback, decided by
  what community geometry can actually be obtained during the build.
