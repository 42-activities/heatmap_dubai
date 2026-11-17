import { GeoJSON, useMap } from 'react-leaflet'
import type { Feature } from 'geojson'
import type { Layer, PathOptions } from 'leaflet'
import type { CommunityGeoJson, CommunityProperties } from '../../data'

const PANE = 'population'

/** geographic_coverage is a 0-100 percentage. Missing / zero population => neutral grey. */
export function coverageColor(p: Partial<CommunityProperties>): string {
  const cov = p.geographic_coverage
  if (!(Number(p.population) > 0) || typeof cov !== 'number' || !isFinite(cov)) return '#cccccc'
  const c = Math.max(0, Math.min(100, cov))
  return c >= 80 ? '#1a9850' : c >= 60 ? '#91cf60' : c >= 40 ? '#fee08b' : c >= 20 ? '#fc8d59' : '#d73027'
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export function populationTooltip(p: CommunityProperties): string {
  if (p.population === undefined) return `<b>${esc(p.name)}</b><br>No coverage data`
  return (
    `<b>${esc(p.name)}</b><br>Population: ${p.population.toLocaleString()}` +
    `<br>Accessible population: ${(p.accessible_population ?? 0).toLocaleString()}` +
    `<br>Geographic coverage: ${p.geographic_coverage != null ? p.geographic_coverage + '%' : 'n/a'}`
  )
}

export default function PopulationLayer({ geo }: { geo: CommunityGeoJson }) {
  const map = useMap()
  // Own pane keeps polygons under heat layers and station hit-markers.
  if (!map.getPane(PANE)) map.createPane(PANE).style.zIndex = '350'
  return (
    <GeoJSON
      data={geo as unknown as GeoJSON.FeatureCollection}
      pane={PANE}
      style={(f?: Feature): PathOptions => {
        const p = (f?.properties ?? {}) as CommunityProperties
        return { color: '#555', weight: 0.7, fillColor: coverageColor(p), fillOpacity: Number(p.population) > 0 ? 0.6 : 0.25 }
      }}
      onEachFeature={(f: Feature, layer: Layer) => {
        layer.bindTooltip(populationTooltip(f.properties as CommunityProperties), { sticky: true })
      }}
    />
  )
}
