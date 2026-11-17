# Frontend (React + TypeScript + Vite)

Single-page app with Overview, Heatmap, Explorer and Data views. Consumes the
FastAPI backend (`/api`) or, in static mode, the bundled `web/data` JSON.

## Dev

```bash
make up                 # from repo root: db + loader + api on :8000
cd frontend && npm ci && npm run dev
npm run test -- --run
```

`predev`/`prebuild` copy `../web/data/*` into `public/data/` (git-ignored).

## Dual build

| Variable | Meaning |
|---|---|
| `VITE_API_BASE` | `/api` (or full URL) = use the API; **empty** = static mode reading bundled `data/*.json` |
| `VITE_BASE` | URL base: `/` (Docker/dev) or `/heatmap_dubai/` (GitHub Pages) |

```bash
VITE_BASE=/heatmap_dubai/ VITE_API_BASE= npm run build   # Pages (static)
```

## Docker

`frontend/Dockerfile` builds with `VITE_API_BASE=/api VITE_BASE=/` and serves
`dist` from `nginx:1.27-alpine`. `nginx.conf` falls back to `index.html` for
client routing and proxies `/api/` to `http://api:8000/` (prefix stripped).

```bash
docker compose up -d --build frontend   # http://localhost:8080
```

Production: `docker-compose.prod.yml` binds it to `127.0.0.1:8080` behind the
owner's TLS proxy.

## Deploy (GitHub Pages)

`.github/workflows/pages.yml` runs on push to `main`, builds in static mode and
deploys `frontend/dist`. The repo's Pages source must be set to **GitHub
Actions** (Settings, Pages).
