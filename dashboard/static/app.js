let selectedJobId = null;
let selectedOutputDir = null;

const depsEl = document.getElementById("deps");
const jobsEl = document.getElementById("jobs");
const logEl = document.getElementById("log");
const openOutputBtn = document.getElementById("openOutput");

async function refreshDeps() {
  depsEl.textContent = "Checking...";
  const response = await fetch("/api/deps");
  const data = await response.json();
  depsEl.textContent = data.output || "No output.";
}

function jobStatusClass(status) {
  return `status-${status}`;
}

async function refreshJobs() {
  const response = await fetch("/api/jobs");
  const jobs = await response.json();
  jobsEl.innerHTML = "";
  if (!jobs.length) {
    jobsEl.innerHTML = '<div class="job"><div class="job-title">No jobs yet</div><div class="job-meta">Run an upload or URL analysis.</div></div>';
    return;
  }
  for (const job of jobs) {
    const item = document.createElement("div");
    item.className = `job ${job.id === selectedJobId ? "active" : ""}`;
    item.innerHTML = `
      <div class="job-title">${escapeHtml(job.label)}</div>
      <div class="job-meta">
        <span class="${jobStatusClass(job.status)}">${escapeHtml(job.status)}</span>
        · ${escapeHtml(job.kind)}
        · ${escapeHtml(job.created_at)}
      </div>
    `;
    item.addEventListener("click", () => selectJob(job.id));
    jobsEl.appendChild(item);
  }
}

async function selectJob(jobId) {
  selectedJobId = jobId;
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await response.json();
  selectedOutputDir = job.output_dir;
  openOutputBtn.disabled = !selectedOutputDir;
  logEl.textContent = job.log || "Job has not produced output yet.";
  await refreshJobs();
}

async function submitUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = new FormData(form);
  const response = await fetch("/api/analyze-upload", { method: "POST", body });
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "Upload failed.");
    return;
  }
  await selectJob(data.job_id);
}

async function submitUrl(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = new URLSearchParams(new FormData(form));
  const response = await fetch("/api/analyze-url", { method: "POST", body });
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "URL analysis failed.");
    return;
  }
  await selectJob(data.job_id);
}

async function openOutput() {
  if (!selectedOutputDir) return;
  await fetch("/api/open-output", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: selectedOutputDir })
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".form").forEach((f) => f.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`${tab.dataset.tab}Form`).classList.add("active");
  });
});

document.getElementById("uploadForm").addEventListener("submit", submitUpload);
document.getElementById("urlForm").addEventListener("submit", submitUrl);
document.getElementById("refreshDeps").addEventListener("click", refreshDeps);
document.getElementById("refreshJobs").addEventListener("click", refreshJobs);
openOutputBtn.addEventListener("click", openOutput);

setInterval(async () => {
  await refreshJobs();
  if (selectedJobId) {
    const current = selectedJobId;
    const response = await fetch(`/api/jobs/${current}`);
    if (response.ok && selectedJobId === current) {
      const job = await response.json();
      logEl.textContent = job.log || "Job has not produced output yet.";
      selectedOutputDir = job.output_dir;
      openOutputBtn.disabled = !selectedOutputDir;
    }
  }
}, 2500);

refreshDeps();
refreshJobs();
