const datasets = [
  { name: 'Bus stops', id: 'rta_bus_stop_details-open-api', note: 'Stop master: names, coordinates, amenities.', real: true },
  { name: 'Bus routes', id: 'rta_bus_routes-open-api', note: 'Route to stop sequence (route/stop bridge).', real: true },
  { name: 'Network coverage', id: 'rta_bus_network_coverage-open-api', note: 'Community-level coverage % and population within 400 m.', real: true },
  { name: 'Community boundaries', id: 'Dubai Pulse open data', note: 'GeoJSON polygons for the coverage choropleth.', real: true },
  { name: 'Monthly passengers (2026)', id: 'rta_bus_ridership-open-api', note: 'Placeholder values per stop and month.', real: false },
]

export default function Data() {
  return (
    <section>
      <h1>Data</h1>
      <p>
        Stops, routes and coverage come from the Dubai RTA open APIs (STG gateway snapshot). The
        passenger figures are not real ridership.
      </p>

      <h2>Datasets</h2>
      <div className="kpis">
        {datasets.map((d) => (
          <div className="kpi" key={d.name}>
            <div className="kpi__label">
              {d.name}
              {!d.real && <span className="badge-sample">SAMPLE</span>}
            </div>
            <div className="kpi__sub">{d.id}</div>
            <div>{d.note}</div>
          </div>
        ))}
      </div>

      <h2>Real vs placeholder</h2>
      <p className="error" role="note">
        Passenger counts are <strong>SAMPLE data</strong> until PROD ridership access is granted
        (STG exposes a single ridership row). Do not draw conclusions from the passenger layer.
        Stops, routes and coverage are real STG data.
      </p>

      <h2>Attribution</h2>
      <ul>
        <li>Bus stops, routes, ridership and network coverage: Roads and Transport Authority (RTA) via Dubai Data.</li>
        <li>Community boundaries: &copy; Dubai Municipality, via Dubai Pulse open data.</li>
        <li>Basemap: &copy; OpenStreetMap contributors.</li>
      </ul>

      <h2>Regenerating data</h2>
      <ol>
        <li>Put credentials in <code>.env</code> (<code>ENVIRONMENT=STG</code> or <code>PROD</code>).</li>
        <li>Run <code>python3 scripts/export_web_data.py</code> to rebuild <code>web/data/*.json</code>.</li>
        <li>Reseed Postgres with <code>make refresh</code>; static builds bundle the JSON at build time.</li>
        <li>STG to PROD: switch <code>ENVIRONMENT=PROD</code>, verify the PROD token URL, and replace the placeholder passenger generator with real ridership aggregates.</li>
      </ol>
    </section>
  )
}
