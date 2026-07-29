import calendar
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, session, send_file
from db import query, execute
from utils.decorators import patient_login_required
from utils.helpers import log_activity, json_dumps, json_loads, severity_label
from utils.pdf_report import build_monthly_report_pdf
from ml.diagnosis_model import predict_diagnosis, get_model_status

patient_bp = Blueprint("patient", __name__, url_prefix="/api/patient")


@patient_bp.get("/health-tips")
@patient_login_required
def health_tips():
    tips = query("SELECT icon, title, content, category FROM health_tips WHERE is_active = 1 ORDER BY RAND() LIMIT 6")
    return jsonify({"tips": tips})


@patient_bp.get("/dashboard-summary")
@patient_login_required
def dashboard_summary():
    pid = session["patient_id"]
    patient = query("SELECT full_name, avatar_emoji FROM patients WHERE id=%s", (pid,), fetch="one")

    dates = query(
        "SELECT log_date FROM symptom_logs WHERE patient_id=%s ORDER BY log_date DESC", (pid,))
    log_dates = {row["log_date"] for row in dates}

    # streak: consecutive days ending today or yesterday
    streak = 0
    cursor = date.today()
    if cursor not in log_dates:
        cursor -= timedelta(days=1)
    while cursor in log_dates:
        streak += 1
        cursor -= timedelta(days=1)

    last_log = query(
        "SELECT log_date, severity FROM symptom_logs WHERE patient_id=%s ORDER BY log_date DESC LIMIT 1",
        (pid,), fetch="one")

    recent_30 = query(
        "SELECT severity FROM symptom_logs WHERE patient_id=%s AND log_date >= %s",
        (pid, date.today() - timedelta(days=30)))
    avg_severity = round(sum(r["severity"] for r in recent_30) / len(recent_30), 1) if recent_30 else None

    return jsonify({
        "patient_name": patient["full_name"] if patient else "Friend",
        "avatar_emoji": (patient or {}).get("avatar_emoji") or "🙂",
        "streak_days": streak,
        "total_logs": len(log_dates),
        "last_log_date": last_log["log_date"].isoformat() if last_log else None,
        "avg_severity_30d": avg_severity,
        "logged_today": date.today() in log_dates,
    })


# ---------------------------------------------------------------
# Symptom logging (calendar-driven)
# ---------------------------------------------------------------
@patient_bp.get("/calendar/<int:year>/<int:month>")
@patient_login_required
def calendar_month(year, month):
    pid = session["patient_id"]
    start = date(year, month, 1)
    end_day = calendar.monthrange(year, month)[1]
    end = date(year, month, end_day)

    rows = query(
        "SELECT log_date, severity FROM symptom_logs WHERE patient_id=%s AND log_date BETWEEN %s AND %s",
        (pid, start, end))
    days = {r["log_date"].isoformat(): r["severity"] for r in rows}
    return jsonify({"year": year, "month": month, "days": days})


@patient_bp.get("/symptoms/<log_date>")
@patient_login_required
def get_symptom_log(log_date):
    pid = session["patient_id"]
    log = query(
        "SELECT * FROM symptom_logs WHERE patient_id=%s AND log_date=%s", (pid, log_date), fetch="one")
    if not log:
        return jsonify({"log": None})

    diagnoses = query("SELECT label, probability, source FROM diagnoses WHERE log_id=%s ORDER BY probability DESC", (log["id"],))
    log["symptoms_tags"] = json_loads(log.get("symptoms_tags"))
    log["log_date"] = log["log_date"].isoformat()
    log["created_at"] = log["created_at"].isoformat()
    return jsonify({"log": log, "diagnoses": diagnoses})


@patient_bp.post("/symptoms")
@patient_login_required
def submit_symptoms():
    pid = session["patient_id"]
    data = request.get_json(force=True, silent=True) or {}

    log_date = data.get("date") or date.today().isoformat()
    text = (data.get("symptoms_text") or "").strip()
    tags = data.get("symptoms_tags") or []
    severity = int(data.get("severity") or 3)
    mood = data.get("mood")
    notes = (data.get("notes") or "").strip() or None

    combined_text = text
    if tags:
        combined_text = (", ".join(tags) + (". " + text if text else "")).strip()

    if not combined_text:
        return jsonify({"error": "Please describe your symptoms or select at least one symptom tag."}), 400

    severity = max(1, min(5, severity))

    existing = query(
        "SELECT id FROM symptom_logs WHERE patient_id=%s AND log_date=%s", (pid, log_date), fetch="one")

    if existing:
        log_id = existing["id"]
        execute(
            """UPDATE symptom_logs SET symptoms_text=%s, symptoms_tags=%s, severity=%s, mood=%s, notes=%s
               WHERE id=%s""",
            (text, json_dumps(tags), severity, mood, notes, log_id))
        execute("DELETE FROM diagnoses WHERE log_id=%s", (log_id,))
    else:
        log_id, _ = execute(
            """INSERT INTO symptom_logs (patient_id, log_date, symptoms_text, symptoms_tags, severity, mood, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (pid, log_date, text, json_dumps(tags), severity, mood, notes))

    diagnoses, source = predict_diagnosis(combined_text)

    for d in diagnoses:
        execute(
            "INSERT INTO diagnoses (log_id, label, probability, source) VALUES (%s,%s,%s,%s)",
            (log_id, d["label"], d["prob"], source))

    top_summary = diagnoses[0]["label"] if diagnoses else None
    execute("UPDATE symptom_logs SET ai_summary=%s WHERE id=%s", (top_summary, log_id))

    log_activity("patient", pid, "symptom_log", f"Logged symptoms for {log_date}")

    return jsonify({
        "message": "Symptoms logged and analyzed! 🩺",
        "log_id": log_id,
        "diagnoses": diagnoses,
        "source": source,
        "model_status": get_model_status()["status"],
    }), 201


# ---------------------------------------------------------------
# Records
# ---------------------------------------------------------------
@patient_bp.get("/records")
@patient_login_required
def records():
    pid = session["patient_id"]
    page = max(1, int(request.args.get("page", 1)))
    per_page = 10
    offset = (page - 1) * per_page

    total = query("SELECT COUNT(*) AS c FROM symptom_logs WHERE patient_id=%s", (pid,), fetch="one")["c"]
    logs = query(
        "SELECT * FROM symptom_logs WHERE patient_id=%s ORDER BY log_date DESC LIMIT %s OFFSET %s",
        (pid, per_page, offset))

    for log in logs:
        log["log_date"] = log["log_date"].isoformat()
        log["created_at"] = log["created_at"].isoformat()
        log["symptoms_tags"] = json_loads(log.get("symptoms_tags"))
        log["severity_label"] = severity_label(log["severity"])
        diags = query("SELECT label, probability FROM diagnoses WHERE log_id=%s ORDER BY probability DESC LIMIT 3", (log["id"],))
        log["diagnoses"] = diags

    available_months = query(
        "SELECT DISTINCT DATE_FORMAT(log_date, '%Y-%m') AS ym FROM symptom_logs WHERE patient_id=%s ORDER BY ym DESC",
        (pid,))

    return jsonify({
        "logs": logs,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "available_months": [m["ym"] for m in available_months],
    })


@patient_bp.get("/records/download/<int:year>/<int:month>")
@patient_login_required
def download_report(year, month):
    pid = session["patient_id"]
    patient = query("SELECT * FROM patients WHERE id=%s", (pid,), fetch="one")

    start = date(year, month, 1)
    end_day = calendar.monthrange(year, month)[1]
    end = date(year, month, end_day)

    logs = query(
        "SELECT * FROM symptom_logs WHERE patient_id=%s AND log_date BETWEEN %s AND %s ORDER BY log_date",
        (pid, start, end))

    diagnoses_by_log = {}
    for log in logs:
        diags = query("SELECT label, probability FROM diagnoses WHERE log_id=%s ORDER BY probability DESC", (log["id"],))
        diagnoses_by_log[log["id"]] = [{"label": d["label"], "probability": float(d["probability"])} for d in diags]

    pdf_buffer = build_monthly_report_pdf(patient, year, month, logs, diagnoses_by_log)
    filename = f"SymptTrack_Report_{patient['full_name'].replace(' ', '_')}_{year}-{month:02d}.pdf"

    log_activity("patient", pid, "download_report", f"Downloaded report for {year}-{month:02d}")

    return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


# ---------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------
@patient_bp.get("/analytics")
@patient_login_required
def analytics():
    pid = session["patient_id"]
    since = date.today() - timedelta(days=90)

    rows = query(
        "SELECT log_date, severity FROM symptom_logs WHERE patient_id=%s AND log_date >= %s ORDER BY log_date",
        (pid, since))
    trend = [{"date": r["log_date"].isoformat(), "severity": r["severity"]} for r in rows]

    top_diagnoses = query(
        """SELECT d.label, COUNT(*) AS occurrences, AVG(d.probability) AS avg_prob
           FROM diagnoses d JOIN symptom_logs s ON d.log_id = s.id
           WHERE s.patient_id=%s AND s.log_date >= %s
           GROUP BY d.label ORDER BY occurrences DESC LIMIT 6""",
        (pid, since))
    for t in top_diagnoses:
        t["avg_prob"] = round(float(t["avg_prob"]), 3)

    # trend direction: compare avg severity of last 15d vs previous 15d
    last15 = [r["severity"] for r in rows if r["log_date"] >= date.today() - timedelta(days=15)]
    prev15 = [r["severity"] for r in rows if date.today() - timedelta(days=30) <= r["log_date"] < date.today() - timedelta(days=15)]
    avg_last15 = sum(last15) / len(last15) if last15 else None
    avg_prev15 = sum(prev15) / len(prev15) if prev15 else None

    if avg_last15 is None or avg_prev15 is None:
        direction = "not_enough_data"
    elif avg_last15 < avg_prev15 - 0.15:
        direction = "improving"
    elif avg_last15 > avg_prev15 + 0.15:
        direction = "declining"
    else:
        direction = "stable"

    mood_counts = query(
        "SELECT mood, COUNT(*) AS c FROM symptom_logs WHERE patient_id=%s AND mood IS NOT NULL AND log_date >= %s GROUP BY mood",
        (pid, since))

    return jsonify({
        "trend": trend,
        "top_diagnoses": top_diagnoses,
        "direction": direction,
        "avg_last_15d": round(avg_last15, 2) if avg_last15 else None,
        "avg_prev_15d": round(avg_prev15, 2) if avg_prev15 else None,
        "mood_breakdown": mood_counts,
    })


@patient_bp.put("/profile")
@patient_login_required
def update_profile():
    pid = session["patient_id"]
    data = request.get_json(force=True, silent=True) or {}
    fields = ["full_name", "phone", "dob", "gender", "blood_group", "height_cm", "weight_kg", "avatar_emoji"]
    updates, values = [], []
    for f in fields:
        if f in data:
            updates.append(f"{f} = %s")
            values.append(data[f] or None)
    if not updates:
        return jsonify({"error": "Nothing to update."}), 400
    values.append(pid)
    execute(f"UPDATE patients SET {', '.join(updates)} WHERE id = %s", tuple(values))
    log_activity("patient", pid, "profile_update", "Updated profile details")
    return jsonify({"message": "Profile updated successfully! ✅"})
