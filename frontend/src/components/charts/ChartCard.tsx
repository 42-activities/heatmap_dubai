import type { ReactNode } from 'react'

export const axisStyle = { fill: 'var(--muted)', fontSize: 12 }
export const tooltipStyle = {
  contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8 },
  itemStyle: { color: 'var(--text)' },
  labelStyle: { color: 'var(--text)' },
}

export default function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <figure className="chart" data-testid="chart">
      <figcaption className="chart__title">{title}</figcaption>
      <div className="chart__body">{children}</div>
    </figure>
  )
}
