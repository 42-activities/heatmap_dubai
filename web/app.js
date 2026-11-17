(function () {
  'use strict';

  var DUBAI_CENTER = [25.2, 55.3];
  var DUBAI_ZOOM = 11;

  var map = L.map('map').setView(DUBAI_CENTER, DUBAI_ZOOM);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  var App = {
    map: map,
    stops: [],
    layers: {},   // name -> Leaflet layer; later tasks register theirs here

    showEmptyState: function () {
      document.getElementById('empty-state').hidden = false;
    },

    // Fetch a static JSON file; resolves to parsed data or null on any failure.
    fetchJson: function (path) {
      return fetch(path)
        .then(function (r) { if (!r.ok) throw new Error(path + ' ' + r.status); return r.json(); })
        .catch(function (e) { console.warn('Failed to load ' + path + ':', e.message); return null; });
    },

    // Load stops; returns true if there is data to render.
    loadData: function () {
      return App.fetchJson('data/stops.json').then(function (stops) {
        App.stops = Array.isArray(stops) ? stops : [];
        if (!App.stops.length) { App.showEmptyState(); return false; }
        return true;
      });
    },

    // Add a labelled checkbox to #layer-controls that toggles a layer.
    addToggle: function (name, label, layer, checked) {
      App.layers[name] = layer;
      var wrap = document.createElement('label');
      var box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = !!checked;
      box.addEventListener('change', function () {
        if (box.checked) layer.addTo(map); else map.removeLayer(layer);
      });
      wrap.appendChild(box);
      wrap.appendChild(document.createTextNode(' ' + label));
      document.getElementById('layer-controls').appendChild(wrap);
      if (box.checked) layer.addTo(map);
    },

    // Network heat layer: one point per stop, uniform intensity.
    addNetworkLayer: function () {
      var points = App.stops.map(function (s) { return [s.lat, s.lon]; });
      var layer = L.heatLayer(points, { radius: 12, blur: 15, minOpacity: 0.35, max: 1.0 });
      App.addToggle('network', 'Network (bus stops)', layer, true);
      return layer;
    },

    // ---- Passengers (monthly, 2026) ----
    passengers: null,        // parsed passengers.json (or null)
    month: '2026-01',
    direction: 'in',         // 'in' | 'out'
    passengerGroup: null,    // L.layerGroup: heat layer + invisible hit markers
    passengerHeat: null,
    passengerMax: { in: 1, out: 1 },

    setMonth: function (ym) { App.month = ym; App.updatePassengerLayer(); },
    setDirection: function (dir) { App.direction = dir === 'out' ? 'out' : 'in'; App.updatePassengerLayer(); },

    // Row for a station in a month, or null.
    passengerRow: function (stopId, ym) {
      var rows = App.passengers && App.passengers.stations[String(stopId)];
      if (!rows) return null;
      for (var i = 0; i < rows.length; i++) if (rows[i].month === ym) return rows[i];
      return null;
    },

    // Badge is visible only while the Passengers layer is on the map AND data is placeholder.
    updateBadge: function () {
      var on = App.passengerGroup && map.hasLayer(App.passengerGroup);
      document.getElementById('sample-badge').hidden =
        !(on && App.passengers && App.passengers.placeholder === true);
    },

    // Rebuild the heat layer for the selected month + direction.
    updatePassengerLayer: function () {
      if (!App.passengerGroup || !App.passengers) return;
      map.closePopup();   // avoid a stale-month popup
      var dir = App.direction, max = App.passengerMax[dir] || 1, pts = [];
      App.stops.forEach(function (s) {
        var row = App.passengerRow(s.stop_id, App.month);
        if (!row || !(row[dir] > 0)) return;
        pts.push([s.lat, s.lon, row[dir] / max]);   // weight normalised by max over all months
      });
      if (App.passengerHeat) App.passengerGroup.removeLayer(App.passengerHeat);
      App.passengerHeat = L.heatLayer(pts, { radius: 18, blur: 20, minOpacity: 0.3, max: 1.0 });
      App.passengerGroup.addLayer(App.passengerHeat);
      App.layers.passengerHeat = App.passengerHeat;
    },

    addPassengerLayer: function () {
      return App.fetchJson('data/passengers.json').then(function (data) {
        if (!data || !data.stations) return;
        App.passengers = data;
        // Global max per direction so months are visually comparable.
        var mx = { in: 1, out: 1 };
        Object.keys(data.stations).forEach(function (k) {
          data.stations[k].forEach(function (r) {
            if (r.in > mx.in) mx.in = r.in;
            if (r.out > mx.out) mx.out = r.out;
          });
        });
        App.passengerMax = mx;

        // Invisible canvas circle markers give cheap click popups for ~4k stations.
        var canvas = L.canvas({ padding: 0.5 });
        var markers = App.stops.filter(function (s) {
          return data.stations[String(s.stop_id)];
        }).map(function (s) {
          var m = L.circleMarker([s.lat, s.lon], {
            renderer: canvas, radius: 6, stroke: false, fillOpacity: 0.01, fillColor: '#000'
          });
          m.on('click', function () {
            var row = App.passengerRow(s.stop_id, App.month);
            var html = '<b>' + String(s.stop_name).replace(/</g, '&lt;') + '</b><br>' + App.month +
              '<br>In: ' + (row ? row.in : 'n/a') + '<br>Out: ' + (row ? row.out : 'n/a');
            L.popup().setLatLng(m.getLatLng()).setContent(html).openOn(map);
          });
          return m;
        });

        App.passengerGroup = L.layerGroup(markers);
        App.passengerGroup.on('add remove', App.updateBadge);
        App.addToggle('passengers', 'Passengers (monthly)', App.passengerGroup, false);
        App.updatePassengerLayer();
        App.updateBadge();
        App.initPassengerControls();
      });
    },

    initPassengerControls: function () {
      var box = document.getElementById('passenger-controls');
      var sel = document.getElementById('month-select');
      for (var m = 1; m <= 12; m++) {
        var ym = '2026-' + (m < 10 ? '0' : '') + m;
        var o = document.createElement('option');
        o.value = ym; o.textContent = ym;
        sel.appendChild(o);
      }
      sel.value = App.month;
      sel.addEventListener('change', function () { App.setMonth(sel.value); });
      Array.prototype.forEach.call(document.querySelectorAll('input[name="direction"]'), function (r) {
        r.addEventListener('change', function () { if (r.checked) App.setDirection(r.value); });
      });
      box.hidden = false;
    },
  };

  window.HeatmapApp = App;

  App.loadData().then(function (ok) {
    if (!ok) return;
    App.addNetworkLayer();
    App.addPassengerLayer();
  });
})();
