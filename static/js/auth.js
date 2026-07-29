// auth.js — login / signup page logic

function switchTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".auth-panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === tab));
  hideError("login-error"); hideError("signup-error");
}

function showError(id, message) {
  const el = document.getElementById(id);
  el.textContent = `⚠️ ${message}`;
  el.classList.add("show");
}
function hideError(id) {
  const el = document.getElementById(id);
  el.classList.remove("show");
  el.textContent = "";
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".auth-tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

  const loginForm = document.getElementById("login-form");
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError("login-error");
    const btn = loginForm.querySelector("button[type=submit]");
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Signing in...`;
    try {
      const data = await apiFetch("/api/auth/login", { method: "POST", body: { email, password } });
      toast(data.message, "success");
      window.location.href = "/home";
    } catch (err) {
      showError("login-error", err.message);
      btn.disabled = false;
      btn.innerHTML = "Log In &nbsp;🔐";
    }
  });

  const signupForm = document.getElementById("signup-form");
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError("signup-error");
    const btn = signupForm.querySelector("button[type=submit]");

    const payload = {
      full_name: document.getElementById("signup-name").value.trim(),
      email: document.getElementById("signup-email").value.trim(),
      password: document.getElementById("signup-password").value,
      dob: document.getElementById("signup-dob").value || null,
      gender: document.getElementById("signup-gender").value,
      phone: document.getElementById("signup-phone").value.trim(),
    };

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Creating account...`;
    try {
      const data = await apiFetch("/api/auth/signup", { method: "POST", body: payload });
      toast(data.message, "success");
      window.location.href = "/home";
    } catch (err) {
      showError("signup-error", err.message);
      btn.disabled = false;
      btn.innerHTML = "Create My Account &nbsp;🎉";
    }
  });
});
