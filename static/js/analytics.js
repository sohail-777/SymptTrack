// analytics.js — health trend & diagnosis analytics charts

const TREND_COPY = {
  improving: { label: "📈 Improving", cls: "trend-badge-improving", msg: "Your reported severity has been trending down over the last two weeks. Keep it up! 🎉" },
  declining: { label: "📉 Declining", cls: "trend-badge-declining", msg: "Your reported severity has been trending up recently. Consider checking in with a doctor if this continues." },
  stable: { label: "➡️ Stable", cls: "trend-badge-stable", msg: "Your health has been fairly steady over the last two weeks." },
  not_enough_data: { label: "📊 Not enough data", cls: "trend-badge-not_enough_data", msg: "Log symptoms on a few more days so we can show a meaningful trend." },
};

async function loadAnalytics() {
  try {
    const data = await apiFetch("/api/patient/analytics");
    renderTrendBadge(data.direction);
    renderTrendChart(data.trend);
    renderDiagnosesChart(data.top_diagnoses);
    renderMoodBreakdown(data.mood_breakdown);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderTrendBadge(direction) {
  const info = TREND_COPY[direction] || TREND_COPY.not_enough_data;
  const badge = document.getElementById("trend-badge");
  badge.textContent = info.label;
  badge.className = `badge ${info.cls}`;
  document.getElementById("trend-message").textContent = info.msg;
}

function renderTrendChart(trend) {
  const ctx = document.getElementById("trend-chart");
  if (!trend.length) {
    document.getElementById("trend-chart-empty").style.display = "block";
    ctx.style.display = "none";
    return;
  }
  new Chart(ctx, {
    type: "line",
    data: {
      labels: trend.map(t => formatDate(t.date)),
      datasets: [{
        label: "Severity",
        data: trend.map(t => t.severity),
        borderColor: "#0F7173",
        backgroundColor: "rgba(15,113,115,0.12)",
        tension: 0.35,
        fill: true,
        pointBackgroundColor: "#E6425A",
        pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 5, ticks: { stepSize: 1 } } },
    },
  });
}

function renderDiagnosesChart(top) {
  const ctx = document.getElementById("diagnoses-chart");
  if (!top.length) {
    document.getElementById("diagnoses-chart-empty").style.display = "block";
    ctx.style.display = "none";
    return;
  }
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map(t => t.label),
      datasets: [{
        label: "Times Suggested",
        data: top.map(t => t.occurrences),
        backgroundColor: "#14A3A6",
        borderRadius: 8,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { stepSize: 1, precision: 0 } } },
    },
  });
}

function renderMoodBreakdown(moods) {
  const wrap = document.getElementById("mood-breakdown");
  if (!moods.length) { wrap.innerHTML = `<p class="text-muted">No mood data yet.</p>`; return; }
  const emojiMap = { good: "🙂 Good", okay: "😐 Okay", low: "😔 Low" };
  wrap.innerHTML = moods.map(m => `
    <div class="flex justify-between items-center mb-8">
      <span>${emojiMap[m.mood] || m.mood}</span>
      <span class="badge badge-teal">${m.c}×</span>
    </div>`).join("");
}

document.addEventListener("DOMContentLoaded", loadAnalytics);
