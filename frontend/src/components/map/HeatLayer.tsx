import { useEffect } from 'react'
import L from 'leaflet'
import './leaflet-global'
import 'leaflet.heat'
import { useMap } from 'react-leaflet'

export type HeatPoint = [number, number, number?]

interface Props {
  points: HeatPoint[]
  radius?: number
  blur?: number
  minOpacity?: number
}

/** Thin react-leaflet wrapper for leaflet.heat: (re)builds the layer when points/options change. */
export default function HeatLayer({ points, radius = 12, blur = 15, minOpacity = 0.35 }: Props) {
  const map = useMap()
  useEffect(() => {
    const layer = L.heatLayer(points as L.HeatLatLng[], { radius, blur, minOpacity, max: 1.0 })
    layer.addTo(map)
    return () => {
      layer.remove()
    }
  }, [map, points, radius, blur, minOpacity])
  return null
}
