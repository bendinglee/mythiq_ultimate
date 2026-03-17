let mode = "auto";
let lastJobId = null;

const promptEl = document.getElementById("prompt");
const sourceUrlEl = document.getElementById("sourceUrl");
const transcriptEl = document.getElementById("transcript");
const targetCountEl = document.getElementById("targetCount");
const runBtn = document.getElementById("runBtn");
const rerunBtn = document.getElementById("rerunBtn");
const likeBtn = document.getElementById("likeBtn");
const dislikeBtn = document.getElementById("dislikeBtn");
const feedbackNotesEl = document.getElementById("feedbackNotes");

const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const summaryEl = document.getElementById("summary");
const logsEl = document.getElementById("logs");
const criticEl = document.getElementById("critic");
const artifactsEl = document.getElementById("artifacts");
const historyEl = document.getElementById("history");

function setMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll(".chip").forEach(x => {
    x.classList.toggle("active", x.dataset.mode === nextMode);
  });
}

document.querySelectorAll(".chip").forEach(btn => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

function renderResult(data) {
  lastJobId = data.job_id || null;
  statusEl.textContent = data.ok ? "done" : (data.status || "error");
  previewEl.textContent = data.preview || JSON.stringify(data, null, 2);
  summaryEl.textContent = JSON.stringify({
    ok: data.ok,
    feature: data.feature,
    job_id: data.job_id,
    status: data.status,
    metrics: data.metrics,
    attempts: data.attempts || []
  }, null, 2);
  logsEl.textContent = (data.logs || []).join("\n");
  criticEl.textContent = JSON.stringify(data.critic_report || {}, null, 2);
  artifactsEl.innerHTML = "";
  (data.artifacts || []).forEach(a => {
    const link = document.createElement("a");
    link.href = a.path;
    link.target = "_blank";
    link.textContent = `${a.kind}: ${a.path}`;
    artifactsEl.appendChild(link);
  });
}

async function loadHistory() {
  const res = await fetch("/api/history");
  const data = await res.json();
  historyEl.innerHTML = "";
  (data.items || []).forEach(item => {
    const a = document.createElement("a");
    a.href = "#";
    a.textContent = `[${item.feature}] (${item.critique_score ?? "?"}) ${item.prompt || item.source_url || item.job_id}`;
    a.addEventListener("click", (e) => {
      e.preventDefault();
      promptEl.value = item.prompt || "";
      sourceUrlEl.value = item.source_url || "";
      setMode(item.feature || "auto");
    });
    historyEl.appendChild(a);
  });
}

runBtn.addEventListener("click", async () => {
  const payload = {
    prompt: promptEl.value.trim(),
    mode,
    source_url: sourceUrlEl.value.trim(),
    transcript: transcriptEl.value.trim(),
    target_count: Number(targetCountEl.value || 5)
  };
  if (!payload.prompt && !payload.source_url) return;

  statusEl.textContent = "running...";
  const res = await fetch("/api/command", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  renderResult(data);
  loadHistory();
});

rerunBtn.addEventListener("click", async () => {
  if (!lastJobId) return;
  const res = await fetch("/api/rerun", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ job_id: lastJobId })
  });
  const data = await res.json();
  renderResult(data);
  loadHistory();
});

async function sendFeedback(rating) {
  if (!lastJobId) return;
  await fetch("/api/feedback", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      job_id: lastJobId,
      rating,
      notes: feedbackNotesEl.value.trim()
    })
  });
  statusEl.textContent = `feedback saved (${rating})`;
}

likeBtn.addEventListener("click", () => sendFeedback(1));
dislikeBtn.addEventListener("click", () => sendFeedback(-1));

loadHistory();
