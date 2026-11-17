import L from 'leaflet'

// leaflet.heat attaches itself to the global `L`; guarantee it exists whatever build of leaflet is resolved.
;(window as unknown as { L?: typeof L }).L ??= L
