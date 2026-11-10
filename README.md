# 🏥 SymptTrack — Health Journal & ML Diagnosis Assistant

A full-stack patient health journal: log daily symptoms on a visual calendar,
get an instant AI-assisted diagnosis suggestion, track trends over time, and
download monthly PDF reports — with a complete admin control panel behind it.

**Stack:** HTML / CSS / vanilla JS (frontend) · Flask (backend) · MySQL (database)
· HuggingFace `CORe-clinical-diagnosis-prediction` transformer (ML), with a
guaranteed rule-based fallback engine.


## ✨ Features

**Patient side**
- 🔐 Email/password signup & login (with session auth)
- 🏠 Home dashboard — streak counter, quick stats, rotating health tips & daily habit checklist
- 🩺 Symptom calendar — tap any date to log symptoms via chips or free text, get an instant AI diagnosis suggestion
- 📋 Records — full history of logged symptoms + diagnoses, with **monthly PDF report download**
- 📊 Analytics — severity trend chart, most frequent suggested diagnoses, mood breakdown, and an "improving / stable / declining" indicator
- ℹ️ About page — explains the product, the pages, and the ML model used

**Admin side** (`/admin`, fixed credentials seeded via `.env`)
- 📊 Overview dashboard — patient counts, logs today/7-day, avg severity, live ML model status
- 👥 Patient management — search, view full patient detail + logs, activate/deactivate, delete
- 📋 Daily logs — every symptom log across all patients, filterable by date
- 💡 Health Tips CMS — add/hide/delete the tips shown on the patient home page
- ⚙️ Settings — site name/tagline, change admin password
- 🕒 Activity log — audit trail of logins, signups, and admin actions

**ML diagnosis engine**
- Primary: `bvanaken/CORe-clinical-diagnosis-prediction` (HuggingFace transformer), loaded lazily in a background thread so the server boots instantly.
- Fallback: a transparent keyword/rule-based engine (`ml/rule_engine.py`) that instantly and reliably classifies common symptom patterns (colds, flu, migraines, GI issues, allergies, etc.) whenever the transformer model is loading, unavailable, or errors out — **the diagnosis feature never breaks**, even with no internet access or GPU.

---

## 📁 Project structure

```
SymptTrack/
├── app.py                  # Flask entry point
├── config.py                # env-driven config
├── db.py                    # MySQL connection pool + query helpers
├── seed.py                  # one-time setup: seeds default admin account
├── requirements.txt
├── .env.example              # copy to .env and fill in
├── database/
│   └── schema.sql            # full MySQL schema + seed data
├── ml/
│   ├── diagnosis_model.py    # CORe model wrapper (lazy background load)
│   └── rule_engine.py        # guaranteed fallback diagnosis engine
├── routes/
│   ├── pages.py               # HTML page routes
│   ├── auth.py                 # patient + admin auth API
│   ├── patient.py              # patient API (symptoms, records, analytics...)
│   └── admin.py                 # admin API (patients, logs, CMS, settings...)
├── utils/
│   ├── decorators.py           # login-required guards
│   ├── helpers.py                # small shared helpers
│   ├── pdf_report.py             # monthly PDF report generator (reportlab)
│   └── json_provider.py           # safe JSON serialization for MySQL types
├── templates/                  # Jinja-rendered HTML pages
│   ├── login.html, home.html, symptoms.html, records.html, analytics.html, about.html
│   └── admin/ (login.html, dashboard.html)
└── static/
    ├── css/ (style.css, auth.css, dashboard.css, admin.css)
    └── js/  (common.js, auth.js, home.js, symptoms.js, records.js, analytics.js, admin.js)
```

---

## 🚀 Setup

### 1. Prerequisites
- Python 3.10+
- MySQL 8.0+ (or MariaDB 10.6+)

### 2. Clone & install dependencies
**Windows (PowerShell):**
```bash
cd SymptTrack
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd SymptTrack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note on `torch`/`transformers`:** these are large downloads. If you just
> want to try the app quickly, you can skip them and set `USE_CORE_MODEL=0`
> in `.env` — the app will run entirely on the fast, dependency-light rule
> engine described above with no loss of functionality.

### 3. Create the database
```bash
mysql -u root -p < database/schema.sql
```
This creates the `symptrack` database, all tables, and seeds default health tips.

> ⚠️ **Only run this once.** The script drops and recreates all tables so it
> can be re-run cleanly during development — running it again later will
> delete any patients/logs you've since created. (If you previously saw a
> `Table 'activity_log' already exists` warning, that was harmless — MySQL's
> `IF NOT EXISTS` simply skipped an already-created table — but the script
> now resets cleanly instead of warning.)

### 4. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set `DB_USER` / `DB_PASSWORD` to match your MySQL setup, and
optionally change `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD`.

### 5. Seed the admin account
```bash
python seed.py
```

### 6. Run the app
```bash
python app.py
```
Visit **http://localhost:5000** for the patient site and **http://localhost:5000/admin**
for the admin panel (login with the credentials from step 5).

---

## 📊 Charts

Analytics charts use [Chart.js](https://www.chartjs.org), bundled locally at
`static/js/vendor/chart.umd.js` (not loaded from a CDN) so the page works
fully offline and isn't affected by browser tracking-prevention features
that can block third-party script domains like `cdnjs.cloudflare.com`.

## 🔒 Security notes for production

- Change `SECRET_KEY` and the default admin password before deploying.
- Set `FLASK_DEBUG=0` in production.
- Serve behind HTTPS — cookies carry the session.
- The provided `.env` values are for local development only.

---

## ⚠️ Disclaimer

SymptTrack is a self-tracking and decision-support tool. It does **not**
provide a medical diagnosis and is not a substitute for professional medical
advice. Always consult a qualified healthcare provider.
