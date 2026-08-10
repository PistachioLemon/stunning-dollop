const modal = document.querySelector("#modal");
const modalContent = document.querySelector("#modalContent");
const reply = document.querySelector("#reply");
const input = document.querySelector("#chat");

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Dispatcher request failed.");
  return data;
}
function openModal(html) { modalContent.innerHTML = html; modal.showModal(); }
document.querySelector("#closeModal").onclick = () => modal.close();
setInterval(() => { document.querySelector("#clock").textContent = new Date().toLocaleString(); }, 1000);

async function askDispatcher() {
  if (!input.value.trim()) return;
  try { const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ text: input.value }) }); reply.textContent = `${result.agent}: ${result.reply}`; input.value = ""; }
  catch (error) { reply.textContent = error.message; }
}
document.querySelector("#send").onclick = askDispatcher;
input.addEventListener("keydown", event => { if (event.key === "Enter") askDispatcher(); });

async function refreshFleet() {
  const trucks = await api("/api/trucks");
  document.querySelector("#fleetStatus").textContent = trucks.length ? `${trucks.length} truck node${trucks.length === 1 ? "" : "s"} reporting` : "No truck telemetry yet · simulator ready";
  return trucks;
}
document.querySelector("#fleetBtn").onclick = async () => {
  const trucks = await refreshFleet();
  const rows = trucks.map(t => `<div class="med-row"><strong>${t.truck_id}</strong><p>${t.speed_mph ?? 0} mph · fuel ${t.fuel_percent ?? "—"}% · HOS ${t.hos_drive_minutes_remaining ?? "—"} min</p></div>`).join("");
  openModal(`<h2>Fleet State</h2>${rows || "<p>No live truck nodes. CPU-only simulation is available through the telemetry API.</p>"}`);
};
document.querySelector("#dispatchBtn").onclick = () => openModal(`<h2>Load Decision Engine</h2><p>Ranks gross revenue, operating cost, deadhead, loaded miles, and risk. Booking remains operator-approved.</p><p><small>API: POST /api/dispatch/evaluate</small></p>`);
document.querySelector("#telemetryBtn").onclick = () => openModal(`<h2>Truck Telemetry</h2><p>CPU-only simulation is the baseline. GPS works independently; CAN, OBD-II, reefer, load sensors, cargo cameras, and MQTT activate only when their adapters are configured.</p><p>No AI accelerator is required to boot or run dispatch rules.</p>`);
document.querySelector("#cargoBtn").onclick = () => openModal(`<h2>Cargo Vision</h2><p>Truck/load evidence only. Residential cameras are not part of this system.</p><p>Without an accelerator, captured evidence and deterministic checks remain available; vision inference can use CPU models or stay disabled.</p>`);

api("/api/health").then(data => {
  document.querySelector("#systemStatus").textContent = data.runtime.cpu_only_ready ? "CPU BASELINE READY" : "CONFIGURATION BLOCKED";
}).catch(() => { document.querySelector("#systemStatus").textContent = "OFFLINE"; });
refreshFleet().catch(() => { document.querySelector("#fleetStatus").textContent = "Fleet service unavailable"; });
