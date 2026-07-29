// common.js — shared helpers used across all SymptTrack pages

async function apiFetch(url, options = {}) {
  const opts = {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  };
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (e) { /* no json body */ }
  if (!res.ok) {
    const err = new Error(data.error || "Something went wrong. Please try again.");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function toast(message, type = "info") {
  const stack = document.getElementById("toast-stack");
  if (!stack) return alert(message);
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  const icon = type === "success" ? "✅" : type === "error" ? "⚠️" : "🩺";
  el.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity 250ms ease";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 260);
  }, 3400);
}

function setupMobileNav() {
  const toggle = document.querySelector(".nav-toggle");
  const navbar = document.querySelector(".navbar");
  if (toggle && navbar) {
    toggle.addEventListener("click", () => navbar.classList.toggle("open"));
  }
}

function highlightActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll(".nav-links a").forEach((a) => {
    if (a.getAttribute("href") === path) a.classList.add("active");
  });
}

function formatDate(dateStr, opts = { day: "numeric", month: "short" }) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", opts);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  setupMobileNav();
  highlightActiveNav();
});
