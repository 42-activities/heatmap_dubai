export interface Page<T> {
  results: T[]
  total: number
}

export interface PageParams {
  limit?: number
  offset?: number
}

export interface Stop {
  stop_id: number
  stop_name: string
  lat: number
  lon: number
}

export interface Community {
  community_num: number
  community_name: string
}

export interface Route {
  route_name: string
  route_type: string
  stop_count: number
}

export interface Coverage {
  community_num: number
  community_name: string
  population: number
  accessible_population: number
  geographic_coverage: number
}

export interface Kpis {
  stops: number
  communities: number
  routes: number
  coverage_avg: number
  coverage_median: number
  population: number
  accessible_population: number
  passengers_placeholder: boolean
}

export type Direction = 'in' | 'out'

export interface PassengerCount {
  stop_id: number
  count: number
  placeholder: boolean
}

export interface CommunityProperties {
  community_num: number
  name: string
  population?: number
  accessible_population?: number
  geographic_coverage?: number
}

export interface CommunityFeature {
  type: 'Feature'
  properties: CommunityProperties
  geometry: { type: string; coordinates: unknown }
}

export interface CommunityGeoJson {
  type: 'FeatureCollection'
  features: CommunityFeature[]
}

export class TypedError extends Error {
  readonly status?: number
  readonly cause?: unknown
  constructor(message: string, status?: number, options?: { cause?: unknown }) {
    super(message)
    this.name = 'TypedError'
    this.status = status
    this.cause = options?.cause
  }
}

/** The single interface every view uses; identical in API and static modes. */
export interface DataSource {
  getKpis(): Promise<Kpis>
  getStops(p?: PageParams): Promise<Page<Stop>>
  /** Every stop (pages through the API's 1000 cap in API mode). */
  getAllStops(): Promise<Stop[]>
  getRoutes(p?: PageParams): Promise<Page<Route>>
  getCommunities(p?: PageParams): Promise<Page<Community>>
  getCoverage(): Promise<Page<Coverage>>
  getPassengers(month: string, direction: Direction): Promise<Page<PassengerCount>>
  /** Global max count over all months for a direction (for comparable heat intensity). */
  getPassengerMax(direction: Direction): Promise<number>
  getCommunitiesGeoJson(): Promise<CommunityGeoJson>
}
