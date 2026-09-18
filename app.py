"""
app.py
------
Flask REST API for the Metabolic Risk Prediction Tool.

Endpoints:
    GET  /health              -> {"status": "ok"}
    POST /predict              -> single patient prediction
    POST /predict/batch        -> list of patients -> list of predictions
    GET  /model-info           -> model name + top feature importances

Run:
    pip install flask flask-cors --break-system-packages
    python3 app.py
    (serves on http://0.0.0.0:5000)

Example request:
    curl -X POST http://localhost:5000/predict \
      -H "Content-Type: application/json" \
      -d '{"age":45,"gender":"Female","bmi":31.2,"waist":96,"drug":"Valproate",
           "dose":1200,"duration":36,"sbp":138,"dbp":88,"fbg":118,"tg":210,
           "hdl":38,"ldl":130,"ham_d":14,"cssrs":0}'
"""

import os

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from predict import ALL_FEATURES, predict_one

MODEL_PATH = os.environ.get("MODEL_PATH", "metabolic_risk_model.pkl")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # allow calls from a browser-based front-end on a different origin, if any

_bundle = None


def get_bundle():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


REQUIRED_FIELDS = ALL_FEATURES  # age, gender, bmi, waist, drug, dose, duration, sbp, dbp, fbg, tg, hdl, ldl, ham_d, cssrs
OPTIONAL_FIELDS = {"ham_d", "cssrs"}  # per spec, these two may be omitted


def validate_patient(payload):
    missing = [f for f in REQUIRED_FIELDS if f not in payload and f not in OPTIONAL_FIELDS]
    if missing:
        return f"Missing required fields: {missing}"
    if payload.get("gender") not in (None, "Male", "Female"):
        return "gender must be 'Male' or 'Female'"
    if payload.get("drug") not in (None, "Lithium", "Valproate", "Carbamazepine", "Others"):
        return "drug must be one of Lithium/Valproate/Carbamazepine/Others"
    return None


@app.route("/", methods=["GET"])
def home():
    # Serves the web UI (static/index.html) at the root URL, so one deployed
    # link gives the client both the page and the API behind it.
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/model-info", methods=["GET"])
def model_info():
    bundle = get_bundle()
    return jsonify({
        "model_name": bundle["model_name"],
        "risk_categories": bundle["risk_order"],
        "top_feature_importances": bundle["feature_importance"][:10],
    })


@app.route("/predict", methods=["POST"])
def predict_single():
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    err = validate_patient(payload)
    if err:
        return jsonify({"error": err}), 400

    try:
        bundle = get_bundle()
        result = predict_one(bundle, payload)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, list):
        return jsonify({"error": "Request body must be a JSON array of patient objects"}), 400

    bundle = get_bundle()
    results = []
    for i, patient in enumerate(payload):
        err = validate_patient(patient)
        if err:
            results.append({"index": i, "error": err})
            continue
        try:
            results.append({"index": i, **predict_one(bundle, patient)})
        except Exception as e:
            results.append({"index": i, "error": str(e)})
    return jsonify(results)


if __name__ == "__main__":
    # Load once at startup so the first request isn't slow
    get_bundle()
    port = int(os.environ.get("PORT", 5000))  # hosting platforms set PORT via env var
    app.run(host="0.0.0.0", port=port, debug=False)
