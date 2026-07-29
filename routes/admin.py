from datetime import date, timedelta
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from db import query, execute
from utils.decorators import admin_login_required
from utils.helpers import log_activity, json_loads, calc_age
from ml.diagnosis_model import get_model_status

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/stats")
@admin_login_required
def stats():
    total_patients = query("SELECT COUNT(*) c FROM patients", fetch="one")["c"]
    active_patients = query("SELECT COUNT(*) c FROM patients WHERE is_active=1", fetch="one")["c"]
    total_logs = query("SELECT COUNT(*) c FROM symptom_logs", fetch="one")["c"]
    logs_today = query("SELECT COUNT(*) c FROM symptom_logs WHERE log_date=%s", (date.today(),), fetch="one")["c"]
    logs_7d = query(
        "SELECT COUNT(*) c FROM symptom_logs WHERE log_date >= %s", (date.today() - timedelta(days=7),), fetch="one")["c"]
    new_signups_7d = query(
        "SELECT COUNT(*) c FROM patients WHERE created_at >= %s", (date.today() - timedelta(days=7),), fetch="one")["c"]
    top_conditions = query(
        """SELECT label, COUNT(*) AS occurrences FROM diagnoses
           GROUP BY label ORDER BY occurrences DESC LIMIT 5""")
    severity_avg = query("SELECT AVG(severity) a FROM symptom_logs", fetch="one")["a"]

    return jsonify({
        "total_patients": total_patients,
        "active_patients": active_patients,
        "total_logs": total_logs,
        "logs_today": logs_today,
        "logs_7d": logs_7d,
        "new_signups_7d": new_signups_7d,
        "top_conditions": top_conditions,
        "avg_severity": round(float(severity_avg), 2) if severity_avg else 0,
        "model_status": get_model_status(),
    })


@admin_bp.get("/patients")
@admin_login_required
def list_patients():
    search = request.args.get("q", "").strip()
    if search:
        rows = query(
            "SELECT id, full_name, email, phone, gender, is_active, created_at, streak_count FROM patients "
            "WHERE full_name LIKE %s OR email LIKE %s ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%"))
    else:
        rows = query(
            "SELECT id, full_name, email, phone, gender, is_active, created_at, streak_count FROM patients "
            "ORDER BY created_at DESC")
    for r in rows:
        r["created_at"] = r["created_at"].isoformat()
    return jsonify({"patients": rows})


@admin_bp.get("/patients/<int:pid>")
@admin_login_required
def patient_detail(pid):
    patient = query("SELECT * FROM patients WHERE id=%s", (pid,), fetch="one")
    if not patient:
        return jsonify({"error": "Patient not found."}), 404
    patient.pop("password_hash", None)
    patient["created_at"] = patient["created_at"].isoformat()
    patient["dob"] = patient["dob"].isoformat() if patient.get("dob") else None
    patient["age"] = calc_age(patient.get("dob"))

    logs = query(
        "SELECT * FROM symptom_logs WHERE patient_id=%s ORDER BY log_date DESC LIMIT 60", (pid,))
    for log in logs:
        log["log_date"] = log["log_date"].isoformat()
        log["created_at"] = log["created_at"].isoformat()
        log["symptoms_tags"] = json_loads(log.get("symptoms_tags"))
        diags = query("SELECT label, probability FROM diagnoses WHERE log_id=%s ORDER BY probability DESC LIMIT 3", (log["id"],))
        log["diagnoses"] = diags

    return jsonify({"patient": patient, "logs": logs})


@admin_bp.put("/patients/<int:pid>")
@admin_login_required
def update_patient(pid):
    data = request.get_json(force=True, silent=True) or {}
    fields = ["full_name", "phone", "gender", "blood_group", "is_active"]
    updates, values = [], []
    for f in fields:
        if f in data:
            updates.append(f"{f} = %s")
            values.append(data[f])
    if not updates:
        return jsonify({"error": "Nothing to update."}), 400
    values.append(pid)
    execute(f"UPDATE patients SET {', '.join(updates)} WHERE id=%s", tuple(values))
    log_activity("admin", session["admin_id"], "patient_update", f"Updated patient #{pid}")
    return jsonify({"message": "Patient record updated."})


@admin_bp.delete("/patients/<int:pid>")
@admin_login_required
def delete_patient(pid):
    execute("DELETE FROM patients WHERE id=%s", (pid,))
    log_activity("admin", session["admin_id"], "patient_delete", f"Deleted patient #{pid}")
    return jsonify({"message": "Patient record deleted."})


@admin_bp.get("/logs")
@admin_login_required
def all_logs():
    day = request.args.get("date")
    page = max(1, int(request.args.get("page", 1)))
    per_page = 15
    offset = (page - 1) * per_page

    base_sql = """SELECT s.*, p.full_name, p.email FROM symptom_logs s
                  JOIN patients p ON p.id = s.patient_id"""
    params = []
    if day:
        base_sql += " WHERE s.log_date = %s"
        params.append(day)
    base_sql += " ORDER BY s.log_date DESC, s.created_at DESC LIMIT %s OFFSET %s"
    params += [per_page, offset]

    logs = query(base_sql, tuple(params))
    for log in logs:
        log["log_date"] = log["log_date"].isoformat()
        log["created_at"] = log["created_at"].isoformat()
        log["symptoms_tags"] = json_loads(log.get("symptoms_tags"))

    count_sql = "SELECT COUNT(*) c FROM symptom_logs" + (" WHERE log_date=%s" if day else "")
    total = query(count_sql, (day,) if day else None, fetch="one")["c"]

    return jsonify({"logs": logs, "page": page, "total": total, "total_pages": max(1, (total + per_page - 1)//per_page)})


@admin_bp.get("/activity")
@admin_login_required
def activity_feed():
    rows = query("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 100")
    for r in rows:
        r["created_at"] = r["created_at"].isoformat()
    return jsonify({"activity": rows})


# ---------------------------------------------------------------
# CMS: settings + health tips
# ---------------------------------------------------------------
@admin_bp.get("/settings")
@admin_login_required
def get_settings():
    rows = query("SELECT setting_key, setting_value FROM settings")
    return jsonify({"settings": {r["setting_key"]: r["setting_value"] for r in rows}})


@admin_bp.put("/settings")
@admin_login_required
def update_settings():
    data = request.get_json(force=True, silent=True) or {}
    for key, value in data.items():
        execute(
            "INSERT INTO settings (setting_key, setting_value) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE setting_value = %s",
            (key, value, value))
    log_activity("admin", session["admin_id"], "settings_update", f"Updated settings: {list(data.keys())}")
    return jsonify({"message": "Settings saved."})


@admin_bp.get("/health-tips")
@admin_login_required
def admin_list_tips():
    rows = query("SELECT * FROM health_tips ORDER BY id DESC")
    return jsonify({"tips": rows})


@admin_bp.post("/health-tips")
@admin_login_required
def admin_add_tip():
    data = request.get_json(force=True, silent=True) or {}
    tip_id, _ = execute(
        "INSERT INTO health_tips (icon, title, content, category) VALUES (%s,%s,%s,%s)",
        (data.get("icon", "💡"), data.get("title", ""), data.get("content", ""), data.get("category", "general")))
    return jsonify({"message": "Health tip added.", "id": tip_id}), 201


@admin_bp.put("/health-tips/<int:tip_id>")
@admin_login_required
def admin_update_tip(tip_id):
    data = request.get_json(force=True, silent=True) or {}
    fields = ["icon", "title", "content", "category", "is_active"]
    updates, values = [], []
    for f in fields:
        if f in data:
            updates.append(f"{f} = %s")
            values.append(data[f])
    if not updates:
        return jsonify({"error": "Nothing to update."}), 400
    values.append(tip_id)
    execute(f"UPDATE health_tips SET {', '.join(updates)} WHERE id=%s", tuple(values))
    return jsonify({"message": "Health tip updated."})


@admin_bp.delete("/health-tips/<int:tip_id>")
@admin_login_required
def admin_delete_tip(tip_id):
    execute("DELETE FROM health_tips WHERE id=%s", (tip_id,))
    return jsonify({"message": "Health tip deleted."})


@admin_bp.put("/change-password")
@admin_login_required
def change_admin_password():
    data = request.get_json(force=True, silent=True) or {}
    new_password = data.get("new_password") or ""
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    execute("UPDATE admins SET password_hash=%s WHERE id=%s",
            (generate_password_hash(new_password), session["admin_id"]))
    return jsonify({"message": "Admin password updated."})
