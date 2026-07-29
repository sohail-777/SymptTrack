"""
diagnosis_model.py — ML diagnosis engine.

Primary engine : bvanaken/CORe-clinical-diagnosis-prediction (HuggingFace)
Fallback engine: local keyword/rule based classifier (utils.symptom_rules)

Design goals
------------
1. The Flask app must NEVER crash or hang because of the ML layer.
2. The (large) transformer model is loaded lazily in a background
   thread right after the server starts, so the first request isn't
   stuck waiting for a multi-hundred-MB download.
3. While the transformer model is still loading (or if it fails to
   load at all — no internet, no torch, etc.) every request is
   instantly served by the rule engine, so "diagnosis" always works.
"""
import threading
import time
from config import Config
from ml.rule_engine import rule_based_diagnosis

_state = {
    "status": "not_started",   # not_started | loading | ready | unavailable
    "tokenizer": None,
    "model": None,
    "error": None,
}
_lock = threading.Lock()


def start_background_load():
    """Kick off model loading in a daemon thread. Safe to call once at boot."""
    if not Config.USE_CORE_MODEL:
        _state["status"] = "unavailable"
        _state["error"] = "USE_CORE_MODEL disabled in .env — using rule engine."
        print("[ml] CORe model disabled via config. Using rule-based engine only.")
        return

    thread = threading.Thread(target=_load_model, daemon=True)
    thread.start()


def _load_model():
    with _lock:
        if _state["status"] in ("loading", "ready"):
            return
        _state["status"] = "loading"

    try:
        print(f"[ml] Loading {Config.CORE_MODEL_NAME} in background (this can take a while)...")
        t0 = time.time()
        import torch  # noqa: F401  (imported lazily so app boots instantly without torch too)
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        tokenizer = AutoTokenizer.from_pretrained(Config.CORE_MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(Config.CORE_MODEL_NAME)
        model.eval()

        _state["tokenizer"] = tokenizer
        _state["model"] = model
        _state["status"] = "ready"
        print(f"[ml] CORe model loaded successfully in {time.time() - t0:.1f}s.")
    except Exception as e:  # noqa: BLE001 — deliberately broad: ML load must never crash the app
        _state["status"] = "unavailable"
        _state["error"] = str(e)
        print(f"[ml] Could not load CORe model ({e}). Falling back to rule-based engine.")


def get_model_status():
    return {"status": _state["status"], "error": _state["error"], "engine": Config.CORE_MODEL_NAME}


def predict_diagnosis(text, threshold=0.3, top_k=8):
    """
    Returns (diagnoses, source) where diagnoses is a list of
    {"label": str, "prob": float} sorted by probability desc,
    and source is 'core_model' or 'rule_engine'.
    """
    text = (text or "").strip()
    if not text:
        return [], "rule_engine"

    if _state["status"] == "ready":
        try:
            import torch
            tokenizer = _state["tokenizer"]
            model = _state["model"]
            tokenized = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                out = model(**tokenized)
            probs = torch.sigmoid(out.logits)[0].cpu().tolist()

            preds = []
            for idx, p in enumerate(probs):
                if p >= threshold:
                    label = model.config.id2label.get(idx, str(idx))
                    preds.append({"label": _humanize_label(label), "prob": round(float(p), 4)})
            preds = sorted(preds, key=lambda x: x["prob"], reverse=True)[:top_k]

            if preds:
                return preds, "core_model"
            # model ran but nothing crossed the threshold -> fall through to rule engine
        except Exception as e:  # noqa: BLE001
            print(f"[ml] CORe inference failed ({e}); using rule engine for this request.")

    # Loading / unavailable / low-confidence -> guaranteed rule-based result
    return rule_based_diagnosis(text, top_k=top_k), "rule_engine"


def _humanize_label(label):
    return label.replace("_", " ").replace("-", " ").strip().capitalize()
