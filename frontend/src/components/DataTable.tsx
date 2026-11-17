import { useEffect, useMemo, useState } from 'react'

export interface Column<T> {
  key: string
  header: string
  accessor: (row: T) => string | number
  sortable?: boolean
  format?: (value: string | number) => string
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  pageSize?: number
}

export default function DataTable<T>({ columns, rows, rowKey, pageSize = 25 }: Props<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(null)
  const [page, setPage] = useState(0)

  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    if (!col) return rows
    const m = sort.dir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const x = col.accessor(a)
      const y = col.accessor(b)
      if (typeof x === 'number' && typeof y === 'number') return (x - y) * m
      return String(x).localeCompare(String(y), undefined, { numeric: true }) * m
    })
  }, [rows, columns, sort])

  const pages = Math.max(1, Math.ceil(sorted.length / pageSize))
  useEffect(() => setPage(0), [rows])
  const cur = Math.min(page, pages - 1)
  const visible = sorted.slice(cur * pageSize, (cur + 1) * pageSize)

  const toggle = (key: string) =>
    setSort((s) => (s && s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))

  return (
    <div className="dt">
      <div className="dt__scroll">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={sort?.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  {c.sortable === false ? (
                    c.header
                  ) : (
                    <button type="button" onClick={() => toggle(c.key)}>
                      {c.header}
                      {sort?.key === c.key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
                    </button>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={rowKey(r)}>
                {columns.map((c) => {
                  const v = c.accessor(r)
                  return <td key={c.key}>{c.format ? c.format(v) : v}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="dt__pager">
        <button type="button" onClick={() => setPage(cur - 1)} disabled={cur === 0}>Previous</button>
        <span>Page {cur + 1} of {pages}</span>
        <button type="button" onClick={() => setPage(cur + 1)} disabled={cur >= pages - 1}>Next</button>
      </div>
    </div>
  )
}
