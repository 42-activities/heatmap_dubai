import {
  TypedError,
  type Community,
  type CommunityGeoJson,
  type Coverage,
  type DataSource,
  type Direction,
  type Kpis,
  type Page,
  type PageParams,
  type PassengerCount,
  type Route,
  type Stop,
} from './types'

export function createApi(base: string): DataSource {
  async function get<T>(path: string): Promise<T> {
    let res: Response
    try {
      res = await fetch(`${base}${path}`)
    } catch (e) {
      throw new TypedError(`Network error fetching ${path}`, undefined, { cause: e })
    }
    if (!res.ok) throw new TypedError(`Request failed (${res.status}) for ${path}`, res.status)
    try {
      return (await res.json()) as T
    } catch (e) {
      throw new TypedError(`Invalid JSON from ${path}`, res.status, { cause: e })
    }
  }

  const qs = (p?: PageParams) => {
    const q = new URLSearchParams()
    if (p?.limit !== undefined) q.set('limit', String(p.limit))
    if (p?.offset !== undefined) q.set('offset', String(p.offset))
    const s = q.toString()
    return s ? `?${s}` : ''
  }

  const maxCache = new Map<Direction, Promise<number>>()
  const MONTHS = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`)

  const api: DataSource = {
    getKpis: () => get<Kpis>('/kpis'),
    getStops: (p) => get<Page<Stop>>(`/stops${qs(p)}`),
    async getAllStops() {
      const LIMIT = 1000
      const all: Stop[] = []
      for (;;) {
        const page = await get<Page<Stop>>(`/stops?limit=${LIMIT}&offset=${all.length}`)
        all.push(...page.results)
        if (page.results.length < LIMIT || all.length >= page.total) return all
      }
    },
    getRoutes: (p) => get<Page<Route>>(`/routes${qs(p)}`),
    getCommunities: (p) => get<Page<Community>>(`/communities${qs(p)}`),
    getCoverage: () => get<Page<Coverage>>('/coverage'),
    async getPassengers(month, direction) {
      const raw = await get<Page<PassengerCount>>(
        `/passengers?month=${encodeURIComponent(month)}&direction=${direction}`,
      )
      return {
        results: raw.results.map(({ stop_id, count, placeholder }) => ({ stop_id, count, placeholder })),
        total: raw.total,
      }
    },
    getPassengerMax(direction) {
      let p = maxCache.get(direction)
      if (!p) {
        p = Promise.all(MONTHS.map((m) => api.getPassengers(m, direction))).then((pages) =>
          pages.reduce((mx, pg) => pg.results.reduce((a, r) => Math.max(a, r.count), mx), 0),
        )
        p.catch(() => maxCache.delete(direction)) // do not cache failures
        maxCache.set(direction, p)
      }
      return p
    },
    getCommunitiesGeoJson: () => get<CommunityGeoJson>('/communities.geojson'),
  }
  return api
}
