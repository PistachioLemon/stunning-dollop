(() => {
  const button = document.querySelector("#learningBtn");
  const statusText = document.querySelector("#learningStatus");
  const modal = document.querySelector("#modal");
  const modalContent = document.querySelector("#modalContent");
  const reply = document.querySelector("#reply");
  let recorder = null;
  let chunks = [];
  let captureStream = null;

  async function learningApi(path, options = {}) {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Operational learning request failed.");
    return data;
  }

  function escaped(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  async function refreshStatus() {
    try {
      const data = await learningApi("/api/learning/status");
      const next = data.schedule?.next_run ? new Date(data.schedule.next_run).toLocaleString() : "disabled";
      statusText.textContent = `${data.lessons} lessons · ${data.selected_occurrences} selected · ${data.awaiting_acknowledgement || 0} awaiting OK · next ${next}`;
      return data;
    } catch (_) {
      statusText.textContent = "Learning service unavailable";
      return null;
    }
  }

  function pendingBatchHtml(data) {
    const batch = (data?.pending_batches || []).find(item => item.status === "awaiting_operator_acknowledgement");
    if (!batch) return "<p><small>No batch is waiting for operator acknowledgement.</small></p>";
    return `<div class="card"><strong>Tonight's TruckLM batch #${batch.id}</strong><br>
      <small>${batch.lesson_ids.length} lessons · ${batch.occurrence_ids.length} selected events</small><br>
      <button class="primary" data-ack-batch="${batch.id}">Acknowledge & approve for 1 AM</button></div>`;
  }

  function openLearning(data) {
    const schedule = data?.schedule;
    modalContent.innerHTML = `
      <h2>RequantAi Operational Learning / TruckLM</h2>
      <p><strong>Training window:</strong> ${schedule?.enabled ? "ON" : "OFF"} · 1:00 AM Pacific</p>
      <p>Driver logoff starts review only. The system prompts for missing particulars; operator acknowledgement authorizes the 1 AM training window.</p>
      <div class="modal-actions">
        <button class="primary" id="driverLogoffReview">Driver logged off · review today</button>
        <button id="learnAllWords">Learn this dispatcher page</button>
        <button id="learnSelection">Learn selected words</button>
        <button id="startScreenLesson">Start screen lesson</button>
      </div>
      <label><input type="checkbox" id="approveLearned"> Include this lesson in tonight's training</label>
      <textarea id="learningNotes" rows="4" placeholder="Add missing particulars, corrections, causes, or the better action to learn."></textarea>
      <div class="modal-actions">
        <button id="manualLesson">Add training particulars</button>
        <button id="prepareTrainingBatch">Prepare tonight's batch</button>
      </div>
      <div id="pendingTraining">${pendingBatchHtml(data)}</div>
      <p><small>Lessons: ${data?.lessons ?? 0} · approved: ${data?.approved_for_training ?? 0} · selected occurrences: ${data?.selected_occurrences ?? 0}</small></p>`;
    modal.showModal();
  }

  button?.addEventListener("click", async () => openLearning(await refreshStatus()));

  async function submitTextLesson(mode, title, content) {
    const notes = document.querySelector("#learningNotes")?.value || "";
    const approved = Boolean(document.querySelector("#approveLearned")?.checked);
    const data = await learningApi("/api/learning/learn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode,
        title,
        content,
        source_url: location.href,
        operator_notes: notes,
        trust: 80,
        approve_for_training: approved
      })
    });
    reply.textContent = `Lesson saved: “${data.title}”.${approved ? " It is selected for tonight's TruckLM batch." : ""}`;
    await refreshStatus();
  }

  modal.addEventListener("click", async event => {
    try {
      if (event.target.id === "driverLogoffReview") {
        const review = await learningApi("/api/learning/driver-logoff", { method: "POST" });
        const prompts = (review.prompts || []).map(p => `<li>${escaped(p)}</li>`).join("");
        document.querySelector("#pendingTraining").innerHTML = `
          <div class="card"><strong>Post-drive review</strong><ul>${prompts}</ul>
          <small>Next training window: ${escaped(review.next_training_window || review.training_window)}</small></div>`;
        document.querySelector("#learningNotes")?.focus();
        reply.textContent = "Post-drive learning review opened. Add anything missed, then prepare tonight's batch.";
      }

      if (event.target.id === "learnAllWords") {
        const clone = document.body.cloneNode(true);
        clone.querySelector("dialog")?.remove();
        const text = clone.innerText.trim();
        if (!text) throw new Error("No readable page text found.");
        await submitTextLesson("page", document.title, text);
        modal.close();
      }

      if (event.target.id === "learnSelection") {
        const text = String(window.getSelection()?.toString() || "").trim();
        if (!text) throw new Error("Select some words first, then press Learn selected words.");
        await submitTextLesson("selection", `Selected text from ${document.title}`, text);
        modal.close();
      }

      if (event.target.id === "manualLesson") {
        const notes = document.querySelector("#learningNotes")?.value.trim();
        if (!notes) throw new Error("Type the training particulars first.");
        const checkbox = document.querySelector("#approveLearned");
        if (checkbox) checkbox.checked = true;
        await submitTextLesson("manual", "Post-drive operator particulars", notes);
        reply.textContent = "Training particulars added and selected for tonight.";
      }

      if (event.target.id === "prepareTrainingBatch") {
        const result = await learningApi("/api/learning/training-batches", { method: "POST" });
        document.querySelector("#pendingTraining").innerHTML = `
          <div class="card"><strong>Tonight's TruckLM batch #${result.batch_id}</strong><br>
          <small>Waiting for your acknowledgement before 1 AM.</small><br>
          <button class="primary" data-ack-batch="${result.batch_id}">Acknowledge & approve for 1 AM</button></div>`;
        reply.textContent = `TruckLM batch ${result.batch_id} prepared. It will not be released at 1 AM until you acknowledge it.`;
      }

      if (event.target.dataset?.ackBatch) {
        const batchId = event.target.dataset.ackBatch;
        const result = await learningApi(`/api/learning/training-batches/${batchId}/acknowledge`, { method: "POST" });
        event.target.disabled = true;
        event.target.textContent = "Approved for 1 AM";
        reply.textContent = `TruckLM batch ${result.batch_id} acknowledged. The dispatcher will release it when the 1 AM Pacific training window opens.`;
        await refreshStatus();
      }

      if (event.target.id === "startScreenLesson") {
        if (!navigator.mediaDevices?.getDisplayMedia || !window.MediaRecorder) {
          throw new Error("This browser does not support screen lesson recording.");
        }
        captureStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
        chunks = [];
        recorder = new MediaRecorder(captureStream, { mimeType: "video/webm" });
        recorder.ondataavailable = e => { if (e.data?.size) chunks.push(e.data); };
        recorder.onstop = async () => {
          const blob = new Blob(chunks, { type: "video/webm" });
          const form = new FormData();
          form.append("recording", blob, "dispatcher-screen-lesson.webm");
          form.append("title", "Operator screen lesson");
          form.append("operator_notes", document.querySelector("#learningNotes")?.value || "");
          form.append("approve_for_training", String(Boolean(document.querySelector("#approveLearned")?.checked)));
          const response = await fetch("/api/learning/screen-recording", { method: "POST", body: form });
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || "Screen lesson upload failed.");
          reply.textContent = "Screen lesson saved. Audio/visual extraction must finish before the lesson becomes a training record.";
          captureStream?.getTracks().forEach(track => track.stop());
          recorder = null;
          await refreshStatus();
        };
        recorder.start(1000);
        event.target.textContent = "Stop screen lesson";
        event.target.id = "stopScreenLesson";
        reply.textContent = "Recording the shared screen lesson. Stop when the demonstration is complete.";
      } else if (event.target.id === "stopScreenLesson") {
        recorder?.stop();
        event.target.textContent = "Saving…";
        event.target.disabled = true;
      }
    } catch (error) {
      reply.textContent = escaped(error.message);
    }
  });

  refreshStatus();
})();
