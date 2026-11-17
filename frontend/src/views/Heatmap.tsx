import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { data } from '../data'
import type { CommunityGeoJson, Direction, Stop } from '../data'
import HeatLayer from '../components/map/HeatLayer'
import type { HeatPoint } from '../components/map/HeatLayer'
import PopulationLayer from '../components/map/PopulationLayer'
import StationMarkers from '../components/map/StationMarkers'
import type { StationCounts } from '../components/map/StationMarkers'

const DUBAI_CENTER: [number, number] = [25.2, 55.3]
const MONTHS = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, '0')}`)

interface Passengers extends StationCounts {
  placeholder: boolean
}

const toMap = (rows: { stop_id: number; count: number }[]) => new Map(rows.map((r) => [r.stop_id, r.count]))
const msg = (e: unknown) => (e instanceof Error ? e.message : 'Failed to load data')

export default function Heatmap() {
  const [stops, setStops] = useState<Stop[] | null>(null)
  const [geo, setGeo] = useState<CommunityGeoJson | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showNetwork, setShowNetwork] = useState(true)
  const [showPassengers, setShowPassengers] = useState(false)
  const [showPopulation, setShowPopulation] = useState(false)
  const [month, setMonth] = useState(MONTHS[0])
  const [direction, setDirection] = useState<Direction>('in')
  const [pax, setPax] = useState<Passengers | null>(null)
  const [paxError, setPaxError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    Promise.all([data.getAllStops(), data.getCommunitiesGeoJson()])
      .then(([s, g]) => {
        if (!live) return
        setStops(s)
        setGeo(g)
      })
      .catch((e) => live && setError(msg(e)))
    return () => {
      live = false
    }
  }, [])

  // Fetch the month's counts (both directions, for popups) while the Passengers layer is on.
  useEffect(() => {
    if (!showPassengers) return
    let live = true
    setPaxError(null)
    Promise.all([data.getPassengers(month, 'in'), data.getPassengers(month, 'out')])
      .then(([i, o]) => {
        if (!live) return
        setPax({
          month,
          in: toMap(i.results),
          out: toMap(o.results),
          placeholder: [...i.results, ...o.results].some((r) => r.placeholder),
        })
      })
      .catch((e) => live && setPaxError(msg(e)))
    return () => {
      live = false
    }
  }, [showPassengers, month])

  const networkPoints = useMemo<HeatPoint[]>(() => (stops ?? []).map((s) => [s.lat, s.lon]), [stops])

  // Weight normalised by the max of the selected month + direction; empty month => no points.
  const passengerPoints = useMemo<HeatPoint[]>(() => {
    if (!stops || !pax || pax.month !== month) return []
    const counts = pax[direction]
    let max = 1
    for (const v of counts.values()) if (v > max) max = v
    const pts: HeatPoint[] = []
    for (const s of stops) {
      const c = counts.get(s.stop_id)
      if (c && c > 0) pts.push([s.lat, s.lon, c / max])
    }
    return pts
  }, [stops, pax, month, direction])

  if (error || !stops || !geo) {
    return (
      <section className="heatmap">
        <h1>Heatmap</h1>
        {error ? <p role="alert" className="error">Failed to load map data: {error}</p> : <p>Loading map…</p>}
      </section>
    )
  }

  const badge = showPassengers && pax?.placeholder === true
  return (
    <section className="heatmap">
      <h1>Heatmap</h1>
      <div className="map-controls">
        <label><input type="checkbox" checked={showNetwork} onChange={(e) => setShowNetwork(e.target.checked)} /> Network (bus stops)</label>
        <label><input type="checkbox" checked={showPassengers} onChange={(e) => setShowPassengers(e.target.checked)} /> Passengers (monthly)</label>
        <label><input type="checkbox" checked={showPopulation} onChange={(e) => setShowPopulation(e.target.checked)} /> Population / bus coverage</label>
        <div className="map-controls__passengers">
          <label>Month{' '}
            <select aria-label="Month" disabled={!showPassengers} value={month} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
          <label><input type="radio" name="direction" disabled={!showPassengers} value="in" checked={direction === 'in'} onChange={() => setDirection('in')} /> In</label>
          <label><input type="radio" name="direction" disabled={!showPassengers} value="out" checked={direction === 'out'} onChange={() => setDirection('out')} /> Out</label>
          {paxError && <span role="alert" className="error">Passenger data failed: {paxError}</span>}
        </div>
      </div>
      <div className="map-wrap">
        <MapContainer center={DUBAI_CENTER} zoom={11} className="map">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {showPopulation && <PopulationLayer geo={geo} />}
          {showNetwork && <HeatLayer points={networkPoints} radius={12} blur={15} minOpacity={0.35} />}
          {showPassengers && <HeatLayer points={passengerPoints} radius={18} blur={20} minOpacity={0.3} />}
          {showPassengers && <StationMarkers stops={stops} counts={pax} />}
        </MapContainer>
        {badge && <div className="sample-badge" role="status">SAMPLE DATA</div>}
      </div>
    </section>
  )
}
