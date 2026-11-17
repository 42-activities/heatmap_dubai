import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApi } from './api'
import { TypedError } from './types'

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

describe('api adapter', () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => vi.unstubAllGlobals())
  const api = createApi('/api')

  it('getPassengers hits the endpoint and returns the Page shape', async () => {
    fetchMock.mockResolvedValue(
      ok({ results: [{ stop_id: 1, month: '2026-01', direction: 'in', count: 5, placeholder: true }], total: 1 }),
    )
    const r = await api.getPassengers('2026-01', 'in')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/passengers?month=2026-01&direction=in')
    expect(r).toEqual({ results: [{ stop_id: 1, count: 5, placeholder: true }], total: 1 })
  })

  it('getStops passes limit/offset', async () => {
    fetchMock.mockResolvedValue(ok({ results: [], total: 0 }))
    await api.getStops({ limit: 10, offset: 20 })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/stops?limit=10&offset=20')
  })

  it('getKpis returns the payload', async () => {
    const k = { stops: 1, communities: 2, routes: 3, coverage_avg: 1, coverage_median: 1, population: 1, accessible_population: 1, passengers_placeholder: true }
    fetchMock.mockResolvedValue(ok(k))
    expect(await api.getKpis()).toEqual(k)
  })

  it('throws TypedError on non-ok response', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) })
    await expect(api.getKpis()).rejects.toBeInstanceOf(TypedError)
    await expect(api.getKpis()).rejects.toMatchObject({ status: 500 })
  })

  it('throws TypedError on rejected fetch', async () => {
    fetchMock.mockRejectedValue(new TypeError('network'))
    await expect(api.getCoverage()).rejects.toBeInstanceOf(TypedError)
  })
})
