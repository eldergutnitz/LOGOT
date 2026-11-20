const FALLBACK_ROWS = [
  { log_date: "2026-11-18", hostname: "sw-core-01", device: "Gi1/0/11", event_type: "Link down" },
  { log_date: "2026-11-18", hostname: "sw-core-01", device: "Gi1/0/11", event_type: "Link up" },
  { log_date: "2026-11-18", hostname: "sw-core-03", device: "Gi1/0/31", event_type: "WBM" },
  { log_date: "2026-11-18", hostname: "sw-edge-04", device: "Fa0/3", event_type: "Device configuration changed" },
  { log_date: "2026-11-19", hostname: "sw-edge-02", device: "Fa0/7", event_type: "Link down" },
  { log_date: "2026-11-19", hostname: "sw-edge-02", device: "Fa0/7", event_type: "Link up" },
];

const CHART_COLORS = [
  "#ee8158",
  "#a94632",
  "#f2ae76",
  "#804638",
  "#db6d50",
  "#a95d43",
  "#e3bd83",
  "#70463c",
  "#d69a62",
  "#95604d",
];

const charts = {
  events: document.getElementById("eventsChart"),
  devices: document.getElementById("devicesChart"),
  timeline: document.getElementById("timelineChart"),
};

loadDashboard();

async function loadDashboard() {
  try {
    const response = await fetch("/api/syslog/logs?limit=2000");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: /api/syslog/logs?limit=2000`);
    }

    const payload = await response.json();
    const rows = Array.isArray(payload) ? payload : payload.items ?? payload.data;
    if (!Array.isArray(rows)) {
      throw new Error("Formato de respuesta no soportado");
    }

    renderDashboard(rows);
    setStatus(`Conectado: ${rows.length} registros`, "ok");
  } catch (error) {
    console.error(error);
    renderDashboard(FALLBACK_ROWS);
    setStatus("Sin API: usando datos de ejemplo", "error");
  }
}

function renderDashboard(rows) {
  renderStats(rows);
  renderChart(charts.events, countBy(rows, (row) => row.event_type || "OTHER"));
  renderChart(charts.devices, countBy(rows, (row) => row.device || "N/A"));
  renderChart(charts.timeline, countBy(rows, (row) => row.log_date || "Sin fecha"), true);
}

function renderStats(rows) {
  const stats = [
    ["Registros", rows.length],
    ["Tipos de evento", new Set(rows.map((row) => row.event_type).filter(Boolean)).size],
    ["Dispositivos", new Set(rows.map((row) => row.device).filter(Boolean)).size],
    ["Hosts", new Set(rows.map((row) => row.hostname).filter(Boolean)).size],
  ];

  const container = document.getElementById("dashboardStats");
  container.replaceChildren(...stats.map(([label, value]) => {
    const card = document.createElement("article");
    card.className = "stat";
    const title = document.createElement("p");
    title.textContent = label;
    const total = document.createElement("strong");
    total.textContent = value;
    card.append(title, total);
    return card;
  }));
}

function countBy(rows, getKey) {
  const counts = new Map();
  for (const row of rows) {
    const key = getKey(row);
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, 10);
}

function renderChart(container, items, chronological = false) {
  const sortedItems = chronological
    ? [...items].sort((a, b) => a.name.localeCompare(b.name))
    : items;
  container.replaceChildren();

  if (!sortedItems.length) {
    const empty = document.createElement("p");
    empty.className = "chart-empty";
    empty.textContent = "No hay datos para mostrar.";
    container.appendChild(empty);
    return;
  }

  const total = sortedItems.reduce((sum, item) => sum + item.count, 0);
  let offset = 0;
  const slices = sortedItems.map((item, index) => {
    const start = offset;
    offset += (item.count / total) * 100;
    return `${CHART_COLORS[index % CHART_COLORS.length]} ${start}% ${offset}%`;
  });

  const layout = document.createElement("div");
  layout.className = "donut-layout";

  const graph = document.createElement("div");
  graph.className = "donut-graph";
  graph.setAttribute("role", "img");
  graph.setAttribute("aria-label", `${total} registros distribuidos entre ${sortedItems.length} categorías`);
  graph.style.background = `conic-gradient(${slices.join(", ")})`;

  const center = document.createElement("div");
  center.className = "donut-center";
  const totalLabel = document.createElement("strong");
  totalLabel.textContent = total;
  const unitLabel = document.createElement("span");
  unitLabel.textContent = "registros";
  center.append(totalLabel, unitLabel);
  graph.appendChild(center);

  const legend = document.createElement("ol");
  legend.className = "chart-legend";
  sortedItems.forEach((item, index) => {
    const entry = document.createElement("li");
    entry.className = "legend-item";

    const swatch = document.createElement("span");
    swatch.className = "legend-swatch";
    swatch.style.backgroundColor = CHART_COLORS[index % CHART_COLORS.length];

    const label = document.createElement("span");
    label.className = "legend-label";
    label.textContent = item.name;
    label.title = item.name;

    const value = document.createElement("span");
    value.className = "legend-value";
    value.textContent = item.count;

    entry.append(swatch, label, value);
    legend.appendChild(entry);
  });

  layout.append(graph, legend);
  container.appendChild(layout);
}

function setStatus(message, kind) {
  const badge = document.getElementById("statusBadge");
  badge.textContent = message;
  badge.classList.remove("ok", "error");
  badge.classList.add(kind);
}
