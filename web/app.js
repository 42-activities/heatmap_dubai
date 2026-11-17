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
    }
  };

  window.HeatmapApp = App;

  App.loadData().then(function (ok) {
    if (!ok) return;
    App.addNetworkLayer();
  });
})();
