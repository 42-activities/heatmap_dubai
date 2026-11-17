import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Coverage } from '../../data'
import ChartCard, { axisStyle, tooltipStyle } from './ChartCard'

export function bucketCoverage(rows: Coverage[], buckets = 10) {
  const out = Array.from({ length: buckets }, (_, i) => ({
    range: `${Math.round((i * 100) / buckets)}-${Math.round(((i + 1) * 100) / buckets)}%`,
    count: 0,
  }))
  for (const r of rows) {
    const i = Math.min(buckets - 1, Math.max(0, Math.floor(r.geographic_coverage * buckets / 100)))
    out[i].count += 1
  }
  return out
}

export default function CoverageHistogram({ rows }: { rows: Coverage[] }) {
  const buckets = bucketCoverage(rows)
  return (
    <ChartCard title="Coverage distribution (communities per coverage band)">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={buckets} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis dataKey="range" tick={axisStyle} stroke="var(--border)" interval={0} angle={-30} textAnchor="end" height={50} />
          <YAxis allowDecimals={false} tick={axisStyle} stroke="var(--border)" />
          <Tooltip {...tooltipStyle} cursor={{ fill: 'var(--border)', opacity: 0.4 }} />
          <Bar dataKey="count" name="Communities" fill="var(--accent)" label={{ position: 'top', fill: 'var(--text)', fontSize: 11 }} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
