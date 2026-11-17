import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { data } from '../data'
import Overview from './Overview'

vi.mock('../data', () => ({
  data: { getKpis: vi.fn(), getCoverage: vi.fn() },
}))

const kpis = {
  stops: 1234, communities: 56, routes: 78, coverage_avg: 0.5, coverage_median: 0.42,
  population: 3000000, accessible_population: 1500000, passengers_placeholder: true,
}
const coverage = {
  total: 2,
  results: [
    { community_num: 1, community_name: 'Alpha', population: 1000, accessible_population: 900, geographic_coverage: 0.9 },
    { community_num: 2, community_name: 'Beta', population: 2000, accessible_population: 100, geographic_coverage: 0.1 },
  ],
}

describe('Overview', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading then KPI totals and charts', async () => {
    vi.mocked(data.getKpis).mockResolvedValue(kpis)
    vi.mocked(data.getCoverage).mockResolvedValue(coverage)
    render(<Overview />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(await screen.findByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('56')).toBeInTheDocument()
    expect(screen.getByText('78')).toBeInTheDocument()
    expect(screen.getByText('50.0%')).toBeInTheDocument()
    expect(screen.getByText('42.0%')).toBeInTheDocument()
    expect(screen.getByText('3,000,000')).toBeInTheDocument()
    expect(screen.getAllByTestId('chart').length).toBeGreaterThanOrEqual(2)
  })

  it('shows an error message when getKpis rejects', async () => {
    vi.mocked(data.getKpis).mockRejectedValue(new Error('boom'))
    vi.mocked(data.getCoverage).mockResolvedValue(coverage)
    render(<Overview />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/boom|failed/i)
  })
})
