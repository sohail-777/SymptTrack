"""
seed.py — one-time setup script.

Run this AFTER creating the MySQL schema (database/schema.sql) and
BEFORE starting the Flask app for the first time:

    python seed.py

It will:
  1. Verify the database connection works.
  2. Create the default admin account (if it doesn't already exist)
     using the credentials from .env (DEFAULT_ADMIN_USERNAME / PASSWORD).
"""
from werkzeug.security import generate_password_hash
from config import Config
from db import query, execute, init_pool

def main():
    init_pool()
    existing = query(
        "SELECT id FROM admins WHERE username = %s",
        (Config.DEFAULT_ADMIN_USERNAME,),
        fetch="one",
    )
    if existing:
        print(f"[seed] Admin '{Config.DEFAULT_ADMIN_USERNAME}' already exists — skipping.")
    else:
        pw_hash = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
        execute(
            "INSERT INTO admins (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
            (Config.DEFAULT_ADMIN_USERNAME, pw_hash, "System Administrator", "super_admin"),
        )
        print(f"[seed] Created default admin account:")
        print(f"        username: {Config.DEFAULT_ADMIN_USERNAME}")
        print(f"        password: {Config.DEFAULT_ADMIN_PASSWORD}")
        print("        (change this after first login!)")

    print("[seed] Done. You can now run: python app.py")


if __name__ == "__main__":
    main()
