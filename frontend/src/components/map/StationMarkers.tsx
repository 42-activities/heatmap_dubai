import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { useMap } from 'react-leaflet'
import type { Stop } from '../../data'

export interface StationCounts {
  month: string
  in: Map<number, number>
  out: Map<number, number>
}

interface Props {
  stops: Stop[]
  counts: StationCounts | null
}

/** Invisible canvas hit-markers (cheap for ~4k stops) that open a popup with the month's in/out counts. */
export default function StationMarkers({ stops, counts }: Props) {
  const map = useMap()
  const countsRef = useRef(counts)
  countsRef.current = counts

  useEffect(() => {
    const renderer = L.canvas({ padding: 0.5 })
    const group = L.layerGroup()
    for (const s of stops) {
      const m = L.circleMarker([s.lat, s.lon], {
        renderer, radius: 6, stroke: false, fillOpacity: 0.01, fillColor: '#000',
      })
      m.bindPopup(() => {
        const c = countsRef.current
        const el = document.createElement('div')
        const name = document.createElement('b')
        name.textContent = s.stop_name
        el.append(name)
        const line = (label: string, v: number | undefined) => {
          el.append(document.createElement('br'), `${label}: ${v === undefined ? 'n/a' : v.toLocaleString()}`)
        }
        if (c) el.append(document.createElement('br'), c.month)
        line('In', c?.in.get(s.stop_id))
        line('Out', c?.out.get(s.stop_id))
        return el
      })
      group.addLayer(m)
    }
    group.addTo(map)
    return () => {
      map.closePopup()
      group.remove()
      renderer.remove()
    }
  }, [map, stops])

  // Avoid a stale-month popup when the selection changes.
  useEffect(() => {
    map.closePopup()
  }, [map, counts])
  return null
}
