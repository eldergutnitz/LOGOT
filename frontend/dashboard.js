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
    const response = await fetch("/api/syslog/stats");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: /api/syslog/stats`);
    }

    const stats = await response.json();
    renderDashboard(stats);
    setStatus(`Conectado: ${stats.total} registros totales`, "ok");
  } catch (error) {
    console.error(error);
    renderFallbackDashboard();
    setStatus("Sin API: usando datos de ejemplo", "error");
  }
}

function renderDashboard(stats) {
  renderStatsFromApi(stats);
  renderChart(charts.events, stats.event_distribution || []);
  renderChart(charts.devices, stats.device_distribution || []);
  renderChart(charts.timeline, stats.timeline_distribution || [], true);
}

function renderStatsFromApi(stats) {
  const values = [
    ["Registros", stats.total],
    ["Tipos de evento", stats.event_types],
    ["Dispositivos", stats.devices],
    ["Hosts", stats.hosts],
  ];

  const container = document.getElementById("dashboardStats");
  container.replaceChildren(...values.map(([label, value]) => {
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

function renderFallbackDashboard() {
  renderDashboard({
    total: 0,
    event_types: 0,
    devices: 0,
    hosts: 0,
    event_distribution: [],
    device_distribution: [],
    timeline_distribution: [],
  });
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
