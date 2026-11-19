const state = {
  view: "detalle",
  rows: [],
  filteredRows: [],
  loading: false,
  error: "",
};

const el = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  loadButton: document.getElementById("loadButton"),
  viewSelector: document.getElementById("viewSelector"),
  searchInput: document.getElementById("searchInput"),
  eventTypeFilter: document.getElementById("eventTypeFilter"),
  fromDate: document.getElementById("fromDate"),
  toDate: document.getElementById("toDate"),
  viewTitle: document.getElementById("viewTitle"),
  viewContainer: document.getElementById("viewContainer"),
  statusBadge: document.getElementById("statusBadge"),
  statsStrip: document.getElementById("statsStrip"),
  emptyTemplate: document.getElementById("emptyTemplate"),
};

const viewTitles = {
  detalle: "Vista Detalle",
  eventos: "Vista por tipos de evento",
  dispositivos: "Vista por dispositivo",
  timeline: "Vista timeline",
};

const FALLBACK_ROWS = [
  { id: 1, log_date: "2026-11-18", log_time: "08:32:10", hostname: "sw-core-01", device: "Gi1/0/11", process_id: 1212, event_type: "Link down", message: "Link down on Gi1/0/11" },
  { id: 2, log_date: "2026-11-18", log_time: "08:34:16", hostname: "sw-core-01", device: "Gi1/0/11", process_id: 1212, event_type: "Link up", message: "Link up on Gi1/0/11" },
  { id: 3, log_date: "2026-11-18", log_time: "09:04:42", hostname: "sw-core-03", device: "Gi1/0/31", process_id: 981, event_type: "WBM", message: "WBM health warning" },
  { id: 4, log_date: "2026-11-18", log_time: "09:20:03", hostname: "sw-edge-04", device: "Fa0/3", process_id: 2102, event_type: "Device configuration changed", message: "Device configuration changed by admin" },
  { id: 5, log_date: "2026-11-19", log_time: "07:11:31", hostname: "sw-edge-02", device: "Fa0/7", process_id: 1301, event_type: "Link down", message: "Link down on Fa0/7" },
  { id: 6, log_date: "2026-11-19", log_time: "07:14:58", hostname: "sw-edge-02", device: "Fa0/7", process_id: 1301, event_type: "Link up", message: "Link up on Fa0/7" },
];

init();

function init() {
  wireEvents();
  renderStats();
  loadData();
}

function wireEvents() {
  el.loadButton.addEventListener("click", loadData);

  el.viewSelector.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-view]");
    if (!btn) return;

    state.view = btn.dataset.view;

    for (const segment of el.viewSelector.querySelectorAll(".segment")) {
      const active = segment === btn;
      segment.classList.toggle("active", active);
      segment.setAttribute("aria-selected", active ? "true" : "false");
    }

    render();
  });

  [el.searchInput, el.eventTypeFilter, el.fromDate, el.toDate].forEach((control) => {
    control.addEventListener("input", applyFiltersAndRender);
    control.addEventListener("change", applyFiltersAndRender);
  });
}

async function loadData() {
  setLoading(true);
  setStatus("Cargando datos...", "");

  try {
    const apiBase = sanitizeApiBase(el.apiBaseUrl.value);
    const rows = await fetchRows(apiBase);

    state.rows = normalizeRows(rows);
    populateEventTypeFilter(state.rows);

    applyFiltersAndRender();
    setStatus(`Conectado: ${state.rows.length} registros`, "ok");
  } catch (error) {
    console.error(error);
    // Fallback local for offline demos and first-run UX.
    state.rows = normalizeRows(FALLBACK_ROWS);
    populateEventTypeFilter(state.rows);

    applyFiltersAndRender();
    setStatus("Sin API: usando datos de ejemplo", "error");
  } finally {
    setLoading(false);
  }
}

function sanitizeApiBase(rawValue) {
  const value = (rawValue || "").trim();
  if (!value) return "/api";
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

async function fetchRows(apiBase) {
  const url = `${apiBase}/syslog/logs?limit=2000`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${url}`);
  }

  const payload = await response.json();
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.data)) return payload.data;

  throw new Error("Formato de respuesta no soportado");
}

function normalizeRows(rows) {
  return rows.map((row, idx) => ({
    id: row.id ?? idx + 1,
    log_date: row.log_date ?? "",
    log_time: row.log_time ?? "",
    hostname: row.hostname ?? "",
    device: row.device ?? "",
    process_id: row.process_id ?? "",
    event_type: row.event_type ?? "OTHER",
    message: row.message ?? "",
  }));
}

function populateEventTypeFilter(rows) {
  const current = el.eventTypeFilter.value;
  const unique = [...new Set(rows.map((x) => x.event_type).filter(Boolean))].sort((a, b) => a.localeCompare(b));

  el.eventTypeFilter.innerHTML = "<option value=\"\">Todos</option>";
  for (const eventType of unique) {
    const option = document.createElement("option");
    option.value = eventType;
    option.textContent = eventType;
    el.eventTypeFilter.appendChild(option);
  }

  if (unique.includes(current)) {
    el.eventTypeFilter.value = current;
  }
}

function applyFiltersAndRender() {
  const q = el.searchInput.value.trim().toLowerCase();
  const eventType = el.eventTypeFilter.value;
  const fromDate = el.fromDate.value;
  const toDate = el.toDate.value;

  state.filteredRows = state.rows.filter((row) => {
    const date = row.log_date || "";

    if (eventType && row.event_type !== eventType) return false;
    if (fromDate && date && date < fromDate) return false;
    if (toDate && date && date > toDate) return false;

    if (q) {
      const bag = `${row.hostname} ${row.device} ${row.message} ${row.event_type}`.toLowerCase();
      if (!bag.includes(q)) return false;
    }

    return true;
  });

  renderStats();
  render();
}

function renderStats() {
  const rows = state.filteredRows.length ? state.filteredRows : state.rows;
  const eventTypes = new Set(rows.map((r) => r.event_type).filter(Boolean)).size;
  const devices = new Set(rows.map((r) => r.device).filter(Boolean)).size;
  const hosts = new Set(rows.map((r) => r.hostname).filter(Boolean)).size;

  el.statsStrip.innerHTML = "";
  el.statsStrip.appendChild(renderStat("Registros", String(rows.length)));
  el.statsStrip.appendChild(renderStat("Tipos de evento", String(eventTypes)));
  el.statsStrip.appendChild(renderStat("Dispositivos", String(devices)));
  el.statsStrip.appendChild(renderStat("Hosts", String(hosts)));
}

function renderStat(label, value) {
  const wrap = document.createElement("article");
  wrap.className = "stat";

  const p = document.createElement("p");
  p.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;

  wrap.append(p, strong);
  return wrap;
}

function render() {
  el.viewTitle.textContent = viewTitles[state.view] || "Vista";
  el.viewContainer.innerHTML = "";

  if (!state.filteredRows.length) {
    const empty = el.emptyTemplate.content.cloneNode(true);
    el.viewContainer.appendChild(empty);
    return;
  }

  if (state.view === "detalle") {
    el.viewContainer.appendChild(renderDetailTable(state.filteredRows));
    return;
  }

  if (state.view === "eventos") {
    const grouped = groupCount(state.filteredRows, (r) => r.event_type || "OTHER");
    el.viewContainer.appendChild(renderBars(grouped));
    return;
  }

  if (state.view === "dispositivos") {
    const grouped = groupCount(state.filteredRows, (r) => r.device || "N/A");
    el.viewContainer.appendChild(renderBars(grouped));
    return;
  }

  if (state.view === "timeline") {
    const grouped = groupCount(state.filteredRows, (r) => r.log_date || "Sin fecha");
    el.viewContainer.appendChild(renderBars(grouped));
  }
}

function renderDetailTable(rows) {
  const table = document.createElement("table");

  table.innerHTML = `
    <thead>
      <tr>
        <th>Fecha</th>
        <th>Hora</th>
        <th>Host</th>
        <th>Device</th>
        <th>Evento</th>
        <th>Mensaje</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.log_date || "-")}</td>
      <td>${escapeHtml(row.log_time || "-")}</td>
      <td>${escapeHtml(row.hostname || "-")}</td>
      <td>${escapeHtml(row.device || "-")}</td>
      <td>${escapeHtml(row.event_type || "-")}</td>
      <td>${escapeHtml(row.message || "-")}</td>
    `;
    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  return table;
}

function groupCount(rows, keyFn) {
  const counter = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    counter.set(key, (counter.get(key) || 0) + 1);
  }

  return [...counter.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 30);
}

function renderBars(items) {
  const max = Math.max(...items.map((i) => i.count), 1);
  const container = document.createElement("div");
  container.className = "bar-list";

  for (const item of items) {
    const row = document.createElement("article");
    row.className = "bar-row";

    const pct = Math.round((item.count / max) * 100);

    row.innerHTML = `
      <div class="bar-head">
        <span>${escapeHtml(item.name)}</span>
        <strong>${item.count}</strong>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${pct}%"></div>
      </div>
    `;

    container.appendChild(row);
  }

  return container;
}

function setStatus(message, kind) {
  el.statusBadge.textContent = message;
  el.statusBadge.classList.remove("ok", "error");
  if (kind) {
    el.statusBadge.classList.add(kind);
  }
}

function setLoading(isLoading) {
  state.loading = isLoading;
  el.loadButton.disabled = isLoading;
  el.loadButton.textContent = isLoading ? "Cargando..." : "Cargar";
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
