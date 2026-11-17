import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Coverage } from '../../data'
import ChartCard, { axisStyle, tooltipStyle } from './ChartCard'

export function topBottom(rows: Coverage[], n = 5) {
  const sorted = [...rows].sort((a, b) => b.geographic_coverage - a.geographic_coverage)
  const pick = sorted.length <= 2 * n ? sorted : [...sorted.slice(0, n), ...sorted.slice(-n)]
  return pick.map((r) => ({ name: r.community_name, pct: +r.geographic_coverage.toFixed(1) }))
}

export default function TopBottomCommunities({ rows }: { rows: Coverage[] }) {
  const d = topBottom(rows)
  return (
    <ChartCard title="Highest and lowest coverage communities (%)">
      <ResponsiveContainer width="100%" height={Math.max(260, d.length * 28)}>
        <BarChart data={d} layout="vertical" margin={{ top: 8, right: 32, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tick={axisStyle} stroke="var(--border)" unit="%" />
          <YAxis type="category" dataKey="name" width={120} tick={axisStyle} stroke="var(--border)" interval={0} />
          <Tooltip {...tooltipStyle} cursor={{ fill: 'var(--border)', opacity: 0.4 }} formatter={(v) => `${v}%`} />
          <Bar dataKey="pct" name="Coverage" fill="var(--accent)" label={{ position: 'right', fill: 'var(--text)', fontSize: 11, formatter: (v: number) => `${v}%` }} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
