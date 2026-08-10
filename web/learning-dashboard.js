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
    if (!response.ok) throw new Error(data.detail || "Nova learning request failed.");
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
      statusText.textContent = `${data.lessons} lessons · ${data.selected_occurrences} selected events · next ${next}`;
      return data;
    } catch (_) {
      statusText.textContent = "Learning service unavailable";
      return null;
    }
  }

  function openLearning(data) {
    const schedule = data?.schedule;
    modalContent.innerHTML = `
      <h2>Nova Learn / TruckLM</h2>
      <p><strong>Nightly training:</strong> ${schedule?.enabled ? "ON" : "OFF"} · 1:00 AM Pacific</p>
      <p>Learn adds knowledge immediately. Selected lessons and daily occurrences are automatically batched for TruckLM training at 1 AM. New model candidates are evaluated before promotion.</p>
      <div class="modal-actions">
        <button class="primary" id="learnAllWords">Learn all words on this Nova page</button>
        <button id="learnSelection">Learn selected words</button>
        <button id="startScreenLesson">Start screen lesson</button>
      </div>
      <label><input type="checkbox" id="approveLearned"> Include this lesson in nightly training</label>
      <textarea id="learningNotes" rows="4" placeholder="Operator notes: what should Nova learn from this?"></textarea>
      <div class="modal-actions">
        <button id="manualLesson">Teach a manual lesson</button>
        <button id="queueTrainingNow">Queue training candidate now</button>
      </div>
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
    reply.textContent = `Nova learned “${data.title}”.${approved ? " It is selected for the 1 AM TruckLM batch." : ""}`;
    await refreshStatus();
  }

  modal.addEventListener("click", async event => {
    try {
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
        if (!notes) throw new Error("Type the lesson in Operator notes first.");
        await submitTextLesson("manual", "Operator-taught lesson", notes);
        modal.close();
      }

      if (event.target.id === "queueTrainingNow") {
        const result = await learningApi("/api/learning/training-batches", { method: "POST" });
        reply.textContent = `TruckLM candidate batch ${result.batch_id} queued. Production model promotion remains gated by evaluation.`;
        modal.close();
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
          form.append("recording", blob, "nova-screen-lesson.webm");
          form.append("title", "Operator screen lesson");
          form.append("operator_notes", document.querySelector("#learningNotes")?.value || "");
          form.append("approve_for_training", String(Boolean(document.querySelector("#approveLearned")?.checked)));
          const response = await fetch("/api/learning/screen-recording", { method: "POST", body: form });
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || "Screen lesson upload failed.");
          reply.textContent = "Screen lesson saved. Audio/visual extraction is queued before it can become a training example.";
          captureStream?.getTracks().forEach(track => track.stop());
          recorder = null;
          await refreshStatus();
        };
        recorder.start(1000);
        event.target.textContent = "Stop screen lesson";
        event.target.id = "stopScreenLesson";
        reply.textContent = "Nova is recording the shared screen lesson. Stop when the demonstration is complete.";
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
