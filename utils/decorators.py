from functools import wraps
from flask import session, jsonify, redirect, url_for


def patient_login_required(f):
    """Protects JSON API routes — returns 401 JSON if not logged in."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("patient_id"):
            return jsonify({"error": "Please log in to continue."}), 401
        return f(*args, **kwargs)
    return wrapper


def patient_page_required(f):
    """Protects HTML page routes — redirects to login if not logged in."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("patient_id"):
            return redirect(url_for("pages.login_page"))
        return f(*args, **kwargs)
    return wrapper


def admin_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return jsonify({"error": "Admin authentication required."}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_page_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("pages.admin_login_page"))
        return f(*args, **kwargs)
    return wrapper
