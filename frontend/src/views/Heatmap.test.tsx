import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { data } from '../data'
import Heatmap from './Heatmap'

vi.mock('../data', () => ({
  data: { getAllStops: vi.fn(), getPassengers: vi.fn(), getPassengerMax: vi.fn(), getCommunitiesGeoJson: vi.fn() },
}))

// jsdom can't draw a map: stub react-leaflet, leaflet and leaflet.heat.
const heatLayer = vi.hoisted(() => vi.fn((..._a: unknown[]) => ({ addTo: vi.fn().mockReturnThis(), remove: vi.fn() })))
vi.mock('../components/map/leaflet-global', () => ({}))
vi.mock('leaflet.heat', () => ({}))
vi.mock('leaflet', () => {
  const chain = () => ({
    on: vi.fn().mockReturnThis(), addTo: vi.fn().mockReturnThis(), remove: vi.fn(),
    addLayer: vi.fn().mockReturnThis(), clearLayers: vi.fn(), bindPopup: vi.fn().mockReturnThis(),
  })
  const L = { heatLayer, canvas: vi.fn(() => ({ remove: vi.fn() })), circleMarker: vi.fn(chain), layerGroup: vi.fn(chain) }
  return { default: L, ...L }
})
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  GeoJSON: () => <div data-testid="choropleth" />,
  useMap: () => ({ closePopup: vi.fn(), createPane: vi.fn(), getPane: vi.fn(() => ({ style: {} })) }),
}))

const stops = [
  { stop_id: 1, stop_name: 'A', lat: 25.1, lon: 55.1 },
  { stop_id: 2, stop_name: 'B', lat: 25.2, lon: 55.2 },
]
const pax = (placeholder: boolean) => ({
  total: 2,
  results: [{ stop_id: 1, count: 10, placeholder }, { stop_id: 2, count: 5, placeholder }],
})
const geo = { type: 'FeatureCollection' as const, features: [] }

describe('Heatmap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(data.getAllStops).mockResolvedValue(stops)
    vi.mocked(data.getPassengers).mockResolvedValue(pax(true))
    vi.mocked(data.getCommunitiesGeoJson).mockResolvedValue(geo)
    vi.mocked(data.getPassengerMax).mockResolvedValue(20)
  })

  it('shows loading, then the three layer toggles, month selector and direction control', async () => {
    render(<Heatmap />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/network/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/passengers/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/population/i)).toBeInTheDocument()
    const opts = within(screen.getByRole('combobox', { name: /month/i })).getAllByRole('option').map((o) => (o as HTMLOptionElement).value)
    expect(opts).toEqual(Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`))
    expect(screen.getByRole('radio', { name: /^in$/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /^out$/i })).toBeInTheDocument()
  })

  it('shows the SAMPLE badge only while Passengers is on and data is placeholder', async () => {
    render(<Heatmap />)
    await screen.findByLabelText(/network/i)
    expect(screen.queryByText(/sample data/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/passengers/i))
    expect(await screen.findByText(/sample data/i)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/passengers/i))
    expect(screen.queryByText(/sample data/i)).not.toBeInTheDocument()
  })

  it('hides the badge when passenger data is not placeholder', async () => {
    vi.mocked(data.getPassengers).mockResolvedValue(pax(false))
    render(<Heatmap />)
    await screen.findByLabelText(/network/i)
    fireEvent.click(screen.getByLabelText(/passengers/i))
    await waitFor(() => expect(data.getPassengers).toHaveBeenCalled())
    expect(screen.queryByText(/sample data/i)).not.toBeInTheDocument()
  })

  it('rebuilds weighted passenger heat on month change; empty month does not throw', async () => {
    render(<Heatmap />)
    await screen.findByLabelText(/network/i)
    fireEvent.click(screen.getByLabelText(/passengers/i))
    await waitFor(() => expect(data.getPassengers).toHaveBeenCalledWith('2026-01', 'in'))
    // weights use the GLOBAL max (20), not this month's max (10)
    await waitFor(() => expect(heatLayer).toHaveBeenCalledWith([[25.1, 55.1, 0.5], [25.2, 55.2, 0.25]], expect.anything()))
    const weighted = heatLayer.mock.results.at(-1)!.value as { remove: ReturnType<typeof vi.fn> }
    vi.mocked(data.getPassengers).mockResolvedValue({ results: [], total: 0 })
    fireEvent.change(screen.getByRole('combobox', { name: /month/i }), { target: { value: '2026-07' } })
    await waitFor(() => expect(data.getPassengers).toHaveBeenCalledWith('2026-07', 'in'))
    // let the (empty) fetch resolve, then the empty layer must be the latest build
    await vi.mocked(data.getPassengers).mock.results.at(-1)!.value
    await waitFor(() => expect(heatLayer).toHaveBeenLastCalledWith([], expect.anything()))
    expect(weighted.remove).toHaveBeenCalled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/passengers/i)).toBeInTheDocument()
  })

  it('shows an error when stops fail to load', async () => {
    vi.mocked(data.getAllStops).mockRejectedValue(new Error('boom'))
    render(<Heatmap />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/boom|failed/i)
  })
})
