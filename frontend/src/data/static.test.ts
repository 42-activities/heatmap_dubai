import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createStatic } from './static'
import { TypedError } from './types'

const files: Record<string, unknown> = {
  'stops.json': [
    { stop_id: 1, stop_name: 'A', lat: 25, lon: 55 },
    { stop_id: 2, stop_name: 'B', lat: 25.1, lon: 55.1 },
    { stop_id: 3, stop_name: 'C', lat: 25.2, lon: 55.2 },
  ],
  'routes.json': [
    { route_name: '10', route_type: 'Urban', stop_count: 2 },
    { route_name: '11', route_type: 'Urban', stop_count: 3 },
  ],
  'coverage.json': [
    { community_num: 101, community_name: 'X', population: 100, accessible_population: 50, geographic_coverage: 10 },
    { community_num: 102, community_name: 'Y', population: 200, accessible_population: 150, geographic_coverage: 20 },
    { community_num: 103, community_name: 'Z', population: 300, accessible_population: 300, geographic_coverage: 90 },
    { community_num: 104, community_name: 'W', population: 0, accessible_population: 0, geographic_coverage: 40 },
  ],
  'passengers.json': {
    placeholder: true,
    year: 2026,
    stations: {
      '2': [{ month: '2026-01', in: 20, out: 21 }, { month: '2026-02', in: 22, out: 23 }],
      '1': [{ month: '2026-01', in: 10, out: 11 }, { month: '2026-02', in: 12, out: 13 }],
    },
  },
  'communities.geojson': {
    type: 'FeatureCollection',
    features: [
      { type: 'Feature', properties: { community_num: 101, name: 'X' }, geometry: { type: 'Point', coordinates: [0, 0] } },
      { type: 'Feature', properties: { community_num: 999, name: 'NoCov' }, geometry: { type: 'Point', coordinates: [1, 1] } },
    ],
  },
}

describe('static adapter', () => {
  const fetchMock = vi.fn()
  let st: ReturnType<typeof createStatic>
  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockImplementation(async (url: string) => {
      const name = url.split('/').pop()!
      return name in files
        ? { ok: true, status: 200, json: async () => files[name] }
        : { ok: false, status: 404, json: async () => ({}) }
    })
    vi.stubGlobal('fetch', fetchMock)
    st = createStatic('/base/')
  })
  afterEach(() => vi.unstubAllGlobals())

  it('getPassengerMax returns the global max over all stations and months per direction', async () => {
    expect(await st.getPassengerMax('in')).toBe(22)
    expect(await st.getPassengerMax('out')).toBe(23)
  })

  it('reads from BASE_URL/data', async () => {
    await st.getStops()
    expect(fetchMock.mock.calls[0][0]).toBe('/base/data/stops.json')
  })

  it('getPassengers un-pivots to the API shape, sorted by stop_id', async () => {
    expect(await st.getPassengers('2026-01', 'in')).toEqual({
      results: [
        { stop_id: 1, count: 10, placeholder: true },
        { stop_id: 2, count: 20, placeholder: true },
      ],
      total: 2,
    })
    const out = await st.getPassengers('2026-02', 'out')
    expect(out.results.map((r) => r.count)).toEqual([13, 23])
  })

  it('getStops paginates and reports full total', async () => {
    const p = await st.getStops({ limit: 2, offset: 1 })
    expect(p.total).toBe(3)
    expect(p.results.map((s) => s.stop_id)).toEqual([2, 3])
  })

  it('getCommunities derives from coverage', async () => {
    const p = await st.getCommunities()
    expect(p.total).toBe(4)
    expect(p.results[0]).toEqual({ community_num: 101, community_name: 'X' })
  })

  it('getKpis is computed from fixtures', async () => {
    expect(await st.getKpis()).toEqual({
      stops: 3,
      communities: 4,
      routes: 2,
      coverage_avg: 40,
      coverage_median: 30,
      population: 600,
      accessible_population: 500,
      passengers_placeholder: true,
    })
  })

  it('getCommunitiesGeoJson merges coverage by community_num', async () => {
    const g = await st.getCommunitiesGeoJson()
    expect(g.features[0].properties).toEqual({
      community_num: 101,
      name: 'X',
      population: 100,
      accessible_population: 50,
      geographic_coverage: 10,
    })
    expect(g.features[1].properties).toEqual({ community_num: 999, name: 'NoCov' })
  })

  it('throws TypedError on 404 and on rejected fetch', async () => {
    fetchMock.mockImplementation(async () => ({ ok: false, status: 404, json: async () => ({}) }))
    st = createStatic('/base/')
    await expect(st.getRoutes()).rejects.toBeInstanceOf(TypedError)
    fetchMock.mockRejectedValue(new TypeError('offline'))
    st = createStatic('/base/')
    await expect(st.getCoverage()).rejects.toBeInstanceOf(TypedError)
  })

  it('getAllStops returns every stop', async () => {
    expect(await st.getAllStops()).toHaveLength(3)
  })

  it('bare getStops defaults to limit 100 like the backend', async () => {
    files['stops.json'] = Array.from({ length: 150 }, (_, i) => ({ stop_id: i, stop_name: 's', lat: 0, lon: 0 }))
    st = createStatic('/base/')
    const p = await st.getStops()
    expect(p.results).toHaveLength(100)
    expect(p.total).toBe(150)
    expect(await st.getAllStops()).toHaveLength(150)
  })
})
