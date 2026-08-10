const healingEscape = value => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function healingBadge(finding) {
  return finding.healthy ? "HEALTHY" : "ATTENTION";
}

function healingSummary(data) {
  const findings = data.findings || [];
  const unhealthy = findings.filter(item => !item.healthy);
  const proposals = data.repair_proposals || {};
  const proposalCount = Object.values(proposals).reduce((total, items) => total + items.length, 0);
  return { findings, unhealthy, proposals, proposalCount };
}

function renderHealingDashboard(data) {
  const { findings, unhealthy, proposals, proposalCount } = healingSummary(data);
  const rows = findings.length ? findings.map(item => {
    const detailText = Object.entries(item.details || {})
      .map(([key, value]) => `${healingEscape(key)}: ${healingEscape(value)}`)
      .join(" · ");
    return `<div class="med-row">
      <strong>${healingEscape(item.component)} · ${healingBadge(item)}</strong>
      <p>${healingEscape(item.signature)}${detailText ? ` · ${detailText}` : ""}</p>
    </div>`;
  }).join("") : "<p>No health probes reported yet.</p>";

  const proposalRows = Object.entries(proposals).flatMap(([issueId, items]) =>
    (items || []).map(item => `<div class="med-row">
      <strong>Proposed repair · ${healingEscape(item.proposed_action)}</strong>
      <p>${healingEscape(issueId)} · trust ${healingEscape(item.trust)} · risk ${healingEscape(item.risk)}</p>
      <small>${healingEscape(item.title)} — proposal only; the dispatcher has not executed it.</small>
    </div>`)
  ).join("");

  openModal(`<h2>RequantAi System Recovery</h2>
    <p><strong>${unhealthy.length ? `${unhealthy.length} issue${unhealthy.length === 1 ? "" : "s"} detected` : "All reported probes healthy"}</strong></p>
    <p>Repair execution: <strong>${data.execution_enabled ? "ENABLED" : "GATED / DISABLED"}</strong> · Repair proposals: ${proposalCount} · Knowledge loaded: ${data.knowledge_items_bootstrapped ?? 0}</p>
    <h3>System Health</h3>
    ${rows}
    <h3>Repair Proposals</h3>
    ${proposalRows || "<p>No high-trust repair proposal is currently available.</p>"}
    <div class="modal-actions">
      <button class="primary" id="refreshHealingDashboard">Run Diagnostics Again</button>
    </div>`);
}

async function loadHealingDashboard(showModal = true) {
  const status = document.querySelector("#healingStatus");
  try {
    const data = await api("/api/healing/status");
    const { unhealthy, proposalCount } = healingSummary(data);
    if (status) {
      status.textContent = unhealthy.length
        ? `${unhealthy.length} issue${unhealthy.length === 1 ? "" : "s"} · ${proposalCount} proposal${proposalCount === 1 ? "" : "s"}`
        : "Healthy · repair execution gated";
    }
    if (showModal) renderHealingDashboard(data);
  } catch (error) {
    if (status) status.textContent = "Diagnostics unavailable";
    if (showModal) {
      openModal(`<h2>RequantAi System Recovery</h2><p>${healingEscape(error.message)}</p>`);
    }
  }
}

const healingButton = document.querySelector("#healingBtn");
if (healingButton) healingButton.onclick = () => loadHealingDashboard(true);

modal.addEventListener("click", event => {
  if (event.target.id === "refreshHealingDashboard") loadHealingDashboard(true);
});

loadHealingDashboard(false);
