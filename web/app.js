const api = async (path, options = {}) => {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Nova could not complete that action.");
  return data;
};

const modal = document.querySelector("#modal");
const modalContent = document.querySelector("#modalContent");
const reply = document.querySelector("#reply");
let activeSOS = null;
let sosTimer = null;

function openModal(html) {
  modalContent.innerHTML = html;
  modal.showModal();
}
document.querySelector("#closeModal").onclick = () => modal.close();

function updateClock() {
  document.querySelector("#clock").textContent = new Intl.DateTimeFormat("en-US", {
    weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit"
  }).format(new Date());
}
updateClock();
setInterval(updateClock, 30000);

async function askNova() {
  const input = document.querySelector("#chat");
  if (!input.value.trim()) return;
  reply.textContent = "Thinking…";
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ text: input.value }) });
    reply.textContent = result.reply;
    input.value = "";
  } catch (error) { reply.textContent = error.message; }
}
document.querySelector("#send").onclick = askNova;
document.querySelector("#chat").addEventListener("keydown", e => { if (e.key === "Enter") askNova(); });

document.querySelector("#medicationBtn").onclick = async () => {
  const items = await api("/api/medications");
  const rows = items.length ? items.map(item => `
    <div class="med-row"><strong>${item.due_time} — ${item.name}</strong><p>${item.dosage}</p>
    <div class="modal-actions"><button class="primary" onclick="recordDose(${item.id}, 'taken')">I took it</button>
    <button onclick="recordDose(${item.id}, 'skipped')">Skip this dose</button></div></div>`).join("") :
    "<p>No medications are scheduled yet. Add them from the caregiver setup screen or API.</p>";
  openModal(`<h2>Medication Schedule</h2>${rows}`);
};
window.recordDose = async (id, status) => {
  await api(`/api/medications/${id}/record`, { method: "POST", body: JSON.stringify({ status }) });
  modal.close();
  reply.textContent = status === "taken" ? "Recorded. You took your medication." : "Recorded as skipped.";
};

document.querySelector("#notesBtn").onclick = () => openModal(`
  <h2>Family Note</h2><p>Save a message, thought, or memory.</p>
  <div class="modal-actions"><input id="noteBody" placeholder="Type your note…">
  <button class="primary" id="saveNote">Save Note</button></div>`);
modal.addEventListener("click", async event => {
  if (event.target.id === "saveNote") {
    const body = document.querySelector("#noteBody").value;
    if (!body.trim()) return;
    await api("/api/notes", { method: "POST", body: JSON.stringify({ category: "family", body }) });
    modal.close();
    reply.textContent = "Saved. Your family note is safe in Nova.";
  }
});

document.querySelector("#homeBtn").onclick = () => openModal(`
  <h2>My Home</h2><p>Home Assistant controls appear here after it is connected.</p>
  <div class="modal-actions"><button class="primary" onclick="homeAction('light','turn_on','light.living_room')">Living room lights on</button>
  <button onclick="homeAction('light','turn_off','light.living_room')">Living room lights off</button></div>`);
window.homeAction = async (domain, service, entity_id) => {
  const result = await api("/api/home/control", { method: "POST", body: JSON.stringify({ domain, service, entity_id }) });
  modal.close();
  reply.textContent = `Home command accepted in ${result.mode} mode.`;
};

document.querySelector("#checkinBtn").onclick = () => openModal(`
  <h2>How are you feeling?</h2><div class="modal-actions">
  <button class="primary" onclick="checkin('good')">I’m doing well</button>
  <button onclick="checkin('okay')">I’m okay</button>
  <button class="danger" onclick="checkin('need_help')">I need some help</button></div>`);
window.checkin = async feeling => {
  await api("/api/notes", { method: "POST", body: JSON.stringify({ category: "check_in", body: feeling }) });
  modal.close();
  reply.textContent = feeling === "need_help" ? "I heard you. Press SOS for urgent help, or leave a family note." : "Thank you. I recorded today’s check-in.";
};

async function refreshLockerStatus() {
  try {
    const status = await api("/api/locker/status");
    document.querySelector("#lockerStatus").textContent =
      `${status.state === "locked" ? "Locked" : "Unlocked"} · ${status.mode} mode`;
  } catch (_) {
    document.querySelector("#lockerStatus").textContent = "Locker unavailable";
  }
}

document.querySelector("#packageBtn").onclick = async () => {
  const [status, packages] = await Promise.all([
    api("/api/locker/status"),
    api("/api/packages")
  ]);
  const expected = packages.filter(item => item.state === "expected");
  const rows = expected.length
    ? expected.map(item => `<div class="med-row"><strong>${item.carrier} · ${item.tracking_code}</strong><p>For ${item.recipient}</p>
      <div class="modal-actions"><button class="primary" onclick="generatePackageCode(${item.id}, 'qr')">Generate QR</button>
      <button onclick="generatePackageCode(${item.id}, 'code128')">Generate Barcode</button></div></div>`).join("")
    : "<p>No expected deliveries are registered.</p>";
  openModal(`<h2>Package Guardian</h2>
    <p>Locker: <strong>${status.state}</strong> · ${status.mode} mode</p>
    ${rows}
    <div class="modal-actions">
      <input id="packageScanCode" autocomplete="off" placeholder="Scan or enter QR/barcode">
      <button class="primary" id="submitPackageScan">Verify & Open</button>
      <button id="cameraPackageScan">Use Camera Scanner</button>
      <video id="scannerVideo" playsinline hidden></video>
      <input id="lockerPin" inputmode="numeric" type="password" placeholder="Operator PIN for controls or generator">
      <button id="manualLockerUnlock">Authorized Unlock</button>
      <button id="manualLockerLock">Authorized Lock</button>
    </div>`);
  setTimeout(() => document.querySelector("#packageScanCode")?.focus(), 50);
};

window.generatePackageCode = async (deliveryId, codeType) => {
  const pin = document.querySelector("#lockerPin")?.value;
  if (!pin) {
    reply.textContent = "Enter the package-locker operator PIN first.";
    return;
  }
  try {
    const generated = await api(`/api/packages/${deliveryId}/access-code`, {
      method: "POST",
      body: JSON.stringify({
        operator_pin: pin,
        code_type: codeType,
        expires_minutes: 30
      })
    });
    openModal(`<h2>${codeType === "qr" ? "One-Time QR Code" : "One-Time Barcode"}</h2>
      <p>Expires ${new Date(generated.expires_at).toLocaleString()}. It works once.</p>
      <img class="code-preview" src="${generated.image_data_url}" alt="One-time package locker access code">
      <div class="modal-actions"><a class="download-code" href="${generated.image_data_url}" download="nova-package-${deliveryId}.${codeType === "qr" ? "png" : "svg"}">Download Code</a></div>`);
  } catch (error) { reply.textContent = error.message; }
};

async function scanPackageCode(code) {
  const result = await api("/api/packages/scan", {
    method: "POST", body: JSON.stringify({ code })
  });
  modal.close();
  reply.textContent = `Package verified. Locker opened briefly for delivery ${result.delivery_id}.`;
  refreshLockerStatus();
}

modal.addEventListener("click", async event => {
  if (event.target.id === "submitPackageScan") {
    const code = document.querySelector("#packageScanCode").value.trim();
    if (!code) return;
    try { await scanPackageCode(code); }
    catch (error) { reply.textContent = error.message; }
  }
  if (event.target.id === "cameraPackageScan") {
    if (!("BarcodeDetector" in window)) {
      reply.textContent = "This browser cannot scan with the camera. Use a USB scanner or enter the code.";
      return;
    }
    const video = document.querySelector("#scannerVideo");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = stream;
      video.hidden = false;
      await video.play();
      const detector = new BarcodeDetector({ formats: ["qr_code", "code_128"] });
      const timer = setInterval(async () => {
        const found = await detector.detect(video);
        if (!found.length) return;
        clearInterval(timer);
        stream.getTracks().forEach(track => track.stop());
        await scanPackageCode(found[0].rawValue);
      }, 350);
    } catch (error) { reply.textContent = `Camera scan failed: ${error.message}`; }
  }
  if (event.target.id === "manualLockerUnlock" || event.target.id === "manualLockerLock") {
    const pin = document.querySelector("#lockerPin").value;
    const operation = event.target.id === "manualLockerUnlock" ? "unlock" : "lock";
    const body = operation === "unlock"
      ? { pin, reason: "touchscreen authorized unlock" }
      : { pin, reason: "touchscreen authorized lock" };
    try {
      const status = await api(`/api/locker/${operation}`, {
        method: "POST", body: JSON.stringify(body)
      });
      modal.close();
      reply.textContent = `Package locker is ${status.state}.`;
      refreshLockerStatus();
    } catch (error) { reply.textContent = error.message; }
  }
});

document.querySelector("#sosBtn").onclick = async () => {
  activeSOS = await api("/api/sos", { method: "POST", body: JSON.stringify({ reason: "Touchscreen SOS button pressed" }) });
  let remaining = activeSOS.countdown_seconds;
  openModal(`<h2>Emergency countdown</h2><p>Nova will prepare the emergency alert in <strong id="sosSeconds">${remaining}</strong> seconds.</p>
    <p>You can cancel with your emergency PIN.</p><div class="modal-actions">
    <input id="sosPin" inputmode="numeric" type="password" placeholder="Emergency PIN">
    <button class="primary" id="cancelSOS">Cancel SOS</button></div>`);
  sosTimer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(sosTimer);
      openModal("<h2>Emergency alert ready</h2><p>Nova completed the local safety workflow. Outbound calling remains disabled until a caregiver configures an approved provider.</p>");
    } else {
      const seconds = document.querySelector("#sosSeconds");
      if (seconds) seconds.textContent = remaining;
    }
  }, 1000);
};
modal.addEventListener("click", async event => {
  if (event.target.id === "cancelSOS" && activeSOS) {
    const pin = document.querySelector("#sosPin").value;
    try {
      await api("/api/sos/cancel", { method: "POST", body: JSON.stringify({ session_id: activeSOS.session_id, pin }) });
      clearInterval(sosTimer);
      modal.close();
      reply.textContent = "SOS cancelled.";
      activeSOS = null;
    } catch (error) { document.querySelector("#sosPin").value = ""; reply.textContent = error.message; }
  }
});

api("/api/health").then(data => {
  if (!data.simulation) document.querySelector(".status").innerHTML = "<span></span> NOVA LIVE";
}).catch(() => document.querySelector(".status").textContent = "NOVA OFFLINE");
refreshLockerStatus();

async function refreshCameraStatus() {
  try {
    const data = await api("/api/security-cameras");
    const status = data.status;
    document.querySelector("#cameraStatus").textContent =
      `${status.camera_count} camera${status.camera_count === 1 ? "" : "s"} · ${status.privacy_mode ? "Privacy on" : status.mode}`;
  } catch (_) {
    document.querySelector("#cameraStatus").textContent = "Camera module unavailable";
  }
}

document.querySelector("#cameraBtn").onclick = async () => {
  const data = await api("/api/security-cameras");
  const cameras = data.cameras.length ? data.cameras.map(camera => `
    <div class="med-row camera-row">
      <div><strong>${camera.name}</strong><p>${camera.room} · ${camera.kind}</p></div>
      <div><span class="camera-badge">${camera.status}</span>
      <button onclick="previewSecurityCamera(${camera.id}, '${camera.name.replaceAll("'", "\\'")}')">View</button>
      <button onclick="simulateCameraEvent(${camera.id})">Test motion</button></div>
    </div>`).join("") : "<p>No cameras enrolled. Add a safe simulated camera below.</p>";
  openModal(`<h2>Home Security Cameras</h2>
    <p>${data.status.mode} mode · Recording policy: ${data.status.recording_policy}</p>
    ${cameras}
    <div class="modal-actions">
      <button class="${data.status.privacy_mode ? "primary" : "danger"}" id="toggleCameraPrivacy">
        ${data.status.privacy_mode ? "Disable Privacy Mode" : "Enable Privacy Mode"}
      </button>
      <input id="cameraName" placeholder="Camera name (Front Door)">
      <input id="cameraRoom" placeholder="Room or area">
      <select id="cameraKind">
        <option value="doorbell">Doorbell</option><option value="outdoor">Outdoor</option>
        <option value="indoor">Indoor</option><option value="driveway">Driveway</option>
        <option value="locker">Package locker</option>
      </select>
      <button class="primary" id="addSimCamera">Add Simulated Camera</button>
    </div>`);
};

window.previewSecurityCamera = async (cameraId, name) => {
  try {
    const preview = await api(`/api/security-cameras/${cameraId}/preview`);
    openModal(`<h2>${name}</h2><div class="camera-preview"><div><strong>SAFE ${preview.mode.toUpperCase()} VIEW</strong><p>${preview.message}</p></div></div>`);
  } catch (error) { reply.textContent = error.message; }
};

window.simulateCameraEvent = async cameraId => {
  try {
    await api(`/api/security-cameras/${cameraId}/events`, {
      method: "POST",
      body: JSON.stringify({ event_type: "motion", confidence: 0.94, description: "Simulated motion test" })
    });
    reply.textContent = "Camera motion test recorded in Nova’s audit trail.";
  } catch (error) { reply.textContent = error.message; }
};

modal.addEventListener("click", async event => {
  if (event.target.id === "toggleCameraPrivacy") {
    const data = await api("/api/security-cameras");
    await api("/api/security-cameras/privacy", {
      method: "POST", body: JSON.stringify({ enabled: !data.status.privacy_mode })
    });
    modal.close();
    reply.textContent = `Camera privacy mode ${data.status.privacy_mode ? "disabled" : "enabled"}.`;
    refreshCameraStatus();
  }
  if (event.target.id === "addSimCamera") {
    const name = document.querySelector("#cameraName").value.trim();
    const room = document.querySelector("#cameraRoom").value.trim();
    const kind = document.querySelector("#cameraKind").value;
    if (!name || !room) return;
    await api("/api/security-cameras", {
      method: "POST",
      body: JSON.stringify({ name, room, kind, connection: "simulation" })
    });
    modal.close();
    reply.textContent = `${name} added safely in simulation mode.`;
    refreshCameraStatus();
  }
});

refreshCameraStatus();
