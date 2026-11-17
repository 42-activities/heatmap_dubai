import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { data } from '../data'
import Explorer from './Explorer'

vi.mock('../data', () => ({
  data: { getAllStops: vi.fn(), getCoverage: vi.fn(), getRoutes: vi.fn() },
}))

const stops = Array.from({ length: 4220 }, (_, i) => ({
  stop_id: i + 1, stop_name: i === 99 ? 'Zebra Plaza' : `Stop ${i + 1}`, lat: 25 + i / 1e5, lon: 55,
}))
const bodyRows = () => within(screen.getAllByRole('rowgroup')[1]).getAllByRole('row')

describe('Explorer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(data.getAllStops).mockResolvedValue(stops)
    vi.mocked(data.getCoverage).mockResolvedValue({
      total: 2,
      results: [
        { community_num: 1, community_name: 'Alpha', population: 1000, accessible_population: 900, geographic_coverage: 90 },
        { community_num: 2, community_name: 'Beta', population: 2000, accessible_population: 100, geographic_coverage: 10 },
      ],
    })
    vi.mocked(data.getRoutes).mockResolvedValue({
      total: 1, results: [{ route_name: 'R1', route_type: 'Bus', stop_count: 5 }],
    })
  })

  it('shows loading then stop rows, bounded by page size', async () => {
    render(<Explorer />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(await screen.findByText('Stop 1')).toBeInTheDocument()
    expect(bodyRows().length).toBeLessThanOrEqual(50)
    expect(screen.getByText(/4,220/)).toBeInTheDocument()
  })

  it('search filters across the full dataset', async () => {
    render(<Explorer />)
    await screen.findByText('Stop 1')
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'zebra' } })
    expect(await screen.findByText('Zebra Plaza')).toBeInTheDocument()
    expect(bodyRows()).toHaveLength(1)
  })

  it('clicking a header sorts asc then desc', async () => {
    render(<Explorer />)
    await screen.findByText('Stop 1')
    fireEvent.click(screen.getByRole('button', { name: /stop_id|stop id/i }))
    fireEvent.click(screen.getByRole('button', { name: /stop_id|stop id/i }))
    expect(within(bodyRows()[0]).getByText('4220')).toBeInTheDocument()
  })

  it('pager advances to the next page', async () => {
    render(<Explorer />)
    await screen.findByText('Stop 1')
    expect(screen.queryByText('Stop 26')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText('Stop 26')).toBeInTheDocument()
    expect(screen.queryByText('Stop 1')).not.toBeInTheDocument()
  })

  it('switches to communities and routes tabs', async () => {
    render(<Explorer />)
    await screen.findByText('Stop 1')
    fireEvent.click(screen.getByRole('tab', { name: /communities/i }))
    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: /routes/i }))
    expect(await screen.findByText('R1')).toBeInTheDocument()
  })

  it('shows an error', async () => {
    vi.mocked(data.getAllStops).mockRejectedValue(new Error('boom'))
    render(<Explorer />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/boom/)
  })
})
