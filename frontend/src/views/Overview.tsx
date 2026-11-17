import { useEffect, useState } from 'react'
import { data } from '../data'
import type { Coverage, Kpis } from '../data'
import KpiTile from '../components/KpiTile'
import CoverageHistogram from '../components/charts/CoverageHistogram'
import PopulationScatter from '../components/charts/PopulationScatter'
import TopBottomCommunities from '../components/charts/TopBottomCommunities'

const num = (n: number) => Math.round(n).toLocaleString('en-US')
const pct = (n: number) => `${(n * 100).toFixed(1)}%`

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; kpis: Kpis; rows: Coverage[] }

export default function Overview() {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let live = true
    Promise.all([data.getKpis(), data.getCoverage()])
      .then(([kpis, cov]) => live && setState({ status: 'ready', kpis, rows: cov.results }))
      .catch((e: unknown) =>
        live && setState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load data' }),
      )
    return () => {
      live = false
    }
  }, [])

  return (
    <section>
      <h1>Overview</h1>
      {state.status === 'loading' && <p role="status">Loading overview…</p>}
      {state.status === 'error' && (
        <p role="alert" className="error">Failed to load overview: {state.message}</p>
      )}
      {state.status === 'ready' && <Ready kpis={state.kpis} rows={state.rows} />}
    </section>
  )
}

function Ready({ kpis, rows }: { kpis: Kpis; rows: Coverage[] }) {
  const accessible = kpis.population > 0 ? kpis.accessible_population / kpis.population : 0
  return (
    <>
      <div className="kpis">
        <KpiTile label="Bus stops" value={num(kpis.stops)} />
        <KpiTile label="Communities" value={num(kpis.communities)} />
        <KpiTile label="Routes" value={num(kpis.routes)} />
        <KpiTile label="Coverage (average)" value={pct(kpis.coverage_avg)} sublabel="geographic, per community" />
        <KpiTile label="Coverage (median)" value={pct(kpis.coverage_median)} sublabel="geographic, per community" />
        <KpiTile label="Population" value={num(kpis.population)} />
        <KpiTile label="Accessible population" value={num(kpis.accessible_population)} sublabel={`${pct(accessible)} of population`} />
      </div>
      <div className="charts">
        <CoverageHistogram rows={rows} />
        <TopBottomCommunities rows={rows} />
        <PopulationScatter rows={rows} />
      </div>
    </>
  )
}
