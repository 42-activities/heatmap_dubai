import {
  TypedError,
  type Community,
  type CommunityGeoJson,
  type Coverage,
  type DataSource,
  type Page,
  type PageParams,
  type Route,
  type Stop,
} from './types'

interface PassengersFile {
  placeholder: boolean
  year: number
  stations: Record<string, { month: string; in: number; out: number }[]>
}

// Matches the backend's default page size so bare calls behave the same in both modes.
const DEFAULT_LIMIT = 100

function paginate<T>(all: T[], p?: PageParams): Page<T> {
  const offset = p?.offset ?? 0
  const end = offset + (p?.limit ?? DEFAULT_LIMIT)
  return { results: all.slice(offset, end), total: all.length }
}

function median(sorted: number[]): number {
  if (!sorted.length) return 0
  const m = sorted.length >> 1
  return sorted.length % 2 ? sorted[m] : (sorted[m - 1] + sorted[m]) / 2
}

export function createStatic(baseUrl: string): DataSource {
  const cache = new Map<string, Promise<unknown>>()

  function load<T>(file: string): Promise<T> {
    let p = cache.get(file)
    if (!p) {
      const url = `${baseUrl}data/${file}`
      p = (async () => {
        let res: Response
        try {
          res = await fetch(url)
        } catch (e) {
          throw new TypedError(`Network error fetching ${url}`, undefined, { cause: e })
        }
        if (!res.ok) throw new TypedError(`Request failed (${res.status}) for ${url}`, res.status)
        try {
          return await res.json()
        } catch (e) {
          throw new TypedError(`Invalid JSON from ${url}`, res.status, { cause: e })
        }
      })()
      // do not cache failures
      p.catch(() => cache.delete(file))
      cache.set(file, p)
    }
    return p as Promise<T>
  }

  const coverage = () => load<Coverage[]>('coverage.json')

  return {
    async getKpis() {
      const [stops, routes, cov, pax] = await Promise.all([
        load<Stop[]>('stops.json'),
        load<Route[]>('routes.json'),
        coverage(),
        load<PassengersFile>('passengers.json'),
      ])
      const vals = cov.map((c) => c.geographic_coverage).sort((a, b) => a - b)
      return {
        stops: stops.length,
        communities: cov.length,
        routes: routes.length,
        coverage_avg: vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0,
        coverage_median: median(vals),
        population: cov.reduce((a, c) => a + c.population, 0),
        accessible_population: cov.reduce((a, c) => a + c.accessible_population, 0),
        passengers_placeholder: pax.placeholder,
      }
    },
    async getStops(p) {
      return paginate(await load<Stop[]>('stops.json'), p)
    },
    async getAllStops() {
      return load<Stop[]>('stops.json')
    },
    async getRoutes(p) {
      return paginate(await load<Route[]>('routes.json'), p)
    },
    async getCommunities(p) {
      const cov = await coverage()
      const all: Community[] = cov.map(({ community_num, community_name }) => ({ community_num, community_name }))
      return paginate(all, p)
    },
    async getCoverage() {
      const all = await coverage()
      return { results: all, total: all.length }
    },
    async getPassengers(month, direction) {
      const pax = await load<PassengersFile>('passengers.json')
      const results = []
      for (const [id, months] of Object.entries(pax.stations)) {
        const row = months.find((m) => m.month === month)
        if (row) results.push({ stop_id: Number(id), count: row[direction], placeholder: pax.placeholder })
      }
      results.sort((a, b) => a.stop_id - b.stop_id)
      return { results, total: results.length }
    },
    async getPassengerMax(direction) {
      const pax = await load<PassengersFile>('passengers.json')
      let max = 0
      for (const rows of Object.values(pax.stations)) for (const r of rows) if (r[direction] > max) max = r[direction]
      return max
    },
    async getCommunitiesGeoJson() {
      const [geo, cov] = await Promise.all([load<CommunityGeoJson>('communities.geojson'), coverage()])
      const byNum = new Map(cov.map((c) => [c.community_num, c]))
      return {
        ...geo,
        features: geo.features.map((f) => {
          const c = byNum.get(f.properties.community_num)
          return c
            ? {
                ...f,
                properties: {
                  ...f.properties,
                  population: c.population,
                  accessible_population: c.accessible_population,
                  geographic_coverage: c.geographic_coverage,
                },
              }
            : f
        }),
      }
    },
  }
}
