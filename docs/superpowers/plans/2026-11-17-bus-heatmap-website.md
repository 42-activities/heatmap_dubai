# Dubai Bus Heatmap Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A shareable Leaflet heatmap of Dubai bus stops with a real network layer, a monthly-2026 placeholder passenger layer (ins/outs), and a real community population/coverage layer, fed by static JSON exported from the live STG API.

**Architecture:** A stdlib-only Python exporter pulls stops + coverage from STG, dedupes/transforms them, generates labeled placeholder monthly passenger data, and writes static JSON into `web/data/`. A self-contained `web/index.html` (Leaflet + Leaflet.heat, CDN) renders the layers with a month selector and in/out toggle, and is also publishable as an Artifact.

**Tech Stack:** Python 3.9+ (stdlib only; `unittest` for tests), HTML/CSS/vanilla JS, Leaflet 1.9.4 + Leaflet.heat 0.2.0 from cdnjs.

**Spec:** `docs/superpowers/specs/2026-11-17-bus-heatmap-website-design.md`

## Global Constraints

- Page loads **pre-exported static JSON only** — no live API calls, no secrets, no `.env` values in the page or committed.
- Placeholder records carry `"placeholder": true`; the UI shows a persistent **"SAMPLE DATA"** badge whenever a placeholder layer is active.
- Placeholder values are **deterministic** (seeded) — stable across runs.
- Passenger data is **monthly for 2026**: per station, one `in` and one `out` total per month `2026-01`…`2026-12`.
- Stop coordinates come from `rta_bus_stop_details-open-api` lat/long; **dedupe by `stop_id`**.
- API: pagination via `page`/`pageSize` (≤1000), ≤60 req/min, 30 s timeout; token URL is env-specific (STG = `/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken`).
- `ENVIRONMENT` env var selects base URL (STG now, PROD later).
- Scripts are **stdlib-only** (no pip installs); CDN libs pinned to exact versions ≥2 weeks old.

## Review Focus

- **Invalid stop coordinates** (null/empty/non-numeric lat or long): exporter must drop the row, never emit NaN points that break the heat layer. → Task 2.
- **Duplicate `stop_id` with differing coords/validity:** dedupe must pick deterministically (latest `valid_from`), not arbitrarily. → Task 2.
- **Short/empty API page** (fewer rows than `pageSize`, or zero): pagination must stop cleanly without an infinite loop. → Task 1.
- **Community with zero/empty population:** population scaling must not divide by zero or produce NaN radii/opacity. → Task 2 (data) + Task 5 (render guard).
- **Page opened with a data file missing/empty:** page must show an empty-state message, not throw or render blank. → Task 3.

---

### Task 1: Shared DDA client module

**Files:**
- Create: `scripts/dda.py`
- Modify: `scripts/test_token.py`, `scripts/test_dataset.py`, `scripts/profile_ridership.py`, `scripts/join_coverage.py` (import shared helpers from `dda` instead of re-defining)
- Test: `scripts/tests/test_dda.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BASE_URLS: dict[str,str]`, `TOKEN_PATH: str`
  - `load_env(path: Path) -> None`
  - `mask(secret: str, keep: int = 4) -> str`
  - `get_config() -> Config` where `Config = namedtuple("Config", "environment base_url security_id client_id client_secret")`
  - `fetch_token(cfg: Config) -> str`
  - `make_getter(base_url: str, token: str) -> Callable[[str, dict], dict]` — returns `get_json(path, params)` doing the authenticated GET of `/open/<path>`
  - `fetch_records(get_json: Callable[[str, dict], dict], path: str, total: int, page_size: int = 1000) -> list[dict]` — paginates via `page`/`pageSize`, concatenates `results`, stops on a short/empty page

- [ ] **Step 1: Write failing tests**

```python
# scripts/tests/test_dda.py  (inserts scripts/ dir onto sys.path, then: import dda)
def test_mask_keeps_prefix():
    assert dda.mask("abcdefgh", 4) == "abcd****"

def test_fetch_records_concatenates_pages_until_short():
    pages = {1: [{"i": n} for n in range(1000)], 2: [{"i": 1000}]}  # 1000 then 1
    calls = []
    def fake(path, params):
        calls.append(params)
        return {"results": pages.get(params["page"], [])}
    out = dda.fetch_records(fake, "rta/x", total=5000)
    assert len(out) == 1001            # stopped after the short 2nd page
    assert calls[0]["pageSize"] == 1000

def test_fetch_records_stops_on_empty_first_page():
    assert dda.fetch_records(lambda p, q: {"results": []}, "rta/x", total=10) == []
```

- [ ] **Step 2: Run tests, verify they fail** — `cd scripts && python3 -m unittest discover -s tests -v` → FAIL (module/attr missing)
- [ ] **Step 3: Implement `scripts/dda.py`** with the Interfaces above. Move `load_env`, `mask`, `BASE_URLS`, `TOKEN_PATH`, token POST, and the page/pageSize loop here. `fetch_records` loops `page=1,2,…`, breaks when a page returns `< page_size` or `0` rows, and caps at `total`.
- [ ] **Step 4: Refactor the four existing scripts** to `from dda import ...` instead of re-defining these helpers (remove their local copies of `load_env`/`mask`/`BASE_URLS`/`TOKEN_PATH`/`fetch_token`/`fetch_records`).
- [ ] **Step 5: Run tests + import smoke + one live token check**
  - `cd scripts && python3 -m unittest discover -s tests -v` → PASS
  - `python3 -c "import test_token, test_dataset, profile_ridership, join_coverage"` → no error
  - `python3 test_token.py` → prints `RESULT: SUCCESS`
- [ ] **Step 6: Commit** — `git add scripts/dda.py scripts/tests/test_dda.py scripts/test_token.py scripts/test_dataset.py scripts/profile_ridership.py scripts/join_coverage.py && git commit -m "refactor: shared DDA client module"`

---

### Task 2: Data export transforms + writer

**Files:**
- Create: `scripts/export_web_data.py`, `web/data/.gitkeep`
- Test: `scripts/tests/test_export.py`

**Interfaces:**
- Consumes: `dda.get_config`, `dda.fetch_token`, `dda.make_getter`, `dda.fetch_records`.
- Produces (pure, unit-tested):
  - `dedupe_stops(records: list[dict]) -> list[dict]` — one row per `stop_id`; drops rows whose `stop_location_latitude`/`_longitude` is missing or non-numeric; on duplicate `stop_id`, keeps the row with the latest `valid_from`. Output rows: `{stop_id, stop_name, lat, lon}`.
  - `build_placeholder_passengers(stops: list[dict], year: int = 2026, seed: int = 20260101) -> dict` — returns `{"placeholder": True, "year": year, "stations": {stop_id: [{"month": "2026-MM", "in": int, "out": int} for 12 months]}}`; deterministic given seed; `in`/`out` in a plausible range (e.g. 0–50000).
  - `summarize_coverage(records: list[dict]) -> list[dict]` — passthrough of `community_num, community_name, population, accessible_population, geographic_coverage` as typed numbers; coerces blank/`None` numerics to `0`.
  - `write_json(out_dir: Path, name: str, obj) -> Path`
  - `main() -> int` — fetch stops+coverage from `get_config()` env, transform, write `web/data/{stops,passengers,coverage,meta}.json`; `meta.json` has `{environment, generated_at, counts, placeholder: {passengers: True}}`.

- [ ] **Step 1: Write failing tests**

```python
def test_dedupe_drops_invalid_coords():
    rows = [{"stop_id": 1, "stop_name": "A", "stop_location_latitude": "",
             "stop_location_longitude": "55.1", "valid_from": "2020-01-01"}]
    assert export_web_data.dedupe_stops(rows) == []

def test_dedupe_keeps_latest_valid_from_per_stop_id():
    rows = [
      {"stop_id": 5, "stop_name": "Old", "stop_location_latitude": 25.0,
       "stop_location_longitude": 55.0, "valid_from": "2017-01-01"},
      {"stop_id": 5, "stop_name": "New", "stop_location_latitude": 25.1,
       "stop_location_longitude": 55.1, "valid_from": "2020-01-01"}]
    out = export_web_data.dedupe_stops(rows)
    assert len(out) == 1 and out[0]["stop_name"] == "New"

def test_placeholder_is_deterministic_and_monthly_2026():
    stops = [{"stop_id": 1, "stop_name": "A", "lat": 25.0, "lon": 55.0}]
    a = export_web_data.build_placeholder_passengers(stops)
    b = export_web_data.build_placeholder_passengers(stops)
    assert a == b                                   # deterministic
    months = [m["month"] for m in a["stations"]["1"]]   # keys are str(stop_id)
    assert len(months) == 12 and months[0] == "2026-01" and months[-1] == "2026-12"
    assert a["placeholder"] is True

def test_summarize_coverage_coerces_blank_population_to_zero():
    rows = [{"community_num": 9, "community_name": "X", "population": "",
             "accessible_population": 10, "geographic_coverage": 80}]
    assert export_web_data.summarize_coverage(rows)[0]["population"] == 0
```

- [ ] **Step 2: Run tests, verify they fail** — `cd scripts && python3 -m unittest discover -s tests -v` → FAIL
- [ ] **Step 3: Implement `scripts/export_web_data.py`** with the Interfaces above. Placeholder uses `random.Random(seed + stop_id)` so values are stable and vary per station. Keep `stop_id` keys as strings in JSON.
- [ ] **Step 4: Run tests, verify pass** — `python3 -m unittest discover -s tests -v` → PASS
- [ ] **Step 5: Produce real data from STG** — `cd scripts && python3 export_web_data.py` then verify: `web/data/stops.json` non-empty, `meta.json` shows `environment: "STG"` and `placeholder.passengers: true`. Expected: thousands of stops, 227 coverage rows.
- [ ] **Step 6: Commit** — `git add scripts/export_web_data.py scripts/tests/test_export.py web/data/.gitkeep web/data/*.json && git commit -m "feat: export STG data + placeholder passengers to web/data"`

---

### Task 3: Web page skeleton + Network layer

**Files:**
- Create: `web/index.html`, `web/app.js`, `web/style.css`
- Modify: none

**Interfaces:**
- Consumes: `web/data/stops.json` (`[{stop_id, stop_name, lat, lon}]`), `web/data/meta.json`.
- Produces: global `window.HeatmapApp` with `loadData()`, `addNetworkLayer()`, and a Leaflet `map`; the HTML scaffold (map div, layer control container, badge element, empty-state element) other tasks attach to.

- [ ] **Step 1:** Build `web/index.html` loading Leaflet 1.9.4 + Leaflet.heat 0.2.0 from cdnjs, with a full-viewport `#map`, a `#controls` panel, a hidden `#sample-badge`, and a hidden `#empty-state`.
- [ ] **Step 2:** In `app.js`, init the map centered on Dubai (`[25.2, 55.3]`, zoom 11) with an OSM/Carto tile layer; `fetch('data/stops.json')`; if the fetch fails or returns `[]`, show `#empty-state` and stop.
- [ ] **Step 3:** Add a **Network** heat layer (`L.heatLayer` from stop coords) + a toggle in `#controls`.
- [ ] **Step 4: Verify (visual)** — open `web/index.html` via the `run` skill or a browser. Expected: Dubai map with a dense stop heat layer; toggling Network on/off works; with `data/stops.json` temporarily emptied, the empty-state shows and no console error.
- [ ] **Step 5: Commit** — `git add web/index.html web/app.js web/style.css && git commit -m "feat: heatmap page skeleton + network layer"`

---

### Task 4: Monthly passenger layers (placeholder) + SAMPLE badge

**Files:**
- Modify: `web/app.js`, `web/index.html`, `web/style.css`

**Interfaces:**
- Consumes: `web/data/passengers.json` (`{placeholder, year, stations: {stop_id: [{month,in,out}]}}`, keys are `str(stop_id)`), Task 3's `map`/controls, `stops.json` for coordinates. Join passengers→coords with `String(stop.stop_id)` (stops.json keeps numeric `stop_id`).
- Produces: `setMonth(ym)`, `setDirection("in"|"out")`, `updatePassengerLayer()` on `window.HeatmapApp`.

- [ ] **Step 1:** Add a **month selector** (`2026-01`…`2026-12`), an **in/out** toggle, and a **Passengers** layer toggle to `#controls`.
- [ ] **Step 2:** Implement `updatePassengerLayer()` — for the selected month+direction, build a heat layer weighting each station by its `in`/`out` value (join passengers→coords by `stop_id`); skip stations with no coord.
- [ ] **Step 3:** Show `#sample-badge` ("SAMPLE DATA") whenever the Passengers layer is active and `passengers.json.placeholder === true`; hide it when off.
- [ ] **Step 4:** Station tooltip/popup shows name + selected-month `in`/`out`.
- [ ] **Step 5: Verify (visual)** — enable Passengers; changing month and in/out visibly changes the heat; SAMPLE badge is visible only while the layer is on; a station popup shows the month's numbers.
- [ ] **Step 6: Commit** — `git add web/ && git commit -m "feat: monthly 2026 passenger placeholder layers + sample badge"`

---

### Task 5: Population / coverage layer

**Files:**
- Modify: `web/app.js`, `web/index.html`, `web/style.css`
- Possibly create: `web/data/communities.geojson` (only if boundaries are obtained)

**Interfaces:**
- Consumes: `web/data/coverage.json`, optional community-boundaries GeoJSON joined by `community_num`/name.
- Produces: `addPopulationLayer()`.

- [ ] **Step 1: Recon** — attempt to obtain a Dubai community-boundaries GeoJSON (Dubai Pulse `dm_community-open`, or convert published KML). Time-box it.
- [ ] **Step 2 (branch A — boundaries found):** save as `web/data/communities.geojson`; render a **choropleth** colored by `geographic_coverage` (or `accessible_population`), with a guard so a `0`/missing value renders a neutral "no data" shade, never NaN.
- [ ] **Step 2 (branch B — not found):** render each community as a labeled **placeholder-positioned** marker sized by population + a ranked side panel; mark the layer with the SAMPLE badge rule (it's placeholder *placement*).
- [ ] **Step 3:** Tooltip shows the **real** numbers (`population`, `accessible_population`, `geographic_coverage`) regardless of branch.
- [ ] **Step 4: Verify (visual)** — Population layer toggles on; coloring/sizing reflects coverage; zero-population community renders without error; tooltip shows real values; SAMPLE badge appears only under branch B.
- [ ] **Step 5: Commit** — `git add web/ && git commit -m "feat: community population/coverage layer"`

---

### Task 6: Publish + repo wiring

**Files:**
- Create: `web/README.md`
- Modify: `README.md`, `TODO.md`

**Interfaces:** consumes the finished `web/` + `web/data/`.

- [ ] **Step 1:** `web/README.md` — how to regenerate data (`python3 scripts/export_web_data.py`), how to open the page, and the STG→PROD swap note (set `ENVIRONMENT=PROD`, replace `passengers.json` with the real monthly-2026 aggregation).
- [ ] **Step 2:** Publish `web/index.html` (+ `web/data/*`, `web/app.js`, `web/style.css`) as an Artifact. If the sandbox blocks external map tiles, apply the tile-free fallback (styled background + stop/heat layers) and re-publish.
- [ ] **Step 3:** Update root `README.md` (link the page/Artifact) and tick the relevant `TODO.md` items.
- [ ] **Step 4: Verify** — the published Artifact opens and all layers work; `python3 -m unittest discover -s scripts/tests -v` still passes.
- [ ] **Step 5: Commit** — `git add web/README.md README.md TODO.md && git commit -m "docs: publish heatmap + wire up web README"`
