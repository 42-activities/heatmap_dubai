import { useEffect, useMemo, useRef, useState } from 'react'
import { data } from '../data'
import type { Coverage, Route, Stop } from '../data'
import DataTable from '../components/DataTable'
import type { Column } from '../components/DataTable'

type TabKey = 'stops' | 'communities' | 'routes'
const TABS: { key: TabKey; label: string }[] = [
  { key: 'stops', label: 'Stops' },
  { key: 'communities', label: 'Communities' },
  { key: 'routes', label: 'Routes' },
]

const int = (v: string | number) => Number(v).toLocaleString('en-US')
const pct = (v: string | number) => `${Number(v).toFixed(1)}%`

const stopCols: Column<Stop>[] = [
  { key: 'stop_id', header: 'Stop ID', accessor: (r) => r.stop_id },
  { key: 'stop_name', header: 'Name', accessor: (r) => r.stop_name },
  { key: 'lat', header: 'Lat', accessor: (r) => r.lat },
  { key: 'lon', header: 'Lon', accessor: (r) => r.lon },
]
const communityCols: Column<Coverage>[] = [
  { key: 'community_num', header: 'Community #', accessor: (r) => r.community_num },
  { key: 'community_name', header: 'Name', accessor: (r) => r.community_name },
  { key: 'population', header: 'Population', accessor: (r) => r.population, format: int },
  { key: 'accessible_population', header: 'Accessible population', accessor: (r) => r.accessible_population, format: int },
  { key: 'geographic_coverage', header: 'Coverage', accessor: (r) => r.geographic_coverage, format: pct },
]
const routeCols: Column<Route>[] = [
  { key: 'route_name', header: 'Route', accessor: (r) => r.route_name },
  { key: 'route_type', header: 'Type', accessor: (r) => r.route_type },
  { key: 'stop_count', header: 'Stops', accessor: (r) => r.stop_count },
]

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; tab: TabKey; rows: unknown[] }

function load(tab: TabKey): Promise<unknown[]> {
  if (tab === 'stops') return data.getAllStops()
  if (tab === 'communities') return data.getCoverage().then((p) => p.results)
  return data.getRoutes({ limit: 1000 }).then((p) => p.results)
}

export default function Explorer() {
  const [tab, setTab] = useState<TabKey>('stops')
  const [query, setQuery] = useState('')
  const [state, setState] = useState<State>({ status: 'loading' })
  const [reloadKey, setReloadKey] = useState(0)
  const cache = useRef(new Map<TabKey, unknown[]>())

  useEffect(() => {
    let live = true
    const cached = cache.current.get(tab)
    if (cached) {
      setState({ status: 'ready', tab, rows: cached }) // instant on tab re-select
      return
    }
    setState({ status: 'loading' })
    load(tab)
      .then((rows) => {
        cache.current.set(tab, rows)
        if (live) setState({ status: 'ready', tab, rows })
      })
      .catch((e: unknown) =>
        live && setState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load data' }),
      )
    return () => {
      live = false
    }
  }, [tab, reloadKey])

  const retry = () => {
    cache.current.delete(tab)
    setReloadKey((k) => k + 1)
  }

  const view: State = state.status === 'ready' && state.tab !== tab ? { status: 'loading' } : state

  const columns = (tab === 'stops' ? stopCols : tab === 'communities' ? communityCols : routeCols) as Column<unknown>[]

  const filtered = useMemo(() => {
    if (view.status !== 'ready') return []
    const q = query.trim().toLowerCase()
    if (!q) return view.rows
    return view.rows.filter((r) =>
      columns.some((c) => {
        const v = c.accessor(r)
        if (String(v).toLowerCase().includes(q)) return true
        // also match the displayed (formatted) value, e.g. "90.0%" or "1,234"
        return c.format ? c.format(v).toLowerCase().includes(q) : false
      }),
    )
  }, [view, query, columns])

  const keyCol = columns[0]

  return (
    <section>
      <h1>Explorer</h1>
      <div role="tablist" className="explorer__tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? 'active' : ''}
            onClick={() => { setTab(t.key); setQuery('') }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <input
        type="search"
        className="explorer__search"
        aria-label="Search"
        placeholder="Search…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {view.status === 'loading' && <p role="status">Loading {tab}…</p>}
      {view.status === 'error' && (
        <p role="alert" className="error">
          Failed to load {tab}: {view.message}{' '}
          <button type="button" onClick={retry}>Retry</button>
        </p>
      )}
      {view.status === 'ready' && (
        <>
          <p className="explorer__count" role="status">
            {filtered.length.toLocaleString('en-US')} of {view.rows.length.toLocaleString('en-US')} {tab}
          </p>
          <DataTable columns={columns} rows={filtered} rowKey={(r) => String(keyCol.accessor(r))} />
        </>
      )}
    </section>
  )
}
