-- ============================================================
--  SymptTrack — Health Journal & ML Diagnosis Assistant
--  MySQL Database Schema
-- ============================================================

-- IMPORTANT: forces this session to talk utf8mb4 regardless of the
-- connecting client's default charset (many fresh MySQL installs
-- default the client/connection charset to latin1, which silently
-- corrupts the emoji values seeded below).
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS symptrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE symptrack;

-- ------------------------------------------------------------
-- Make this script safely re-runnable: if you run schema.sql
-- again (e.g. to reset your local data), drop any existing
-- tables first instead of leaving you with a "table already
-- exists" warning and stale structure. Order matters because of
-- foreign keys, so we also temporarily disable FK checks.
-- ------------------------------------------------------------
-- ⚠️  WARNING: this script DROPS and recreates all SymptTrack tables so it
-- can be re-run cleanly. Only run it once for initial setup — running it
-- again will DELETE all patients, logs and diagnoses created since.

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS diagnoses;
DROP TABLE IF EXISTS symptom_logs;
DROP TABLE IF EXISTS activity_log;
DROP TABLE IF EXISTS health_tips;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS patients;
SET FOREIGN_KEY_CHECKS = 1;

-- ------------------------------------------------------------
-- Patients (application users)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(120)  NOT NULL,
    email           VARCHAR(160)  NOT NULL UNIQUE,
    phone           VARCHAR(20)   DEFAULT NULL,
    password_hash   VARCHAR(255)  NOT NULL,
    dob             DATE          DEFAULT NULL,
    gender          ENUM('female','male','other','prefer_not_to_say') DEFAULT 'prefer_not_to_say',
    blood_group     VARCHAR(5)    DEFAULT NULL,
    height_cm       DECIMAL(5,1)  DEFAULT NULL,
    weight_kg       DECIMAL(5,1)  DEFAULT NULL,
    avatar_emoji    VARCHAR(10)   DEFAULT '🙂',
    is_active       TINYINT(1)    NOT NULL DEFAULT 1,
    streak_count    INT           NOT NULL DEFAULT 0,
    last_login_at   DATETIME      DEFAULT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Admins
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(80)   NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    full_name       VARCHAR(120)  DEFAULT 'System Administrator',
    role            ENUM('super_admin','staff') NOT NULL DEFAULT 'super_admin',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Default admin  ->  username: admin   password: Admin@123
-- (password_hash below is a werkzeug pbkdf2:sha256 hash generated at setup time by seed script)

-- ------------------------------------------------------------
-- Daily symptom logs (one calendar entry per patient per day)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS symptom_logs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    patient_id      INT NOT NULL,
    log_date        DATE NOT NULL,
    symptoms_text   TEXT          DEFAULT NULL,
    symptoms_tags   JSON          DEFAULT NULL,   -- quick-select chips e.g. ["fever","cough"]
    severity        TINYINT       NOT NULL DEFAULT 3,  -- 1 (mild) - 5 (severe)
    mood            VARCHAR(20)   DEFAULT NULL,   -- e.g. good / okay / bad
    notes           TEXT          DEFAULT NULL,
    ai_summary      VARCHAR(255)  DEFAULT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    UNIQUE KEY uq_patient_date (patient_id, log_date)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- ML model diagnosis predictions attached to a log
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diagnoses (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    log_id          INT NOT NULL,
    label           VARCHAR(255) NOT NULL,
    probability     DECIMAL(5,4) NOT NULL,
    source          ENUM('core_model','rule_engine') NOT NULL DEFAULT 'rule_engine',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_diag_log FOREIGN KEY (log_id) REFERENCES symptom_logs(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Health tips / daily habits (CMS-editable by admin)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS health_tips (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    icon            VARCHAR(10)   NOT NULL DEFAULT '💡',
    title           VARCHAR(150)  NOT NULL,
    content         VARCHAR(500)  NOT NULL,
    category        VARCHAR(60)   DEFAULT 'general',
    is_active       TINYINT(1)    NOT NULL DEFAULT 1,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Site settings (CMS style, key/value)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    setting_key     VARCHAR(80)  PRIMARY KEY,
    setting_value   TEXT
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Admin activity / audit log
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    actor_type      ENUM('admin','patient','system') NOT NULL,
    actor_id        INT DEFAULT NULL,
    action          VARCHAR(120) NOT NULL,
    description     VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Seed data
-- ------------------------------------------------------------
INSERT INTO settings (setting_key, setting_value) VALUES
    ('site_name', 'SymptTrack'),
    ('tagline', 'Your Friendly Pocket Health Journal'),
    ('maintenance_mode', '0'),
    ('model_status', 'auto')
ON DUPLICATE KEY UPDATE setting_key = setting_key;

INSERT INTO health_tips (icon, title, content, category) VALUES
('💧', 'Stay Hydrated', 'Aim for 8 glasses of water a day — your cells, joints and brain all run better when hydrated.', 'nutrition'),
('🚶', 'Move Every Hour', 'Short 5-minute walks every hour improve circulation and reduce stiffness from long sitting.', 'fitness'),
('😴', 'Protect Your Sleep', 'Adults need 7-9 hours of sleep. Keep a consistent bedtime to support immune health.', 'sleep'),
('🥦', 'Eat the Rainbow', 'Colorful fruits and vegetables provide a wide range of vitamins, minerals and antioxidants.', 'nutrition'),
('🧘', 'Breathe & Reset', '5 minutes of deep breathing can lower stress hormones and steady your heart rate.', 'mental-health'),
('🧼', 'Wash Hands Often', 'Regular handwashing is still one of the most effective ways to avoid common infections.', 'hygiene'),
('☀️', 'Get Some Sunlight', '10-15 minutes of morning sunlight helps regulate your body clock and vitamin D levels.', 'wellness'),
('📵', 'Screen-Free Wind Down', 'Avoid screens 30 minutes before bed to help your mind and eyes relax before sleep.', 'sleep')
ON DUPLICATE KEY UPDATE title = VALUES(title);
