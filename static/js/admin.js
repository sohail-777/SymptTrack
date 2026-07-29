// admin.js — admin dashboard logic

function switchAdminTab(tab) {
  document.querySelectorAll(".admin-nav a").forEach(a => a.classList.toggle("active", a.dataset.tab === tab));
  document.querySelectorAll(".admin-view").forEach(v => v.classList.toggle("active", v.id === `view-${tab}`));
  const loaders = { overview: loadOverview, patients: loadPatients, logs: loadLogs, tips: loadTips, settings: loadSettings, activity: loadActivity };
  loaders[tab] && loaders[tab]();
}

// ---------------- Overview ----------------
async function loadOverview() {
  try {
    const s = await apiFetch("/api/admin/stats");
    document.getElementById("ov-total-patients").textContent = s.total_patients;
    document.getElementById("ov-active-patients").textContent = s.active_patients;
    document.getElementById("ov-total-logs").textContent = s.total_logs;
    document.getElementById("ov-logs-today").textContent = s.logs_today;
    document.getElementById("ov-logs-7d").textContent = s.logs_7d;
    document.getElementById("ov-signups-7d").textContent = s.new_signups_7d;
    document.getElementById("ov-avg-severity").textContent = `${s.avg_severity} / 5`;

    const modelBadge = document.getElementById("ov-model-status");
    const statusMap = {
      ready: ["badge-success", "🧠 CORe Model Active"],
      loading: ["badge-amber", "⏳ CORe Model Loading..."],
      unavailable: ["badge-grey", "🔧 Rule Engine Active"],
      not_started: ["badge-grey", "⏸️ Model Not Started"],
    };
    const [cls, label] = statusMap[s.model_status.status] || statusMap.not_started;
    modelBadge.className = `badge ${cls}`;
    modelBadge.textContent = label;

    const list = document.getElementById("ov-top-conditions");
    list.innerHTML = s.top_conditions.length
      ? s.top_conditions.map(c => `<div class="flex justify-between items-center mb-8"><span>${escapeHtml(c.label)}</span><span class="badge badge-teal">${c.occurrences}×</span></div>`).join("")
      : `<p class="text-muted">No diagnosis data yet.</p>`;
  } catch (err) { toast(err.message, "error"); }
}

// ---------------- Patients ----------------
async function loadPatients(q = "") {
  const tbody = document.getElementById("patients-tbody");
  tbody.innerHTML = `<tr><td colspan="6">Loading...</td></tr>`;
  try {
    const data = await apiFetch(`/api/admin/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`);
    if (!data.patients.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-muted">No patients found.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.patients.map(p => `
      <tr>
        <td><strong>${escapeHtml(p.full_name)}</strong></td>
        <td>${escapeHtml(p.email)}</td>
        <td>${p.phone ? escapeHtml(p.phone) : "—"}</td>
        <td><span class="status-dot ${p.is_active ? "on" : "off"}"></span>${p.is_active ? "Active" : "Inactive"}</td>
        <td>${p.streak_count || 0} 🔥</td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="viewPatient(${p.id})">View</button>
          <button class="btn btn-sm ${p.is_active ? "btn-ghost" : "btn-primary"}" onclick="toggleActive(${p.id}, ${p.is_active})">${p.is_active ? "Deactivate" : "Activate"}</button>
          <button class="btn btn-sm btn-ghost" style="color:var(--coral);" onclick="deletePatient(${p.id})">Delete</button>
        </td>
      </tr>`).join("");
  } catch (err) { toast(err.message, "error"); }
}

async function toggleActive(id, isActive) {
  try {
    await apiFetch(`/api/admin/patients/${id}`, { method: "PUT", body: { is_active: isActive ? 0 : 1 } });
    toast("Patient status updated.", "success");
    loadPatients(document.getElementById("patient-search").value);
  } catch (err) { toast(err.message, "error"); }
}

async function deletePatient(id) {
  if (!confirm("Permanently delete this patient and all their records? This cannot be undone.")) return;
  try {
    await apiFetch(`/api/admin/patients/${id}`, { method: "DELETE" });
    toast("Patient deleted.", "success");
    loadPatients();
  } catch (err) { toast(err.message, "error"); }
}

async function viewPatient(id) {
  try {
    const data = await apiFetch(`/api/admin/patients/${id}`);
    const p = data.patient;
    const body = document.getElementById("patient-modal-body");
    body.innerHTML = `
      <h3>${escapeHtml(p.full_name)}</h3>
      <p class="text-muted">${escapeHtml(p.email)} ${p.phone ? "· " + escapeHtml(p.phone) : ""}</p>
      <div class="flex gap-8 mb-16" style="flex-wrap:wrap;">
        <span class="badge badge-teal">Age: ${p.age ?? "—"}</span>
        <span class="badge badge-teal">Gender: ${(p.gender || "-").replace("_"," ")}</span>
        <span class="badge badge-teal">Blood: ${p.blood_group || "—"}</span>
        <span class="badge ${p.is_active ? "badge-success" : "badge-grey"}">${p.is_active ? "Active" : "Inactive"}</span>
      </div>
      <h4>Recent Symptom Logs (${data.logs.length})</h4>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Date</th><th>Symptoms</th><th>Severity</th><th>Top Diagnosis</th></tr></thead>
          <tbody>
            ${data.logs.length ? data.logs.map(l => `
              <tr>
                <td>${l.log_date}</td>
                <td>${escapeHtml((l.symptoms_text || (l.symptoms_tags||[]).join(", ")).slice(0,60))}</td>
                <td>${l.severity}/5</td>
                <td>${l.diagnoses[0] ? escapeHtml(l.diagnoses[0].label) : "—"}</td>
              </tr>`).join("") : `<tr><td colspan="4" class="text-muted">No logs yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
    document.getElementById("patient-modal-backdrop").classList.add("show");
  } catch (err) { toast(err.message, "error"); }
}

// ---------------- Daily Logs ----------------
async function loadLogs(page = 1) {
  const tbody = document.getElementById("logs-tbody");
  tbody.innerHTML = `<tr><td colspan="5">Loading...</td></tr>`;
  const day = document.getElementById("logs-date-filter").value;
  try {
    const data = await apiFetch(`/api/admin/logs?page=${page}${day ? `&date=${day}` : ""}`);
    if (!data.logs.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-muted">No logs found.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.logs.map(l => `
      <tr>
        <td>${l.log_date}</td>
        <td><strong>${escapeHtml(l.full_name)}</strong><br><span class="text-muted" style="font-size:12px;">${escapeHtml(l.email)}</span></td>
        <td>${escapeHtml((l.symptoms_text || (l.symptoms_tags||[]).join(", ") || "—").slice(0,70))}</td>
        <td><span class="badge ${l.severity>=4?"badge-coral":l.severity===3?"badge-amber":"badge-success"}">${l.severity}/5</span></td>
        <td>${l.ai_summary ? escapeHtml(l.ai_summary) : "—"}</td>
      </tr>`).join("");
  } catch (err) { toast(err.message, "error"); }
}

// ---------------- Health Tips CMS ----------------
async function loadTips() {
  const wrap = document.getElementById("tips-admin-list");
  wrap.innerHTML = "Loading...";
  try {
    const data = await apiFetch("/api/admin/health-tips");
    wrap.innerHTML = data.tips.map(t => `
      <div class="card mb-12 flex justify-between items-center" style="flex-wrap:wrap; gap:10px;">
        <div class="flex items-center gap-12">
          <span style="font-size:22px;">${t.icon}</span>
          <div>
            <strong>${escapeHtml(t.title)}</strong>
            <p style="margin:0; font-size:13px;">${escapeHtml(t.content)}</p>
          </div>
        </div>
        <div class="flex gap-8">
          <span class="badge ${t.is_active ? "badge-success" : "badge-grey"}">${t.is_active ? "Live" : "Hidden"}</span>
          <button class="btn btn-sm btn-outline" onclick="toggleTip(${t.id}, ${t.is_active})">${t.is_active ? "Hide" : "Show"}</button>
          <button class="btn btn-sm btn-ghost" style="color:var(--coral);" onclick="deleteTip(${t.id})">Delete</button>
        </div>
      </div>`).join("") || `<p class="text-muted">No tips yet — add one below.</p>`;
  } catch (err) { toast(err.message, "error"); }
}

async function toggleTip(id, isActive) {
  await apiFetch(`/api/admin/health-tips/${id}`, { method: "PUT", body: { is_active: isActive ? 0 : 1 } });
  loadTips();
}
async function deleteTip(id) {
  if (!confirm("Delete this health tip?")) return;
  await apiFetch(`/api/admin/health-tips/${id}`, { method: "DELETE" });
  loadTips();
}

// ---------------- Settings ----------------
async function loadSettings() {
  try {
    const data = await apiFetch("/api/admin/settings");
    document.getElementById("setting-site-name").value = data.settings.site_name || "";
    document.getElementById("setting-tagline").value = data.settings.tagline || "";
  } catch (err) { toast(err.message, "error"); }
}

// ---------------- Activity ----------------
async function loadActivity() {
  const wrap = document.getElementById("activity-list");
  wrap.innerHTML = "Loading...";
  try {
    const data = await apiFetch("/api/admin/activity");
    wrap.innerHTML = data.activity.map(a => `
      <div class="activity-item">
        <div class="activity-dot">${a.actor_type === "admin" ? "🧑‍💼" : a.actor_type === "patient" ? "🙂" : "⚙️"}</div>
        <div>
          <strong>${escapeHtml(a.action.replace(/_/g," "))}</strong>
          <p style="margin:2px 0 0; font-size:13px;">${escapeHtml(a.description || "")}</p>
          <span class="text-muted" style="font-size:11.5px;">${new Date(a.created_at).toLocaleString()}</span>
        </div>
      </div>`).join("") || `<p class="text-muted">No activity yet.</p>`;
  } catch (err) { toast(err.message, "error"); }
}

document.addEventListener("DOMContentLoaded", () => {
  loadOverview();

  document.querySelectorAll(".admin-nav a").forEach(a => a.addEventListener("click", (e) => {
    e.preventDefault();
    switchAdminTab(a.dataset.tab);
  }));

  document.getElementById("admin-logout-btn").addEventListener("click", async () => {
    await apiFetch("/api/auth/admin/logout", { method: "POST" });
    window.location.href = "/admin";
  });

  document.getElementById("patient-search").addEventListener("input", (e) => loadPatients(e.target.value));
  document.getElementById("patient-modal-close").addEventListener("click", () => document.getElementById("patient-modal-backdrop").classList.remove("show"));
  document.getElementById("patient-modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "patient-modal-backdrop") e.currentTarget.classList.remove("show"); });

  document.getElementById("logs-date-filter").addEventListener("change", () => loadLogs());
  document.getElementById("logs-clear-filter").addEventListener("click", () => { document.getElementById("logs-date-filter").value = ""; loadLogs(); });

  document.getElementById("add-tip-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      icon: document.getElementById("tip-icon").value.trim() || "💡",
      title: document.getElementById("tip-title").value.trim(),
      content: document.getElementById("tip-content").value.trim(),
      category: document.getElementById("tip-category").value.trim() || "general",
    };
    if (!payload.title || !payload.content) return toast("Please fill in title and content.", "error");
    try {
      await apiFetch("/api/admin/health-tips", { method: "POST", body: payload });
      toast("Health tip added!", "success");
      e.target.reset();
      loadTips();
    } catch (err) { toast(err.message, "error"); }
  });

  document.getElementById("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/api/admin/settings", {
        method: "PUT",
        body: {
          site_name: document.getElementById("setting-site-name").value.trim(),
          tagline: document.getElementById("setting-tagline").value.trim(),
        },
      });
      toast("Settings saved!", "success");
    } catch (err) { toast(err.message, "error"); }
  });

  document.getElementById("change-password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const val = document.getElementById("new-admin-password").value;
    try {
      await apiFetch("/api/admin/change-password", { method: "PUT", body: { new_password: val } });
      toast("Admin password changed.", "success");
      e.target.reset();
    } catch (err) { toast(err.message, "error"); }
  });
});
