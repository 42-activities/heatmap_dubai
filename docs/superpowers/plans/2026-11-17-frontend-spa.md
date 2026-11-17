# Frontend SPA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React + Vite SPA (Overview dashboard, Heatmap, Explorer, Data) that consumes the FastAPI backend, builds static for GitHub Pages, and is served by an nginx container in the Docker stack.

**Architecture:** One React app with a `src/data/` layer behind a `VITE_API_BASE` switch: in the Docker/nginx build it calls `/api` (nginx proxies to the `api` service); in the Pages build it reads the static `web/data/*.json` (shaped to match the API responses). nginx serves the built SPA and reverse-proxies `/api`. A GitHub Actions workflow builds the static variant and deploys it to Pages.

**Tech Stack:** React 18, Vite 6, TypeScript, react-router-dom 7, Recharts 2, react-leaflet 4 + leaflet 1.9, vitest + @testing-library/react, nginx, Docker.

**Spec:** `docs/superpowers/specs/2026-11-17-frontend-spa-design.md`

## Backend it consumes (already built, running at http://localhost:8000)
`GET /kpis`, `/stops?limit&offset`, `/communities`, `/routes`, `/coverage` (all `{results,total}`), `/passengers?month=YYYY-MM&direction=in|out` (`{results:[{stop_id,count,placeholder}],total}`), `/communities.geojson` (FeatureCollection, coverage merged in properties), `/health`. Stops have `{stop_id,stop_name,lat,lon}`. CORS is open for dev.

## Global Constraints

- All new frontend code lives in `frontend/`. Libraries pinned to exact versions ≥2 weeks old.
- **Dual build via env:** `VITE_API_BASE` (`/api` for Docker, empty→static for Pages) and `VITE_BASE` (`/heatmap_dubai/` for Pages, `/` for Docker). The `src/data/` layer is the ONLY place that branches on mode.
- **Static (Pages) build reads `web/data/*.json`** and shapes it to the same TypeScript types the API returns, so views are mode-agnostic. Copy `web/data/` into `frontend/public/data/` at build (a script or Vite `publicDir` copy).
- No secrets in the frontend or in git. No live DDA calls from the browser.
- **Placeholder honesty:** wherever passenger data appears (map, any KPI/chart derived from it), show a visible "SAMPLE DATA" marker when `placeholder` is true.
- nginx serves the SPA and proxies `/api` → `api:8000`; SPA routing falls back to `index.html`.
- Tests: `vitest` + Testing Library; `npm run build` must succeed (type-checks).

## Review Focus

- **API/endpoint down or slow** → each view shows a loading state then a clear error, never a blank white screen or an uncaught crash. → Tasks 3–5 (tested with a rejecting fetch).
- **Static-vs-API shape parity** → the static adapter must return the exact shape views expect (e.g. `{results,total}`); a mismatch silently breaks the Pages build. → Task 2 (tested both adapters against one shape).
- **Pages subpath base** → assets and router must work under `/heatmap_dubai/` (no absolute `/assets` 404s; router `basename`). → Task 6 (built-static smoke under a subpath).
- **Passenger month with no data** → map/overview render an empty/zero state, no NaN or crash. → Task 4.
- **4,220-row stops table** → must not freeze the page (server pagination via `limit/offset/total`, not render-all). → Task 5.

---

### Task 1: Scaffold + app shell + routing + theme

**Files:** Create `frontend/` (Vite React-TS): `package.json`, `vite.config.ts`, `tsconfig*.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/components/Nav.tsx`, `src/components/Layout.tsx`, `src/theme.css`, `src/views/{Overview,Heatmap,Explorer,Data}.tsx` (placeholders), `src/test/App.test.tsx`, `vitest.config.ts`.

**Interfaces:** Produces the router (routes `/`, `/heatmap`, `/explorer`, `/data`), the `Layout`/`Nav` shell, theme tokens (light/dark), and `window`-free env access via `import.meta.env.VITE_*`. `vite.config.ts` sets `base: process.env.VITE_BASE ?? '/'` and a dev proxy `/api` → `http://localhost:8000`.

- [ ] **Step 1:** `npm create vite@6 frontend -- --template react-ts` (or equivalent scaffolding), then add react-router-dom, recharts, react-leaflet, leaflet, vitest, @testing-library/react, jsdom — all pinned. Set `vite.config.ts` base + dev `/api` proxy.
- [ ] **Step 2: Write the failing test** `src/test/App.test.tsx`: render `<App/>` in `MemoryRouter`, assert the four nav links (Overview/Heatmap/Explorer/Data) are present.
- [ ] **Step 3: Run** `cd frontend && npm run test -- --run` → FAIL (nav not built).
- [ ] **Step 4:** Build `App` (router + `Layout` + `Nav`), the four placeholder views, and `theme.css` (light/dark tokens, responsive, mobile nav). Env-driven `basename` on the router from `import.meta.env.BASE_URL`.
- [ ] **Step 5: Run** test → PASS; `npm run build` succeeds (type-check clean); `npm run dev` serves the shell.
- [ ] **Step 6: Commit** `frontend/` (ensure `frontend/node_modules`, `frontend/dist` are git-ignored) — `git add frontend .gitignore && git commit -m "feat: frontend scaffold + app shell + routing"`

---

### Task 2: Data layer (API client + static adapter)

**Files:** Create `src/data/types.ts`, `src/data/api.ts`, `src/data/static.ts`, `src/data/index.ts`, `src/data/*.test.ts`.

**Interfaces:**
- Consumes: the backend endpoints (dev proxy) and `public/data/*.json` (static).
- Produces a single `data` module with typed async functions used by every view: `getKpis()`, `getStops({limit,offset})`, `getRoutes({limit,offset})`, `getCommunities({limit,offset})`, `getCoverage()`, `getPassengers(month, direction)`, `getCommunitiesGeoJson()`. Each returns the SAME shape in both modes (`Page<T>` = `{results:T[], total:number}` where applicable). `index.ts` picks `api.ts` when `VITE_API_BASE` is set, else `static.ts`. A shared `TypedError` for failures.

- [ ] **Step 1: Write failing tests** (`api.test.ts`, `static.test.ts`): mock `fetch` / stub JSON; assert `getPassengers('2026-01','in')` returns `{results:[{stop_id,count,placeholder}],total}` in BOTH modes; assert a rejected fetch throws a `TypedError` (not an unhandled promise).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement `api.ts` (fetch `${VITE_API_BASE}/<path>`, check `res.ok`, parse) and `static.ts` (fetch `${BASE_URL}data/<file>.json`, shape raw arrays into `Page<T>`, un-pivot passengers client-side to match the API). `index.ts` switch. Add a build step copying `web/data/*` → `frontend/public/data/` (script in package.json or a vite plugin).
- [ ] **Step 4: Run** tests → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/data frontend/package.json && git commit -m "feat: typed data layer with API + static adapters"`

---

### Task 3: Overview dashboard (KPIs + charts)

**Files:** `src/views/Overview.tsx`, `src/components/KpiTile.tsx`, `src/components/charts/*.tsx`, `src/views/Overview.test.tsx`.

**Interfaces:** Consumes `data.getKpis()`, `data.getCoverage()`. Produces the Overview view.

- [ ] **Step 1: Write failing test:** render `<Overview/>` with the `data` module mocked; assert KPI tiles show the mocked totals and a chart container renders; assert a rejected `getKpis` shows an error state (not a crash).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement KPI tiles (stops, communities, routes, coverage avg/median, population, accessible %) + 2–3 Recharts charts (coverage distribution; top/bottom communities by coverage; population vs coverage). Loading + error states. A SAMPLE note if any tile derives from passengers.
- [ ] **Step 4: Run** test → PASS; `npm run build` clean.
- [ ] **Step 5: Commit** — `git commit -m "feat: overview dashboard (kpis + charts)"`

---

### Task 4: Heatmap view (react-leaflet)

**Files:** `src/views/Heatmap.tsx`, `src/components/map/*.tsx` (layers, controls), `src/views/Heatmap.test.tsx`.

**Interfaces:** Consumes `data.getStops`, `data.getPassengers`, `data.getCommunitiesGeoJson`. Reuses the layer logic from the existing vanilla `web/app.js` (network heat, monthly-2026 passengers with month selector + in/out + SAMPLE badge, community choropleth) but as React/react-leaflet components. leaflet.heat via a thin wrapper (it's not in react-leaflet).

- [ ] **Step 1: Write failing test:** render `<Heatmap/>` with mocked data and a mocked leaflet (jsdom can't draw tiles); assert the layer toggles, the month selector (2026-01..12), the in/out control, and the SAMPLE badge element exist, and that selecting a month with no passenger data doesn't throw.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement the map: base tiles, network heat layer, passenger heat (month+direction, weighted, rebuilt on change), choropleth from the geojson endpoint, layer control, SAMPLE badge when passenger `placeholder` is true. Empty/zero state for a month with no data.
- [ ] **Step 4: Run** test → PASS; `npm run build` clean; dev-check the map renders against the live API.
- [ ] **Step 5: Commit** — `git commit -m "feat: heatmap view (network + passengers + choropleth)"`

---

### Task 5: Explorer tables

**Files:** `src/views/Explorer.tsx`, `src/components/DataTable.tsx`, `src/views/Explorer.test.tsx`.

**Interfaces:** Consumes `data.getStops/getCommunities/getRoutes` (server pagination via `{limit,offset,total}`). Produces searchable/sortable/paginated tables.

- [ ] **Step 1: Write failing test:** render `<Explorer/>` with mocked paginated data; assert rows render, a search box filters (client or server), sorting toggles, and the pager advances offset; assert it never renders all 4220 rows at once (page size bounded).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement a reusable `DataTable` (columns, sort, pagination) + a tab/selector for Stops / Communities / Routes; search calls the API (or filters the page); loading/error states.
- [ ] **Step 4: Run** test → PASS; `npm run build` clean.
- [ ] **Step 5: Commit** — `git commit -m "feat: explorer tables (stops/communities/routes)"`

---

### Task 6: Data page + nginx container + Pages deploy + docs

**Files:** `src/views/Data.tsx` (fill in); Create `frontend/Dockerfile`, `frontend/nginx.conf`, `.github/workflows/pages.yml`; Modify `docker-compose.yml` (frontend service), `docker-compose.prod.yml`, root `README.md`, `frontend/README.md`, `TODO.md`.

**Interfaces:** consumes the finished views + the backend.

- [ ] **Step 1:** Fill `Data.tsx` (datasets, real-vs-placeholder caveats, attribution incl. Dubai Municipality boundaries, regen/refresh notes).
- [ ] **Step 2:** `frontend/Dockerfile` (multi-stage: `npm ci && npm run build` with `VITE_API_BASE=/api VITE_BASE=/`, then nginx serving `dist`); `frontend/nginx.conf` (serve SPA, `try_files … /index.html`, `location /api/ { proxy_pass http://api:8000/; }`). Add `frontend` service to `docker-compose.yml` (depends_on api, port 80→8080) and prod override.
- [ ] **Step 3:** `.github/workflows/pages.yml`: on push to main, `npm ci && npm run build` with `VITE_BASE=/heatmap_dubai/ VITE_API_BASE=` (static mode, bundles `web/data`), upload `frontend/dist` as the Pages artifact and deploy. (Pages source becomes GitHub Actions — note in README; the old static `web/` page can move to `web/classic/` or stay as a link.)
- [ ] **Step 4: Verify** — (a) `docker compose up -d --build frontend` then `curl -s localhost:8080` serves the SPA and `curl -s localhost:8080/api/health` proxies to the api (db:true); (b) a static build `cd frontend && VITE_BASE=/heatmap_dubai/ VITE_API_BASE= npm run build` succeeds and `dist/index.html` references `/heatmap_dubai/assets/...` (subpath correct); (c) `npm run test -- --run` all green.
- [ ] **Step 5:** Update root `README.md` (frontend + full architecture), `frontend/README.md` (dev, dual build, deploy), tick `TODO.md`.
- [ ] **Step 6: Commit** — `git add frontend .github docker-compose*.yml README.md TODO.md && git commit -m "feat: data page, nginx frontend container, Pages deploy workflow, docs"`
