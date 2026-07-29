import json
from datetime import datetime, date


def log_activity(actor_type, actor_id, action, description=""):
    """Best-effort audit log write — never blocks or breaks the main request."""
    try:
        from db import execute
        execute(
            "INSERT INTO activity_log (actor_type, actor_id, action, description) VALUES (%s,%s,%s,%s)",
            (actor_type, actor_id, action, description),
        )
    except Exception as e:  # noqa: BLE001
        print(f"[activity_log] skipped (non-fatal): {e}")


def to_json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def json_dumps(value):
    return json.dumps(value or [])


def json_loads(value):
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


def severity_label(score):
    return {1: "Mild", 2: "Light", 3: "Moderate", 4: "Serious", 5: "Severe"}.get(int(score), "Moderate")


def calc_age(dob):
    if not dob:
        return None
    today = date.today()
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
