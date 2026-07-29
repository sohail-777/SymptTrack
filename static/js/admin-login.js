document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("admin-login-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    const errBox = document.getElementById("admin-login-error");
    errBox.classList.remove("show");

    const username = document.getElementById("admin-username").value.trim();
    const password = document.getElementById("admin-password").value;

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Signing in...`;
    try {
      await apiFetch("/api/auth/admin/login", { method: "POST", body: { username, password } });
      window.location.href = "/admin/dashboard";
    } catch (err) {
      errBox.textContent = `⚠️ ${err.message}`;
      errBox.classList.add("show");
      btn.disabled = false;
      btn.innerHTML = "Access Admin Panel &nbsp;🔐";
    }
  });
});
