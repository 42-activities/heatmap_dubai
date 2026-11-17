import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import type { Coverage } from '../../data'
import ChartCard, { axisStyle, tooltipStyle } from './ChartCard'

export default function PopulationScatter({ rows }: { rows: Coverage[] }) {
  const d = rows.map((r) => ({ name: r.community_name, population: r.population, pct: +(r.geographic_coverage * 100).toFixed(1) }))
  return (
    <ChartCard title="Population vs coverage (each dot is a community)">
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
          <CartesianGrid stroke="var(--border)" />
          <XAxis type="number" dataKey="population" name="Population" tick={axisStyle} stroke="var(--border)" tickFormatter={(v: number) => v.toLocaleString('en-US')} label={{ value: 'Population', position: 'insideBottom', offset: -8, fill: 'var(--muted)', fontSize: 12 }} />
          <YAxis type="number" dataKey="pct" name="Coverage" unit="%" domain={[0, 100]} tick={axisStyle} stroke="var(--border)" />
          <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={d} fill="var(--accent)" />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
