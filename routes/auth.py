import re
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import query, execute
from utils.helpers import log_activity, calc_age

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/signup")
def signup():
    data = request.get_json(force=True, silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    dob = data.get("dob") or None
    gender = data.get("gender") or "prefer_not_to_say"
    phone = (data.get("phone") or "").strip() or None

    if not full_name or len(full_name) < 2:
        return jsonify({"error": "Please enter your full name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    existing = query("SELECT id FROM patients WHERE email = %s", (email,), fetch="one")
    if existing:
        return jsonify({"error": "An account with this email already exists. Please log in instead."}), 409

    pw_hash = generate_password_hash(password)
    patient_id, _ = execute(
        """INSERT INTO patients (full_name, email, phone, password_hash, dob, gender)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (full_name, email, phone, pw_hash, dob, gender),
    )

    session.clear()
    session["patient_id"] = patient_id
    session["patient_name"] = full_name
    session.permanent = True

    log_activity("patient", patient_id, "signup", f"{full_name} created an account")

    return jsonify({
        "message": f"Welcome to SymptTrack, {full_name.split()[0]}! 🎉",
        "patient": {"id": patient_id, "full_name": full_name, "email": email},
    }), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    patient = query("SELECT * FROM patients WHERE email = %s", (email,), fetch="one")
    if not patient or not check_password_hash(patient["password_hash"], password):
        return jsonify({"error": "Incorrect email or password."}), 401
    if not patient["is_active"]:
        return jsonify({"error": "This account has been deactivated. Please contact support."}), 403

    execute("UPDATE patients SET last_login_at = %s WHERE id = %s", (datetime.now(), patient["id"]))

    session.clear()
    session["patient_id"] = patient["id"]
    session["patient_name"] = patient["full_name"]
    session.permanent = True

    log_activity("patient", patient["id"], "login", f"{patient['full_name']} logged in")

    return jsonify({
        "message": f"Welcome back, {patient['full_name'].split()[0]}! 👋",
        "patient": {"id": patient["id"], "full_name": patient["full_name"], "email": patient["email"]},
    })


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out. See you soon! 👋"})


@auth_bp.get("/me")
def me():
    if not session.get("patient_id"):
        return jsonify({"authenticated": False}), 200
    patient = query(
        "SELECT id, full_name, email, phone, dob, gender, blood_group, height_cm, weight_kg, avatar_emoji, streak_count "
        "FROM patients WHERE id = %s", (session["patient_id"],), fetch="one")
    if not patient:
        session.clear()
        return jsonify({"authenticated": False}), 200
    patient["age"] = calc_age(patient.get("dob"))
    patient["dob"] = patient["dob"].isoformat() if patient.get("dob") else None
    return jsonify({"authenticated": True, "patient": patient})


# ---------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------
@auth_bp.post("/admin/login")
def admin_login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    admin = query("SELECT * FROM admins WHERE username = %s", (username,), fetch="one")
    if not admin or not check_password_hash(admin["password_hash"], password):
        return jsonify({"error": "Invalid admin credentials."}), 401

    session.clear()
    session["admin_id"] = admin["id"]
    session["admin_name"] = admin["full_name"]
    session.permanent = True

    log_activity("admin", admin["id"], "login", f"{admin['username']} logged into the admin panel")

    return jsonify({"message": f"Welcome back, {admin['full_name']}.", "admin": {"id": admin["id"], "username": admin["username"]}})


@auth_bp.post("/admin/logout")
def admin_logout():
    session.clear()
    return jsonify({"message": "Admin logged out."})


@auth_bp.get("/admin/me")
def admin_me():
    if not session.get("admin_id"):
        return jsonify({"authenticated": False}), 200
    admin = query("SELECT id, username, full_name, role FROM admins WHERE id = %s", (session["admin_id"],), fetch="one")
    if not admin:
        session.clear()
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "admin": admin})
