// symptoms.js — interactive calendar + symptom logging modal

const COMMON_SYMPTOMS = [
  "Fever", "Headache", "Cough", "Sore throat", "Fatigue", "Nausea",
  "Vomiting", "Diarrhea", "Body ache", "Chills", "Runny nose", "Dizziness",
  "Chest pain", "Shortness of breath", "Stomach pain", "Rash", "Joint pain", "Anxious"
];

let state = {
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1, // 1-12
  selectedDate: null,
  selectedTags: new Set(),
  calendarDays: {},
};

const MONTH_NAMES = ["January","February","March","April","May","June","July","August","September","October","November","December"];

function renderChips() {
  const wrap = document.getElementById("symptom-chip-grid");
  wrap.innerHTML = COMMON_SYMPTOMS.map(s => `<div class="chip" data-symptom="${s}">${s}</div>`).join("");
  wrap.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const s = chip.dataset.symptom;
      if (state.selectedTags.has(s)) { state.selectedTags.delete(s); chip.classList.remove("selected"); }
      else { state.selectedTags.add(s); chip.classList.add("selected"); }
    });
  });
}

async function loadCalendar() {
  const grid = document.getElementById("calendar-grid");
  document.getElementById("calendar-title").textContent = `${MONTH_NAMES[state.month - 1]} ${state.year}`;

  try {
    const data = await apiFetch(`/api/patient/calendar/${state.year}/${state.month}`);
    state.calendarDays = data.days;
  } catch (err) {
    toast(err.message, "error");
    state.calendarDays = {};
  }

  const firstDay = new Date(state.year, state.month - 1, 1);
  const startWeekday = firstDay.getDay();
  const daysInMonth = new Date(state.year, state.month, 0).getDate();
  const todayIso = new Date().toISOString().slice(0, 10);

  let html = "";
  for (let i = 0; i < startWeekday; i++) html += `<div class="calendar-day empty"></div>`;

  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${state.year}-${String(state.month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const severity = state.calendarDays[iso];
    const sevClass = severity ? `logged sev-${severity}` : "";
    const todayClass = iso === todayIso ? "today" : "";
    html += `<div class="calendar-day ${sevClass} ${todayClass}" data-date="${iso}">
      <span>${d}</span>${severity ? '<span class="dot"></span>' : ""}
    </div>`;
  }
  grid.innerHTML = html;

  grid.querySelectorAll(".calendar-day:not(.empty)").forEach(el => {
    el.addEventListener("click", () => openModal(el.dataset.date));
  });
}

function changeMonth(delta) {
  state.month += delta;
  if (state.month > 12) { state.month = 1; state.year++; }
  if (state.month < 1) { state.month = 12; state.year--; }
  loadCalendar();
}

async function openModal(dateIso) {
  state.selectedDate = dateIso;
  state.selectedTags = new Set();
  document.getElementById("modal-date-label").textContent = formatDate(dateIso, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  document.getElementById("symptom-text").value = "";
  document.getElementById("symptom-notes").value = "";
  document.getElementById("severity-range").value = 3;
  updateSeverityEmoji(3);
  document.getElementById("diagnosis-result").style.display = "none";
  document.querySelectorAll('input[name=mood]').forEach(r => r.checked = r.value === "okay");

  renderChips();

  try {
    const data = await apiFetch(`/api/patient/symptoms/${dateIso}`);
    if (data.log) {
      document.getElementById("symptom-text").value = data.log.symptoms_text || "";
      document.getElementById("symptom-notes").value = data.log.notes || "";
      document.getElementById("severity-range").value = data.log.severity;
      updateSeverityEmoji(data.log.severity);
      (data.log.symptoms_tags || []).forEach(tag => {
        state.selectedTags.add(tag);
        const chip = document.querySelector(`.chip[data-symptom="${tag}"]`);
        if (chip) chip.classList.add("selected");
      });
      if (data.log.mood) {
        const r = document.querySelector(`input[name=mood][value="${data.log.mood}"]`);
        if (r) r.checked = true;
      }
      if (data.diagnoses && data.diagnoses.length) renderDiagnosis(data.diagnoses);
    }
  } catch (err) { /* no existing log — fine */ }

  document.getElementById("modal-backdrop").classList.add("show");
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.remove("show");
}

function updateSeverityEmoji(val) {
  const map = { 1: "😌", 2: "🙂", 3: "😕", 4: "😣", 5: "🤒" };
  document.getElementById("severity-emoji").textContent = map[val] || "😕";
  document.getElementById("severity-value").textContent = val;
}

function renderDiagnosis(diagnoses) {
  const box = document.getElementById("diagnosis-result");
  box.style.display = "block";
  box.innerHTML = `
    <h4>🧠 AI-Assisted Suggestions</h4>
    ${diagnoses.map(d => `
      <div class="diagnosis-item">
        <span>${escapeHtml(d.label)}</span>
        <div class="flex items-center gap-8">
          <div class="diagnosis-bar"><div class="diagnosis-bar-fill" style="width:${Math.round((d.prob ?? d.probability) * 100)}%"></div></div>
          <span class="text-mono" style="font-size:12px;">${Math.round((d.prob ?? d.probability) * 100)}%</span>
        </div>
      </div>`).join("")}
    <div class="diagnosis-disclaimer">⚠️ <span>This is an automated suggestion, not a medical diagnosis. Please consult a doctor for confirmation.</span></div>
  `;
}

async function submitSymptoms(e) {
  e.preventDefault();
  const btn = document.getElementById("submit-symptom-btn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Analyzing...`;

  const mood = document.querySelector('input[name=mood]:checked')?.value || null;

  const payload = {
    date: state.selectedDate,
    symptoms_text: document.getElementById("symptom-text").value.trim(),
    symptoms_tags: Array.from(state.selectedTags),
    severity: parseInt(document.getElementById("severity-range").value, 10),
    mood,
    notes: document.getElementById("symptom-notes").value.trim(),
  };

  try {
    const data = await apiFetch("/api/patient/symptoms", { method: "POST", body: payload });
    toast(data.message, "success");
    renderDiagnosis(data.diagnoses);
    loadCalendar();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "Save &amp; Get Diagnosis 🩺";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadCalendar();
  document.getElementById("prev-month").addEventListener("click", () => changeMonth(-1));
  document.getElementById("next-month").addEventListener("click", () => changeMonth(1));
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") closeModal(); });
  document.getElementById("severity-range").addEventListener("input", (e) => updateSeverityEmoji(e.target.value));
  document.getElementById("symptom-form").addEventListener("submit", submitSymptoms);
  document.getElementById("log-today-btn").addEventListener("click", () => openModal(new Date().toISOString().slice(0, 10)));
});
