const state = { builds: [], config: null, selectedId: null, timer: null };
const activeStatuses = new Set(["new", "checking_out", "preparing", "installing", "testing", "starting", "destroying"]);
const terminalStatuses = new Set(["failed", "expired", "destroyed"]);
const $ = (selector) => document.querySelector(selector);

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function formatStatus(status) { return status.replaceAll("_", " "); }
function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
function relativeTime(value) {
  if (!value) return "—";
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const abs = Math.abs(seconds);
  const unit = abs < 60 ? "second" : abs < 3600 ? "minute" : abs < 86400 ? "hour" : "day";
  const divisor = unit === "second" ? 1 : unit === "minute" ? 60 : unit === "hour" ? 3600 : 86400;
  return new Intl.RelativeTimeFormat(undefined, { numeric: "auto" }).format(Math.round(seconds / divisor), unit);
}
function duration(seconds) {
  if (seconds == null) return "—";
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}
function statusBadge(status) { return `<span class="status status-${escapeHtml(status)}">${escapeHtml(formatStatus(status))}</span>`; }

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 3500);
}

function setConnection(online) {
  const element = $(".connection");
  element.classList.toggle("online", online);
  $("#connection-label").textContent = online ? "API online" : "API unavailable";
}

function filteredBuilds() {
  const query = $("#search-input").value.trim().toLowerCase();
  const status = $("#status-filter").value;
  return state.builds.filter((build) => {
    const haystack = [build.id, build.requested_ref, ...build.modules].join(" ").toLowerCase();
    return (!query || haystack.includes(query)) && (!status || build.status === status);
  });
}

function renderMetrics() {
  $("#metric-total").textContent = state.builds.length;
  $("#metric-active").textContent = state.builds.filter((item) => activeStatuses.has(item.status)).length;
  $("#metric-running").textContent = state.builds.filter((item) => item.status === "running").length;
  $("#metric-failed").textContent = state.builds.filter((item) => item.status === "failed").length;
}

function renderBuilds() {
  const builds = filteredBuilds();
  $("#build-list").innerHTML = builds.map((build) => {
    const sha = build.repositories[0]?.commit_sha;
    const modules = build.modules.slice(0, 3).map((item) => `<span class="module">${escapeHtml(item)}</span>`).join("");
    const remaining = build.modules.length > 3 ? `<span class="module">+${build.modules.length - 3}</span>` : "";
    return `<div class="build-row" role="row" tabindex="0" data-build-id="${escapeHtml(build.id)}">
      <span><strong class="build-id">${escapeHtml(build.id)}</strong><small class="build-sub">${sha ? escapeHtml(sha.slice(0, 10)) : "Awaiting SHA"}</small></span>
      <span><strong class="source-ref">${escapeHtml(build.requested_ref)}</strong><small class="build-sub">${escapeHtml(build.repositories[0]?.name || "—")}</small></span>
      <span class="module-list">${modules}${remaining}</span>
      <span>${statusBadge(build.status)}</span>
      <span><strong class="source-ref">${formatDate(build.created_at)}</strong><small class="build-sub">${relativeTime(build.created_at)}</small></span>
      <span class="chevron">›</span>
    </div>`;
  }).join("");
  $("#empty-state").hidden = builds.length > 0;
  $(".build-table").hidden = builds.length === 0;
}

function stageMarkup(stage) {
  const symbol = stage.status === "success" ? "✓" : stage.status === "failed" ? "!" : "";
  return `<div class="stage stage-${escapeHtml(stage.status)}">
    <span class="stage-dot">${symbol}</span>
    <span><strong>${escapeHtml(formatStatus(stage.name))}</strong><small>${escapeHtml(stage.summary || formatStatus(stage.status))}</small></span>
    <span class="stage-time">${duration(stage.duration_seconds)}</span>
  </div>`;
}

function renderDrawer(build) {
  if (!build) return closeDrawer();
  const repositories = build.repositories.map((repo) => `<div><span>${escapeHtml(repo.name)}</span><strong class="sha">${escapeHtml(repo.commit_sha || "Pending resolution")}</strong></div>`).join("");
  const canDestroy = build.status !== "destroyed" && build.status !== "destroying";
  const preview = build.status === "running" && build.preview_url ? `<a class="button button-primary" href="${escapeHtml(build.preview_url)}" target="_blank" rel="noopener">Open preview ↗</a>` : "";
  $("#drawer-content").innerHTML = `
    <header class="drawer-header"><div class="drawer-header-top"><div><p class="eyebrow">BUILD DETAIL</p><h2>${escapeHtml(build.id)}</h2></div><button class="icon-button" data-action="close" aria-label="Close details">×</button></div>
      <div class="drawer-actions">${preview}${canDestroy ? `<button class="button button-danger" data-action="destroy" data-id="${escapeHtml(build.id)}">Destroy</button>` : ""}</div>
    </header>
    <div class="detail-body">
      <div class="detail-grid">
        <div><span>Status</span><strong>${statusBadge(build.status)}</strong></div><div><span>Reference</span><strong>${escapeHtml(build.requested_ref)}</strong></div>
        <div><span>Created</span><strong>${formatDate(build.created_at)}</strong></div><div><span>Expires</span><strong>${formatDate(build.expires_at)}</strong></div>
        <div><span>Modules</span><strong>${escapeHtml(build.modules.join(", "))}</strong></div><div><span>Preview port</span><strong>${build.host_port || "—"}</strong></div>
      </div>
      ${build.failure_message ? `<section class="detail-section"><div class="form-error"><strong>${escapeHtml(build.failure_stage || "Build failure")}</strong><br>${escapeHtml(build.failure_message)}</div></section>` : ""}
      <section class="detail-section"><div class="detail-section-title"><h3>Repositories</h3></div><div class="detail-grid">${repositories || "<div><strong>No revisions yet</strong></div>"}</div></section>
      <section class="detail-section"><div class="detail-section-title"><h3>Pipeline</h3><button class="button button-small button-ghost" data-action="logs" data-id="${escapeHtml(build.id)}">All logs</button></div>${build.stages.map(stageMarkup).join("") || '<p class="build-sub">Waiting for the first stage…</p>'}</section>
      <section class="detail-section"><div class="detail-section-title"><h3>Logs</h3><select id="log-stage"><option value="">All stages</option>${build.stages.map((stage) => `<option value="${escapeHtml(stage.name)}">${escapeHtml(formatStatus(stage.name))}</option>`).join("")}</select></div><pre id="log-viewer" class="log-viewer">Select “Load logs” to retrieve the latest output.</pre><button class="button button-small button-ghost" data-action="logs" data-id="${escapeHtml(build.id)}">Load logs</button></section>
    </div>`;
  $("#build-drawer").classList.add("open");
  $("#build-drawer").setAttribute("aria-hidden", "false");
  $("#drawer-overlay").hidden = false;
}

function openDrawer(id) {
  state.selectedId = id;
  renderDrawer(state.builds.find((item) => item.id === id));
  $("#build-drawer").scrollTop = 0;
}
function closeDrawer() {
  state.selectedId = null;
  $("#build-drawer").classList.remove("open");
  $("#build-drawer").setAttribute("aria-hidden", "true");
  $("#drawer-overlay").hidden = true;
}

async function loadLogs(id) {
  const viewer = $("#log-viewer");
  if (!viewer) return;
  viewer.textContent = "Loading logs…";
  const stage = $("#log-stage")?.value || "";
  try {
    const logs = await api(`/builds/${encodeURIComponent(id)}/logs${stage ? `?stage=${encodeURIComponent(stage)}` : ""}`);
    viewer.textContent = logs.content || "No log output is available yet.";
  } catch (error) { viewer.textContent = error.message; }
}

async function destroyBuild(id) {
  if (!confirm(`Destroy runtime resources for ${id}? Logs and audit data will be retained.`)) return;
  try {
    await api(`/builds/${encodeURIComponent(id)}`, { method: "DELETE" });
    showToast("Build destroyed; evidence retained.");
    await refresh();
  } catch (error) { showToast(error.message); }
}

async function refresh() {
  try {
    const nextBuilds = await api("/builds");
    const changed = JSON.stringify(nextBuilds) !== JSON.stringify(state.builds);
    state.builds = nextBuilds;
    setConnection(true);
    if (changed) {
      renderMetrics();
      renderBuilds();
      if (state.selectedId) renderDrawer(state.builds.find((item) => item.id === state.selectedId));
    }
  } catch (error) { setConnection(false); showToast(error.message); }
  clearTimeout(state.timer);
  const active = state.builds.some((item) => activeStatuses.has(item.status));
  state.timer = setTimeout(refresh, active ? 2500 : 8000);
}

async function loadConfig() {
  state.config = await api("/app-config");
  $("#worker-count").textContent = `${state.config.max_concurrent_builds} worker${state.config.max_concurrent_builds === 1 ? "" : "s"}`;
  const select = $("#repository-input");
  select.innerHTML = state.config.repositories.length
    ? state.config.repositories.map((item) => `<option value="${escapeHtml(item.alias)}" data-ref="${escapeHtml(item.default_ref)}">${escapeHtml(item.alias)}</option>`).join("")
    : '<option value="">No repositories configured</option>';
  select.disabled = state.config.repositories.length === 0;
  $("#submit-build").disabled = state.config.repositories.length === 0;
  updateDefaultRef();
}

function updateDefaultRef() {
  const option = $("#repository-input").selectedOptions[0];
  if (option?.dataset.ref) $("#ref-input").value = option.dataset.ref;
}

async function submitBuild(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const errorBox = $("#form-error");
  errorBox.hidden = true;
  $("#submit-build").disabled = true;
  try {
    const build = await api("/builds", { method: "POST", body: JSON.stringify({ repository: form.get("repository"), ref: form.get("ref"), modules: String(form.get("modules")).split(",").map((item) => item.trim()).filter(Boolean), ttl_seconds: Number(form.get("ttl_seconds")) }) });
    $("#create-dialog").close();
    showToast(`Build ${build.id} queued.`);
    await refresh();
    openDrawer(build.id);
  } catch (error) { errorBox.textContent = error.message; errorBox.hidden = false; }
  finally { $("#submit-build").disabled = state.config?.repositories.length === 0; }
}

$("#create-button").addEventListener("click", () => $("#create-dialog").showModal());
$("#refresh-button").addEventListener("click", refresh);
$("#search-input").addEventListener("input", renderBuilds);
$("#status-filter").addEventListener("change", renderBuilds);
$("#repository-input").addEventListener("change", updateDefaultRef);
$("#create-form").addEventListener("submit", submitBuild);
document.querySelectorAll("[data-modal-close]").forEach((button) => button.addEventListener("click", () => $("#create-dialog").close()));
$("#drawer-overlay").addEventListener("click", closeDrawer);
$("#build-list").addEventListener("click", (event) => { const row = event.target.closest("[data-build-id]"); if (row) openDrawer(row.dataset.buildId); });
$("#build-list").addEventListener("keydown", (event) => { if (event.key === "Enter") { const row = event.target.closest("[data-build-id]"); if (row) openDrawer(row.dataset.buildId); } });
$("#build-drawer").addEventListener("click", (event) => { const action = event.target.closest("[data-action]"); if (!action) return; if (action.dataset.action === "close") closeDrawer(); if (action.dataset.action === "logs") loadLogs(action.dataset.id); if (action.dataset.action === "destroy") destroyBuild(action.dataset.id); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("#create-dialog").open) closeDrawer(); });

Promise.all([loadConfig(), refresh()]).catch((error) => { setConnection(false); showToast(error.message); });
