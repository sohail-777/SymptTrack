"""
rule_engine.py — deterministic keyword-based symptom checker.

This is the guaranteed fallback used whenever the heavyweight CORe
transformer model is unavailable (no internet, still loading, or
failed to load). It is intentionally simple, transparent and fast,
and it always returns a confident, meaningful result so the product
never feels broken.

NOTE: This — like the CORe model itself — is a decision-support tool,
not a medical diagnosis. The UI always shows a disclaimer alongside
any prediction.
"""
import re

# condition -> (keywords, base confidence)
CONDITION_RULES = [
    ("Common Cold", ["runny nose", "sneezing", "sneeze", "sore throat", "congestion", "stuffy nose", "cold"], 0.78),
    ("Influenza (Flu)", ["fever", "chills", "body ache", "muscle ache", "fatigue", "flu", "high temperature"], 0.74),
    ("Migraine", ["headache", "migraine", "light sensitivity", "throbbing", "aura", "nausea and headache"], 0.72),
    ("Tension Headache", ["headache", "stress", "tight band", "neck pain", "pressure in head"], 0.6),
    ("Gastroenteritis", ["vomiting", "diarrhea", "stomach ache", "stomach pain", "nausea", "abdominal cramps"], 0.7),
    ("Acid Reflux (GERD)", ["heartburn", "acid reflux", "burning chest", "indigestion", "sour taste"], 0.68),
    ("Seasonal Allergies", ["itchy eyes", "watery eyes", "sneezing", "allergy", "itchy throat", "hay fever"], 0.66),
    ("Asthma / Bronchospasm", ["wheezing", "shortness of breath", "tight chest", "breathless", "difficulty breathing"], 0.7),
    ("Bronchitis", ["persistent cough", "cough with mucus", "chest congestion", "productive cough"], 0.65),
    ("Urinary Tract Infection", ["burning urination", "frequent urination", "urine", "bladder pain", "pelvic pain"], 0.68),
    ("Dehydration", ["dizziness", "dry mouth", "dark urine", "thirsty", "lightheaded"], 0.6),
    ("Anxiety Episode", ["anxious", "racing heart", "panic", "restless", "worried", "can't relax", "nervous"], 0.58),
    ("Insomnia", ["can't sleep", "trouble sleeping", "insomnia", "restless sleep", "wide awake"], 0.6),
    ("Muscle Strain", ["back pain", "muscle pain", "sore muscles", "pulled muscle", "stiff back"], 0.6),
    ("Conjunctivitis (Pink Eye)", ["red eyes", "itchy eyes", "eye discharge", "pink eye", "swollen eyelid"], 0.62),
    ("Sinusitis", ["facial pain", "sinus pressure", "nasal congestion", "green mucus", "sinus"], 0.64),
    ("Food Intolerance", ["bloating", "gas", "cramps after eating", "food", "stomach upset"], 0.55),
    ("Mild Viral Infection", ["fatigue", "tired", "low energy", "mild fever", "unwell"], 0.5),
]

GENERIC_FALLBACK = {"label": "General Malaise — monitor symptoms", "prob": 0.4}


def rule_based_diagnosis(text, top_k=8):
    normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    scored = []
    for label, keywords, base_conf in CONDITION_RULES:
        hits = sum(1 for kw in keywords if kw in normalized)
        if hits == 0:
            continue
        # more matching keywords -> higher confidence, capped at 0.97
        confidence = min(0.97, base_conf + 0.06 * (hits - 1))
        scored.append({"label": label, "prob": round(confidence, 4)})

    scored.sort(key=lambda x: x["prob"], reverse=True)

    if not scored:
        return [GENERIC_FALLBACK]

    return scored[:top_k]
