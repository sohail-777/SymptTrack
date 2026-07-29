from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import patient_page_required, admin_page_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def login_page():
    if session.get("patient_id"):
        return redirect(url_for("pages.home_page"))
    return render_template("login.html")


@pages_bp.get("/home")
@patient_page_required
def home_page():
    return render_template("home.html")


@pages_bp.get("/symptoms")
@patient_page_required
def symptoms_page():
    return render_template("symptoms.html")


@pages_bp.get("/records")
@patient_page_required
def records_page():
    return render_template("records.html")


@pages_bp.get("/analytics")
@patient_page_required
def analytics_page():
    return render_template("analytics.html")


@pages_bp.get("/about")
def about_page():
    return render_template("about.html")


@pages_bp.get("/admin")
def admin_login_page():
    if session.get("admin_id"):
        return redirect(url_for("pages.admin_dashboard_page"))
    return render_template("admin/login.html")


@pages_bp.get("/admin/dashboard")
@admin_page_required
def admin_dashboard_page():
    return render_template("admin/dashboard.html")
