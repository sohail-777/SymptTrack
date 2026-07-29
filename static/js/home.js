// home.js — dashboard home page

const SEVERITY_EMOJI = { 1: "😌", 2: "🙂", 3: "😕", 4: "😣", 5: "🤒" };

async function loadSummary() {
  try {
    const data = await apiFetch("/api/patient/dashboard-summary");
    document.getElementById("greeting-name").textContent = data.patient_name.split(" ")[0];
    document.getElementById("nav-user-emoji").textContent = data.avatar_emoji;
    document.getElementById("stat-streak").textContent = `${data.streak_days} 🔥`;
    document.getElementById("stat-total").textContent = data.total_logs;
    document.getElementById("stat-avg").textContent = data.avg_severity_30d ? `${data.avg_severity_30d} / 5` : "—";
    document.getElementById("stat-last").textContent = data.last_log_date ? formatDate(data.last_log_date) : "No logs yet";

    const banner = document.getElementById("logged-today-banner");
    if (!data.logged_today) {
      banner.innerHTML = `You haven't logged today yet — <a href="/symptoms">tap here to check in 🩺</a>`;
      banner.style.display = "block";
    } else {
      banner.style.display = "none";
    }
  } catch (err) {
    toast(err.message, "error");
  }
}

async function loadTips() {
  const wrap = document.getElementById("tips-grid");
  try {
    const data = await apiFetch("/api/patient/health-tips");
    wrap.innerHTML = data.tips.map(t => `
      <div class="card card-hover tip-card">
        <div class="tip-emoji">${t.icon}</div>
        <div>
          <h4>${escapeHtml(t.title)}</h4>
          <p>${escapeHtml(t.content)}</p>
        </div>
      </div>`).join("");
  } catch (err) {
    wrap.innerHTML = `<p class="text-muted">Couldn't load health tips right now.</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadSummary();
  loadTips();
});
