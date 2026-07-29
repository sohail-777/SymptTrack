// records.js — records list + monthly PDF download

let currentPage = 1;

function severityBadgeClass(sev) {
  return sev >= 4 ? "badge-coral" : sev === 3 ? "badge-amber" : "badge-success";
}

async function loadRecords(page = 1) {
  currentPage = page;
  const list = document.getElementById("records-list");
  list.innerHTML = `<div class="card skeleton" style="height:90px;"></div><div class="card skeleton" style="height:90px;"></div>`;

  try {
    const data = await apiFetch(`/api/patient/records?page=${page}`);

    if (!data.logs.length) {
      list.innerHTML = `<div class="empty-state"><span class="emoji">📭</span>No symptom records yet. <a href="/symptoms">Log your first entry →</a></div>`;
    } else {
      list.innerHTML = data.logs.map(renderRecordCard).join("");
    }

    renderPagination(data.page, data.total_pages);
    populateMonthSelect(data.available_months);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderRecordCard(log) {
  const d = new Date(log.log_date + "T00:00:00");
  const day = d.getDate();
  const month = d.toLocaleDateString("en-US", { month: "short" });
  const topDiag = log.diagnoses[0];

  return `
  <div class="card record-card mb-16">
    <div class="record-date-badge">
      <div class="d">${day}</div>
      <div class="m">${month}</div>
    </div>
    <div style="flex:1;">
      <div class="flex justify-between items-center" style="flex-wrap:wrap; gap:8px;">
        <strong>${escapeHtml(log.symptoms_text || (log.symptoms_tags || []).join(", ") || "No description")}</strong>
        <span class="badge ${severityBadgeClass(log.severity)}">${log.severity_label} · ${log.severity}/5</span>
      </div>
      ${log.notes ? `<p style="font-size:13px;">📝 ${escapeHtml(log.notes)}</p>` : ""}
      <div class="record-tags">
        ${(log.symptoms_tags || []).map(t => `<span class="badge badge-teal">${escapeHtml(t)}</span>`).join("")}
      </div>
      ${topDiag ? `<p class="mt-8" style="font-size:13px;">🧠 Top suggestion: <strong>${escapeHtml(topDiag.label)}</strong> (${Math.round(topDiag.probability * 100)}%)</p>` : ""}
    </div>
  </div>`;
}

function renderPagination(page, totalPages) {
  const wrap = document.getElementById("pagination");
  if (totalPages <= 1) { wrap.innerHTML = ""; return; }
  let html = "";
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="btn btn-sm ${i === page ? "btn-primary" : "btn-outline"}" data-page="${i}">${i}</button>`;
  }
  wrap.innerHTML = html;
  wrap.querySelectorAll("button").forEach(b => b.addEventListener("click", () => loadRecords(parseInt(b.dataset.page, 10))));
}

function populateMonthSelect(months) {
  const select = document.getElementById("month-select");
  if (select.dataset.filled === "1") return;
  if (!months.length) {
    const now = new Date();
    months = [`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`];
  }
  select.innerHTML = months.map(m => {
    const [y, mo] = m.split("-");
    const label = new Date(`${y}-${mo}-01T00:00:00`).toLocaleDateString("en-US", { month: "long", year: "numeric" });
    return `<option value="${m}">${label}</option>`;
  }).join("");
  select.dataset.filled = "1";
}

document.addEventListener("DOMContentLoaded", () => {
  loadRecords(1);

  document.getElementById("download-report-btn").addEventListener("click", () => {
    const val = document.getElementById("month-select").value;
    if (!val) return toast("Please select a month first.", "error");
    const [year, month] = val.split("-");
    window.location.href = `/api/patient/records/download/${year}/${parseInt(month, 10)}`;
  });
});
