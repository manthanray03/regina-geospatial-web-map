// Leaflet map for the Regina park amenities API.
// The API runs on the same server, so all requests use relative URLs.

const API = "/api";
const REGINA_CENTRE = [50.4452, -104.6189];

const COLORS = [
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
];

const typeSelect = document.getElementById("type-filter");
const radiusSelect = document.getElementById("radius");
const nearestBtn = document.getElementById("nearest-btn");
const statusText = document.getElementById("status");
const resultsList = document.getElementById("results");

const typeColors = {};
let amenitiesLayer = null;
const searchLayer = L.layerGroup();

// ---------- map setup ----------

const map = L.map("map").setView(REGINA_CENTRE, 12);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors | Data: City of Regina Open Data",
}).addTo(map);

searchLayer.addTo(map);

// ---------- helpers ----------

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function setStatus(message) {
  statusText.textContent = message;
}

// Data from the API goes into popups, so escape it first.
function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function colorFor(type) {
  return typeColors[type] || "#555";
}

function popupHtml(props) {
  let html = `<strong>${escapeHtml(props.amenity_type)}</strong>`;
  if (props.park_name) {
    html += `<br>${escapeHtml(props.park_name)}`;
  }
  if (props.distance_m !== undefined) {
    html += `<br>Distance: ${Math.round(props.distance_m)} m`;
  }
  return html;
}

function formatDistance(metres) {
  return metres >= 1000 ? `${(metres / 1000).toFixed(2)} km` : `${Math.round(metres)} m`;
}

// ---------- loading data ----------

async function loadTypes() {
  const types = await getJson(`${API}/amenities/types`);
  let total = 0;

  types.forEach((t, i) => {
    typeColors[t.amenity_type] = COLORS[i % COLORS.length];
    total += t.count;

    const option = document.createElement("option");
    option.value = t.amenity_type;
    option.textContent = `${t.amenity_type} (${t.count})`;
    typeSelect.appendChild(option);
  });

  typeSelect.options[0].textContent = `All amenities (${total})`;
}

async function loadAmenities() {
  const type = typeSelect.value;
  const url = type
    ? `${API}/amenities?type=${encodeURIComponent(type)}&limit=10000`
    : `${API}/amenities?limit=10000`;

  setStatus("Loading amenities...");
  const data = await getJson(url);

  if (amenitiesLayer) {
    map.removeLayer(amenitiesLayer);
  }

  amenitiesLayer = L.geoJSON(data, {
    pointToLayer: (feature, latlng) =>
      L.circleMarker(latlng, {
        radius: 5,
        weight: 1,
        color: "#fff",
        fillColor: colorFor(feature.properties.amenity_type),
        fillOpacity: 0.9,
      }),
    onEachFeature: (feature, layer) => layer.bindPopup(popupHtml(feature.properties)),
  }).addTo(map);

  setStatus(`Showing ${data.count} amenities. Click the map to search.`);
}

// ---------- searching ----------

function showResults(features, title) {
  resultsList.innerHTML = "";
  setStatus(title);

  features.forEach((feature) => {
    const props = feature.properties;
    const [lon, lat] = feature.geometry.coordinates;

    const marker = L.circleMarker([lat, lon], {
      radius: 8,
      weight: 2,
      color: "#000",
      fillColor: colorFor(props.amenity_type),
      fillOpacity: 1,
    }).bindPopup(popupHtml(props));
    searchLayer.addLayer(marker);

    const item = document.createElement("li");
    item.innerHTML =
          `${escapeHtml(props.park_name || props.amenity_type)}<br>` +
      `<small>${escapeHtml(props.amenity_type)} - ${formatDistance(props.distance_m)}</small>`;
    item.addEventListener("click", () => {
      map.setView([lat, lon], 17);
      marker.openPopup();
    });
    resultsList.appendChild(item);
  });
}

function typeParam() {
  return typeSelect.value ? `&type=${encodeURIComponent(typeSelect.value)}` : "";
}

async function searchNear(latlng) {
  const radius = Number(radiusSelect.value);
  searchLayer.clearLayers();

  L.circle(latlng, { radius, color: "#1f4e79", fillOpacity: 0.08 }).addTo(searchLayer);
  L.marker(latlng).addTo(searchLayer);

  const url =
    `${API}/amenities/near?lat=${latlng.lat.toFixed(6)}&lon=${latlng.lng.toFixed(6)}` +
    `&radius_m=${radius}${typeParam()}`;

  try {
    const data = await getJson(url);
    const label = radius >= 1000 ? `${radius / 1000} km` : `${radius} m`;
    showResults(data.features, `${data.count} amenities within ${label}`);
  } catch (err) {
    setStatus(`Search failed: ${err.message}`);
  }
}

async function findNearest() {
  const centre = map.getCenter();
  searchLayer.clearLayers();
  L.marker(centre).addTo(searchLayer);

  const url =
    `${API}/amenities/nearest?lat=${centre.lat.toFixed(6)}&lon=${centre.lng.toFixed(6)}` +
    `&limit=5${typeParam()}`;

  try {
    const data = await getJson(url);
    showResults(data.features, "5 closest to the map centre");
  } catch (err) {
    setStatus(`Search failed: ${err.message}`);
  }
}

// ---------- events ----------

map.on("click", (e) => searchNear(e.latlng));
nearestBtn.addEventListener("click", findNearest);

typeSelect.addEventListener("change", async () => {
  searchLayer.clearLayers();
  resultsList.innerHTML = "";
  try {
    await loadAmenities();
  } catch (err) {
    setStatus(`Could not load amenities: ${err.message}`);
  }
});

// ---------- start ----------

(async function start() {
  try {
    await loadTypes();
    await loadAmenities();
  } catch (err) {
    setStatus(`Could not reach the API (${err.message}). Is uvicorn running?`);
  }
})();
