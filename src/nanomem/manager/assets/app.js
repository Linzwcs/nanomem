const app = document.getElementById("app");
const statusEl = document.getElementById("status");
const sideStatusEl = document.getElementById("sideStatus");
const breadcrumbEl = document.getElementById("breadcrumb");
const pageTitleEl = document.getElementById("pageTitle");
const refreshButton = document.getElementById("refresh");

const API_BASE = "/manager/api";

let statsCache = null;
let unitFilters = {
  owner_id: "",
  namespace: "",
  memory_type: "",
  search: "",
  start: "",
  end: "",
  order: "newest_first",
  limit: "50",
  include_redacted: false,
  queue: "all",
};
let logFilters = {
  owner_id: "",
  namespace: "",
  operation_type: "",
  status: "",
  start: "",
  end: "",
  limit: "50",
};

const pageMeta = {
  dashboard: ["Dashboard", "Store overview"],
  "memory-units": ["Memory Units", "Fact review"],
  "operation-logs": ["Operation Logs", "Audit trail"],
  "retrieval-lab": ["Retrieval Lab", "Runtime recall preview"],
  system: ["System Health", "Store and index"],
};

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const display = (value) => value === null || value === undefined || value === "" ? "-" : String(value);
const json = (value) => JSON.stringify(value, null, 2);
const compactDate = (value) => display(value).replace("T", " ").replace("+00:00", " UTC");
const formText = (data, key) => String(data.get(key) || "").trim();

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || payload.error || response.statusText);
  return payload;
}

function route() {
  const hash = window.location.hash || "#/dashboard";
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { name: parts[0] || "dashboard", params: parts.slice(1) };
}

function setChrome(name) {
  const root = name === "memory-units" ? "memory-units" : name;
  const meta = pageMeta[root] || pageMeta.dashboard;
  breadcrumbEl.textContent = meta[1];
  pageTitleEl.textContent = meta[0];
  document.querySelectorAll(".sidebar a").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === root);
  });
}

function badge(value, extra = "") {
  const token = String(extra || value)
    .toLowerCase()
    .replaceAll("_", "-")
    .replace(/[^a-z0-9-]/g, "-");
  return `<span class="pill ${token}">${escapeHtml(display(value))}</span>`;
}

function metric(label, value, hint = "") {
  return `<div class="metric">
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(display(value))}</strong>
    ${hint ? `<small>${escapeHtml(hint)}</small>` : ""}
  </div>`;
}

function formatScope(scope) {
  if (!scope) return "-";
  return `${scope.owner_id}/${scope.namespace || "-"}`;
}

function confidenceText(value) {
  return value === null || value === undefined ? "-" : Number(value).toFixed(2);
}

function confidenceClass(value) {
  if (value === null || value === undefined) return "medium";
  if (Number(value) >= 0.85) return "high";
  if (Number(value) >= 0.7) return "medium";
  return "low";
}

function sourceStatusClass(status) {
  return String(status || "ok").replaceAll("_", "-");
}

function sourceStatusLabel(status) {
  return display(status).replaceAll("_", " ");
}

function roleClass(role) {
  return String(role || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-");
}

function dateStart(value) {
  return value ? `${value}T00:00:00+00:00` : "";
}

function dateEnd(value) {
  return value ? `${value}T23:59:59+00:00` : "";
}

function shortId(value) {
  const raw = display(value);
  return raw.length > 20 ? `${raw.slice(0, 12)}...${raw.slice(-6)}` : raw;
}

async function loadStats({ force = false } = {}) {
  if (statsCache && !force) return statsCache;
  statsCache = await api("/stats");
  const text = `${statsCache.index_backend} / ${statsCache.unit_count} units`;
  statusEl.textContent = text;
  sideStatusEl.textContent = statsCache.path || text;
  return statsCache;
}

async function render() {
  const current = route();
  const root = current.name || "dashboard";
  setChrome(root);
  app.innerHTML = `<div class="loading">Loading.</div>`;
  try {
    if (!statsCache) await loadStats();
    if (root === "dashboard") await renderDashboard();
    else if (root === "memory-units" && current.params[0]) await renderMemoryUnitDetail(current.params[0]);
    else if (root === "memory-units") await renderMemoryUnits();
    else if (root === "operation-logs") await renderOperationLogs();
    else if (root === "retrieval-lab") await renderRetrievalLab();
    else if (root === "system") await renderSystem();
    else window.location.hash = "#/dashboard";
  } catch (error) {
    app.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  }
}

async function renderDashboard() {
  const stats = await loadStats({ force: true });
  const lag = Math.max((stats.unit_count || 0) - (stats.index_document_count || 0), 0);
  const owners = stats.top_owners || [];
  app.innerHTML = `
    <section class="page">
      <div class="page-head">
        <div>
          <h2>Dashboard</h2>
          <p>Authoritative store, derived index, and owner namespace distribution.</p>
        </div>
        <div class="toolbar">
          ${badge(lag === 0 ? "index current" : `${lag} index lag`, lag === 0 ? "ok" : "medium")}
          ${badge(`schema ${stats.schema_version}`)}
        </div>
      </div>

      <div class="metrics">
        ${metric("Memory Units", stats.unit_count)}
        ${metric("Dialogues", stats.dialogue_count)}
        ${metric("Operation Logs", stats.operation_log_count)}
        ${metric("Namespaces", stats.namespace_count)}
        ${metric("Index Docs", stats.index_document_count)}
        ${metric("Index Lag", lag)}
      </div>

      <div class="grid-2">
        <section class="section">
          <div>
            <h3>Owner Namespaces</h3>
            <p class="section-subtitle">Top scopes by durable memory count.</p>
          </div>
          ${renderOwnerBars(owners)}
        </section>

        <section class="section">
          <div>
            <h3>Store Health</h3>
            <p class="section-subtitle">SQLite is authoritative; index state is derived.</p>
          </div>
          <div class="health-strip">
            ${health("Store", stats.store, stats.path)}
            ${health("Schema", `${stats.schema_version}/${stats.latest_schema_version}`, `${stats.pending_schema_migration_count} pending migrations`)}
            ${health("Index", stats.index_backend, `${stats.index_document_count} documents`)}
            ${health("Latest Operation", compactDate(stats.latest_operation_at), "operation log clock")}
          </div>
        </section>
      </div>
    </section>`;
}

function renderOwnerBars(rows) {
  if (!rows.length) return `<div class="empty">No memory scopes yet.</div>`;
  const max = Math.max(...rows.map((row) => row.unit_count || 0), 1);
  return `<div class="bar-list">${rows.map((row) => {
    const width = Math.max(4, Math.round(((row.unit_count || 0) / max) * 100));
    return `<div class="bar-row">
      <div class="mono truncate">${escapeHtml(row.owner_id)}/${escapeHtml(row.namespace || "-")}</div>
      <div class="bar-track"><div class="bar-fill" style="width: ${width}%"></div></div>
      <strong>${escapeHtml(row.unit_count)}</strong>
    </div>`;
  }).join("")}</div>`;
}

function health(label, value, hint) {
  return `<div class="health-item">
    <span class="muted">${escapeHtml(label)}</span>
    <strong class="wrap-anywhere">${escapeHtml(display(value))}</strong>
    <small class="muted wrap-anywhere">${escapeHtml(display(hint))}</small>
  </div>`;
}

function unitQueryParams() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(unitFilters)) {
    if (["queue", "search"].includes(key)) continue;
    if (key === "start" && value) params.set("start", dateStart(value));
    else if (key === "end" && value) params.set("end", dateEnd(value));
    else if (key === "include_redacted" && value) params.set("include_redacted", "true");
    else if (value && key !== "include_redacted") params.set(key, value);
  }
  return params;
}

async function renderMemoryUnits() {
  const payload = await api(`/memory-units?${unitQueryParams()}`);
  const loaded = payload.units || [];
  const searched = applyUnitSearch(loaded, unitFilters.search);
  const items = filterQueue(searched, unitFilters.queue);
  const summary = summarizeUnits(items);
  app.innerHTML = `
    <section class="page">
      <div class="page-head">
        <div>
          <h2>Memory Units</h2>
          <p>Review durable facts, quality signals, and source evidence.</p>
        </div>
        <div class="toolbar">
          ${badge(`${items.length} shown`)}
          ${badge(`${payload.count} loaded`)}
        </div>
      </div>

      ${renderUnitFilters()}

      <div class="metrics">
        ${metric("Shown", items.length)}
        ${metric("Active", summary.active)}
        ${metric("Low Confidence", summary.lowConfidence)}
        ${metric("Evidence Refs", summary.refs)}
        ${metric("Namespaces", summary.namespaces)}
        ${metric("Redacted", summary.redacted)}
      </div>

      <div class="queue-tabs" id="queueTabs">
        ${queueButton("all", "All")}
        ${queueButton("needs_review", "Needs review")}
        ${queueButton("low_confidence", "Low confidence")}
        ${queueButton("evidence_issues", "Evidence issues")}
        ${queueButton("redacted", "Redacted")}
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Time</th><th>Memory</th><th>Scope</th><th>Type</th><th>Confidence</th><th>Evidence</th><th>Status</th></tr>
          </thead>
          <tbody>${items.map(renderUnitRow).join("") || `<tr><td colspan="7" class="muted">No memory units match the current filters.</td></tr>`}</tbody>
        </table>
      </div>
    </section>`;
  bindUnitList();
}

function renderUnitFilters() {
  return `<form class="panel filters" id="unitFilters">
    <label>Owner<input name="owner_id" value="${escapeHtml(unitFilters.owner_id)}" placeholder="owner id"></label>
    <label>Namespace<input name="namespace" value="${escapeHtml(unitFilters.namespace)}" placeholder="personal,work"></label>
    <label>Type<input name="memory_type" value="${escapeHtml(unitFilters.memory_type)}" placeholder="preference"></label>
    <label>Search<input name="search" value="${escapeHtml(unitFilters.search)}" placeholder="client-side text"></label>
    <label>Start<input name="start" type="date" value="${escapeHtml(unitFilters.start)}"></label>
    <label>End<input name="end" type="date" value="${escapeHtml(unitFilters.end)}"></label>
    <label>Order<select name="order">
      <option value="newest_first" ${unitFilters.order === "newest_first" ? "selected" : ""}>Newest first</option>
      <option value="oldest_first" ${unitFilters.order === "oldest_first" ? "selected" : ""}>Oldest first</option>
    </select></label>
    <label>Limit<input name="limit" type="number" min="0" max="500" value="${escapeHtml(unitFilters.limit)}"></label>
    <label class="check-label"><input name="include_redacted" type="checkbox" ${unitFilters.include_redacted ? "checked" : ""}> Include redacted</label>
    <div class="toolbar">
      <button class="button" type="submit">Apply</button>
      <button class="button secondary" type="button" id="clearUnitFilters">Clear</button>
    </div>
  </form>`;
}

function queueButton(value, label) {
  return `<button type="button" data-queue="${value}" class="${unitFilters.queue === value ? "active" : ""}">${escapeHtml(label)}</button>`;
}

function applyUnitSearch(units, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return units;
  return units.filter((unit) => [
    unit.unit_id,
    unit.text,
    unit.memory_type,
    unit.scope?.owner_id,
    unit.scope?.namespace,
  ].some((value) => String(value || "").toLowerCase().includes(needle)));
}

function filterQueue(units, queue) {
  if (queue === "low_confidence") return units.filter((unit) => (unit.confidence ?? 1) < 0.7);
  if (queue === "redacted") return units.filter((unit) => unit.redacted_at);
  if (queue === "evidence_issues") return units.filter((unit) => !unit.dialogue_refs || !unit.dialogue_refs.length);
  if (queue === "needs_review") {
    return units.filter((unit) => (unit.confidence ?? 1) < 0.7 || !unit.dialogue_refs || !unit.dialogue_refs.length || unit.redacted_at);
  }
  return units;
}

function summarizeUnits(units) {
  const namespaces = new Set(units.map((unit) => unit.scope?.namespace || "-"));
  return {
    active: units.filter((unit) => !unit.redacted_at).length,
    lowConfidence: units.filter((unit) => (unit.confidence ?? 1) < 0.7).length,
    refs: units.reduce((sum, unit) => sum + (unit.dialogue_refs || []).length, 0),
    namespaces: namespaces.size,
    redacted: units.filter((unit) => unit.redacted_at).length,
  };
}

function renderUnitRow(unit) {
  const refCount = (unit.dialogue_refs || []).length;
  return `<tr class="clickable" data-unit-id="${escapeHtml(unit.unit_id)}">
    <td class="mono">${escapeHtml(compactDate(unit.timestamp))}</td>
    <td>
      <div class="memory-text clamp-2 wrap-anywhere">${escapeHtml(unit.text)}</div>
      <div class="muted mono">${escapeHtml(shortId(unit.unit_id))}</div>
    </td>
    <td class="mono">${escapeHtml(formatScope(unit.scope))}</td>
    <td>${badge(unit.memory_type, unit.memory_type)}</td>
    <td>${badge(confidenceText(unit.confidence), confidenceClass(unit.confidence))}</td>
    <td>${badge(`${refCount} refs`, refCount ? "ok" : "low")}</td>
    <td>${unit.redacted_at ? badge("redacted", "redacted") : badge("active", "active")}</td>
  </tr>`;
}

function bindUnitList() {
  document.getElementById("unitFilters").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    unitFilters = {
      ...unitFilters,
      owner_id: formText(data, "owner_id"),
      namespace: formText(data, "namespace"),
      memory_type: formText(data, "memory_type"),
      search: formText(data, "search"),
      start: formText(data, "start"),
      end: formText(data, "end"),
      order: formText(data, "order") || "newest_first",
      limit: formText(data, "limit") || "50",
      include_redacted: data.get("include_redacted") === "on",
    };
    renderMemoryUnits();
  });
  document.getElementById("clearUnitFilters").addEventListener("click", () => {
    unitFilters = { owner_id: "", namespace: "", memory_type: "", search: "", start: "", end: "", order: "newest_first", limit: "50", include_redacted: false, queue: "all" };
    renderMemoryUnits();
  });
  document.getElementById("queueTabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-queue]");
    if (!button) return;
    unitFilters.queue = button.dataset.queue;
    renderMemoryUnits();
  });
  document.querySelectorAll("[data-unit-id]").forEach((row) => {
    row.addEventListener("click", () => {
      window.location.hash = `#/memory-units/${encodeURIComponent(row.dataset.unitId)}`;
    });
  });
}

async function renderMemoryUnitDetail(unitId) {
  const payload = await api(`/memory-units/${encodeURIComponent(unitId)}`);
  const unit = payload.unit;
  const chunks = payload.source_chunks || [];
  const warningCount = chunks.filter((chunk) => chunk.status !== "ok").length;
  setChrome("memory-units");
  pageTitleEl.textContent = "Memory Detail";
  breadcrumbEl.textContent = "Fact review / Detail";
  app.innerHTML = `
    <section class="detail-page">
      <div class="detail-header">
        <div class="detail-header-row">
          <div>
            <a class="button secondary" href="#/memory-units">Back to memory units</a>
            <p class="detail-meta mono">${escapeHtml(unit.unit_id)}</p>
            <h2 class="detail-title wrap-anywhere">${escapeHtml(unit.text)}</h2>
          </div>
          <div class="detail-meta">
            ${badge(unit.memory_type, unit.memory_type)}
            ${badge(confidenceText(unit.confidence), confidenceClass(unit.confidence))}
            ${badge(warningCount ? `${warningCount} evidence warnings` : "evidence ok", warningCount ? "medium" : "ok")}
            ${unit.redacted_at ? badge("redacted", "redacted") : badge("active", "active")}
          </div>
        </div>
        <div class="tabs">
          <button class="active" data-tab="evidence">Evidence</button>
          <button data-tab="summary">Summary</button>
          <button data-tab="quality">Quality</button>
          <button data-tab="lifecycle">Lifecycle</button>
          <button data-tab="raw">Raw JSON</button>
        </div>
      </div>
      <div class="detail-body" id="detailBody"></div>
    </section>`;
  const renderTab = (tab) => {
    document.querySelectorAll(".tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
    document.getElementById("detailBody").innerHTML = renderDetailTab(tab, payload);
  };
  document.querySelector(".tabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) renderTab(button.dataset.tab);
  });
  renderTab("evidence");
}

function renderDetailTab(tab, payload) {
  if (tab === "summary") return renderUnitSummary(payload);
  if (tab === "quality") return renderUnitQuality(payload);
  if (tab === "lifecycle") return renderUnitLifecycle(payload);
  if (tab === "raw") return `<pre class="json-view">${escapeHtml(json(payload))}</pre>`;
  return renderEvidence(payload);
}

function renderUnitSummary({ unit, source_chunks }) {
  return `<dl class="fact-grid">
    ${fact("Scope", formatScope(unit.scope), "mono")}
    ${fact("Memory time", compactDate(unit.timestamp))}
    ${fact("Available", compactDate(unit.available_at))}
    ${fact("Confidence", confidenceText(unit.confidence))}
    ${fact("Evidence chunks", (source_chunks || []).length)}
    ${fact("Retention", unit.retention_until || "-")}
  </dl>
  <section class="section">
    <div><h3>Metadata</h3><p class="section-subtitle">Extractor and source annotations.</p></div>
    ${renderMetadata(unit.metadata || {})}
  </section>`;
}

function renderUnitQuality({ unit, source_chunks }) {
  const chunks = source_chunks || [];
  const warningChunks = chunks.filter((chunk) => chunk.status !== "ok");
  const reasons = [];
  if ((unit.confidence ?? 1) < 0.7) reasons.push("low confidence");
  if (!chunks.length) reasons.push("no evidence");
  reasons.push(...warningChunks.map((chunk) => sourceStatusLabel(chunk.status)));
  return `<dl class="fact-grid">
    ${fact("Confidence", confidenceText(unit.confidence))}
    ${fact("Confidence bucket", confidenceClass(unit.confidence))}
    ${fact("Evidence status", warningChunks.length ? "warning" : "ok")}
    ${fact("Review reasons", reasons.join(", ") || "none")}
    ${fact("Dialogue refs", chunks.length)}
    ${fact("Redaction", unit.redacted_at || "active")}
  </dl>`;
}

function renderUnitLifecycle({ unit, source_chunks }) {
  const dialogues = (source_chunks || []).map((chunk) => chunk.dialogue).filter(Boolean);
  return `<dl class="fact-grid">
    ${fact("Memory timestamp", compactDate(unit.timestamp))}
    ${fact("Available at", compactDate(unit.available_at))}
    ${fact("Retention until", unit.retention_until || "-")}
    ${fact("Redacted at", unit.redacted_at || "-")}
    ${fact("Dialogue occurred", dialogues.map((dialogue) => compactDate(dialogue.occurred_at)).join(", ") || "-")}
    ${fact("Dialogue captured", dialogues.map((dialogue) => compactDate(dialogue.captured_at)).join(", ") || "-")}
  </dl>`;
}

function renderEvidence({ source_chunks }) {
  const chunks = source_chunks || [];
  return `<div class="queue-tabs">
    ${chunks.map((chunk, index) => badge(`Evidence ${index + 1}: ${sourceStatusLabel(chunk.status)}`, sourceStatusClass(chunk.status))).join("")}
  </div>
  ${chunks.map(renderSourceChunk).join("") || `<div class="empty">No source evidence recorded.</div>`}`;
}

function renderSourceChunk(chunk, index) {
  const dialogue = chunk.dialogue || {};
  const warning = chunk.status === "ok" ? "" : " warning";
  return `<article class="source-card${warning}">
    <div class="source-head">
      <div>
        <h3>Evidence ${index + 1}</h3>
        <div class="detail-meta mono">${escapeHtml(display(dialogue.dialogue_id || chunk.ref?.dialogue_id))}</div>
      </div>
      <div>${badge(sourceStatusLabel(chunk.status), sourceStatusClass(chunk.status))}</div>
    </div>
    <dl class="source-meta">
      ${fact("Range", chunk.range_label)}
      ${fact("Resolved", `${display(chunk.resolved_message_count)} / ${display(chunk.message_count)} messages`)}
      ${fact("Occurred", compactDate(dialogue.occurred_at))}
      ${fact("Captured", compactDate(dialogue.captured_at))}
      ${fact("Checksum", dialogue.checksum || "-")}
      ${fact("Reveal", chunk.raw_dialogue_available ? "available" : "not available")}
    </dl>
    ${renderTranscript(chunk)}
  </article>`;
}

function renderTranscript(chunk) {
  if (chunk.missing) return `<div class="empty">Dialogue record is missing. The ref remains available for audit.</div>`;
  if (chunk.status === "redacted_dialogue") return `<div class="empty">Dialogue content is redacted.</div>`;
  const messages = chunk.dialogue_messages || chunk.messages || [];
  if (!messages.length) return `<div class="empty">No messages resolved for this evidence range.</div>`;
  return `<div class="dialogue-log">${messages.map((message) => `
    <article class="log-entry ${message.in_ref_range ? "in-ref" : ""} role-${roleClass(message.role)}">
      <div class="log-rail">
        <span class="log-index">#${escapeHtml(message.index)}</span>
        <span class="log-dot"></span>
      </div>
      <div class="log-body">
        <div class="log-meta">
          <span class="mono">${escapeHtml(compactDate(message.timestamp))}</span>
          ${badge(message.role)}
          ${message.speaker_id ? badge(message.speaker_id) : ""}
          ${message.in_ref_range ? badge("extracted range", "ok") : ""}
        </div>
        <div class="log-content">${escapeHtml(message.content)}</div>
      </div>
    </article>
  `).join("")}</div>`;
}

function fact(label, value, className = "") {
  return `<div><dt>${escapeHtml(label)}</dt><dd class="${className} wrap-anywhere">${escapeHtml(display(value))}</dd></div>`;
}

function renderMetadata(metadata) {
  const entries = Object.entries(metadata);
  return `<dl class="metadata-list">${entries.map(([key, value]) => fact(key, summarize(value))).join("") || fact("empty", "No metadata")}</dl>`;
}

function summarize(value) {
  if (Array.isArray(value)) return `array: ${value.length} items`;
  if (value && typeof value === "object") return `object: ${Object.keys(value).length} keys`;
  return display(value);
}

function logQueryParams() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(logFilters)) {
    if (key === "start" && value) params.set("start", dateStart(value));
    else if (key === "end" && value) params.set("end", dateEnd(value));
    else if (value) params.set(key, value);
  }
  return params;
}

async function renderOperationLogs() {
  const payload = await api(`/operation-logs?${logQueryParams()}`);
  app.innerHTML = `<section class="page">
    <div class="page-head">
      <div>
        <h2>Operation Logs</h2>
        <p>Audit capture, read, reindex, and maintenance activity.</p>
      </div>
      <div class="toolbar">${badge(`${payload.count} logs`)}</div>
    </div>
    ${renderLogFilters()}
    <div class="table-wrap"><table>
      <thead><tr><th>Created</th><th>Type</th><th>Status</th><th>Scope</th><th>Summary</th></tr></thead>
      <tbody>${(payload.logs || []).map(renderLogRow).join("") || `<tr><td colspan="5" class="muted">No logs match the current filters.</td></tr>`}</tbody>
    </table></div>
  </section>`;
  bindLogFilters();
}

function renderLogFilters() {
  return `<form class="panel filters" id="logFilters">
    <label>Owner<input name="owner_id" value="${escapeHtml(logFilters.owner_id)}" placeholder="owner id"></label>
    <label>Namespace<input name="namespace" value="${escapeHtml(logFilters.namespace)}" placeholder="personal"></label>
    <label>Operation<input name="operation_type" value="${escapeHtml(logFilters.operation_type)}" placeholder="capture, read, reindex"></label>
    <label>Status<input name="status" value="${escapeHtml(logFilters.status)}" placeholder="ok"></label>
    <label>Start<input name="start" type="date" value="${escapeHtml(logFilters.start)}"></label>
    <label>End<input name="end" type="date" value="${escapeHtml(logFilters.end)}"></label>
    <label>Limit<input name="limit" type="number" min="0" max="500" value="${escapeHtml(logFilters.limit)}"></label>
    <div class="toolbar">
      <button class="button" type="submit">Apply</button>
      <button class="button secondary" type="button" id="clearLogFilters">Clear</button>
    </div>
  </form>`;
}

function renderLogRow(log) {
  return `<tr>
    <td class="mono">${escapeHtml(compactDate(log.created_at))}</td>
    <td>${badge(log.operation_type)}</td>
    <td>${badge(log.status, log.status === "ok" ? "ok" : "medium")}</td>
    <td class="mono">${escapeHtml(log.scope ? formatScope(log.scope) : "-")}</td>
    <td><pre class="json-view">${escapeHtml(json(log.summary))}</pre></td>
  </tr>`;
}

function bindLogFilters() {
  document.getElementById("logFilters").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    logFilters = {
      owner_id: formText(data, "owner_id"),
      namespace: formText(data, "namespace"),
      operation_type: formText(data, "operation_type"),
      status: formText(data, "status"),
      start: formText(data, "start"),
      end: formText(data, "end"),
      limit: formText(data, "limit") || "50",
    };
    renderOperationLogs();
  });
  document.getElementById("clearLogFilters").addEventListener("click", () => {
    logFilters = { owner_id: "", namespace: "", operation_type: "", status: "", start: "", end: "", limit: "50" };
    renderOperationLogs();
  });
}

async function renderRetrievalLab() {
  const stats = await loadStats();
  const defaultOwner = stats.top_owners?.[0]?.owner_id || "";
  app.innerHTML = `<section class="page">
    <div class="page-head">
      <div>
        <h2>Retrieval Lab</h2>
        <p>Preview the same read pipeline that an agent uses at runtime.</p>
      </div>
      <div class="toolbar">${badge("read pipeline", "ok")}</div>
    </div>
    <form class="panel filters" id="readForm">
      <label>Owner<input name="owner_id" value="${escapeHtml(defaultOwner)}" placeholder="owner id"></label>
      <label>Namespaces<input name="namespaces" placeholder="personal,work"></label>
      <label>Query Time<input name="query_time" placeholder="defaults to now"></label>
      <label>Max Units<input name="max_units" type="number" value="5" min="1" max="50"></label>
      <label>Context Budget<input name="context_budget_tokens" type="number" placeholder="optional" min="1"></label>
      <label style="grid-column: 1 / -1">Query<textarea name="query" placeholder="What should the agent remember?"></textarea></label>
      <div class="toolbar"><button class="button" type="submit">Run Preview</button></div>
    </form>
    <div id="readResult" class="empty">No preview has been run.</div>
  </section>`;
  document.getElementById("readForm").addEventListener("submit", handleRetrievalSubmit);
}

async function handleRetrievalSubmit(event) {
  event.preventDefault();
  const target = document.getElementById("readResult");
  target.className = "loading";
  target.textContent = "Running preview.";
  const data = new FormData(event.currentTarget);
  const namespaces = formText(data, "namespaces").split(",").map((item) => item.trim()).filter(Boolean);
  const budget = formText(data, "context_budget_tokens");
  const payload = {
    owner_id: formText(data, "owner_id"),
    namespaces: namespaces.length ? namespaces : null,
    query: formText(data, "query"),
    query_time: formText(data, "query_time"),
    max_units: Number(formText(data, "max_units") || 5),
  };
  if (budget) payload.context_budget_tokens = Number(budget);
  try {
    const result = await api("/retrieval-preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    target.className = "";
    target.innerHTML = renderRetrievalResult(result);
    await loadStats({ force: true });
  } catch (error) {
    target.className = "error";
    target.textContent = error.message;
  }
}

function renderRetrievalResult(result) {
  const ranked = result.ranked_units || [];
  return `<div class="page">
    <div class="metrics">
      ${metric("Ranked Units", ranked.length)}
      ${metric("Rendered Units", result.context?.unit_count)}
      ${metric("Tokens", result.context?.token_count)}
      ${metric("Index Backend", result.stats?.index_backend)}
      ${metric("Candidates", result.stats?.candidate_count)}
      ${metric("Returned", result.stats?.returned_count)}
    </div>
    <section class="context-card">
      <div class="source-head">
        <div><h3>Rendered Context</h3><p class="section-subtitle">This is what the agent would receive.</p></div>
        ${badge(`${result.context?.token_count || 0} tokens`)}
      </div>
      <div class="context-text">${escapeHtml(result.context?.text || "No context rendered.")}</div>
    </section>
    ${ranked.map(renderRankedUnit).join("") || `<div class="empty">No memory units were retrieved.</div>`}
    <details class="section">
      <summary>Raw response</summary>
      <pre class="json-view">${escapeHtml(json(result))}</pre>
    </details>
  </div>`;
}

function renderRankedUnit(row) {
  const unit = row.unit;
  return `<article class="result-card">
    <div class="result-head">
      <div>
        <h3 class="wrap-anywhere">#${escapeHtml(row.rank)} ${escapeHtml(unit.text)}</h3>
        <p class="section-subtitle mono">${escapeHtml(unit.unit_id)}</p>
      </div>
      <div class="detail-meta">
        ${badge(unit.memory_type, unit.memory_type)}
        ${badge(Number(row.score || 0).toFixed(4), "ok")}
      </div>
    </div>
    <div class="result-score">
      <strong>Score</strong>
      <div class="bar-track"><div class="bar-fill" style="width: ${Math.max(2, Math.min(100, Math.round((row.score || 0) * 100)))}%"></div></div>
    </div>
    <dl class="fact-grid">
      ${fact("Scope", formatScope(unit.scope), "mono")}
      ${fact("Timestamp", compactDate(unit.timestamp))}
      ${fact("Confidence", confidenceText(unit.confidence))}
      ${fact("Retrieval text", row.retrieval_text || "-")}
    </dl>
    <div class="toolbar">
      <a class="button secondary" href="#/memory-units/${encodeURIComponent(unit.unit_id)}">Open evidence</a>
    </div>
  </article>`;
}

async function renderSystem() {
  const stats = await loadStats({ force: true });
  const lag = Math.max((stats.unit_count || 0) - (stats.index_document_count || 0), 0);
  app.innerHTML = `<section class="page">
    <div class="page-head">
      <div>
        <h2>System Health</h2>
        <p>Local manager status. Login authentication is intentionally out of scope for this local build.</p>
      </div>
      <div class="toolbar">${badge(lag === 0 ? "healthy" : "needs reindex", lag === 0 ? "ok" : "medium")}</div>
    </div>

    <div class="metrics">
      ${metric("Store", stats.store, stats.path)}
      ${metric("Schema", `${stats.schema_version}/${stats.latest_schema_version}`)}
      ${metric("Index Backend", stats.index_backend)}
      ${metric("Index Docs", stats.index_document_count)}
      ${metric("Store Units", stats.unit_count)}
      ${metric("Index Lag", lag)}
    </div>

    <section class="section">
      <div class="source-head">
        <div>
          <h3>Index Maintenance</h3>
          <p class="section-subtitle">Rebuild derived retrieval state from the authoritative store.</p>
        </div>
        <button class="button" id="reindex">Reindex All</button>
      </div>
      <pre class="json-view" id="reindexResult">No reindex run.</pre>
    </section>

    <section class="section">
      <div><h3>Configuration Summary</h3><p class="section-subtitle">Manager uses the existing server process and control API.</p></div>
      <dl class="fact-grid">
        ${fact("Manager route", "/manager")}
        ${fact("API route", "/manager/api")}
        ${fact("Authentication", "not enabled for local manager")}
        ${fact("Raw dialogue", "audit surface only")}
      </dl>
    </section>

    <details class="section">
      <summary>Raw stats</summary>
      <pre class="json-view">${escapeHtml(json(stats))}</pre>
    </details>
  </section>`;
  document.getElementById("reindex").addEventListener("click", async () => {
    const button = document.getElementById("reindex");
    const output = document.getElementById("reindexResult");
    button.disabled = true;
    output.textContent = "Reindexing.";
    try {
      const result = await api("/reindex", { method: "POST", body: "{}" });
      output.textContent = json(result);
      await loadStats({ force: true });
      renderSystem();
    } catch (error) {
      output.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

refreshButton.addEventListener("click", async () => {
  statsCache = null;
  await render();
});

window.addEventListener("hashchange", render);
if (!window.location.hash) window.location.hash = "#/dashboard";
render();
