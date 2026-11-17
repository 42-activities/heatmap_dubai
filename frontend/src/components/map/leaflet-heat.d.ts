declare module 'leaflet.heat'

declare namespace L {
  type HeatLatLng = [number, number] | [number, number, number]
  interface HeatLayerOptions {
    minOpacity?: number
    maxZoom?: number
    max?: number
    radius?: number
    blur?: number
    gradient?: Record<number, string>
  }
  function heatLayer(latlngs: HeatLatLng[], options?: HeatLayerOptions): Layer
}
