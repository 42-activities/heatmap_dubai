interface Props {
  label: string
  value: string
  sublabel?: string
  sample?: boolean
}

export default function KpiTile({ label, value, sublabel, sample }: Props) {
  return (
    <div className="kpi">
      <div className="kpi__label">
        {label}
        {sample && <span className="badge-sample">SAMPLE</span>}
      </div>
      <div className="kpi__value">{value}</div>
      {sublabel && <div className="kpi__sub">{sublabel}</div>}
    </div>
  )
}
