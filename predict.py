"""
predict.py
----------
Command-line prediction script for the metabolic risk model.

Usage (flags):
    python3 predict.py --model metabolic_risk_model.pkl \
        --age 45 --gender Female --bmi 31.2 --waist 96 \
        --drug Valproate --dose 1200 --duration 36 \
        --sbp 138 --dbp 88 --fbg 118 --tg 210 --hdl 38 --ldl 130 \
        --ham_d 14 --cssrs 0

Usage (interactive):
    python3 predict.py --model metabolic_risk_model.pkl --interactive

Usage (batch, from CSV of patients with the same feature columns):
    python3 predict.py --model metabolic_risk_model.pkl --batch new_patients.csv --out predictions.csv
"""

import argparse
import json

import joblib
import numpy as np
import pandas as pd

NUMERIC_FEATURES = [
    "age", "bmi", "waist", "dose", "duration",
    "sbp", "dbp", "fbg", "tg", "hdl", "ldl", "ham_d", "cssrs",
]
CATEGORICAL_FEATURES = ["gender", "drug"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def load_bundle(model_path):
    return joblib.load(model_path)


def predict_one(bundle, patient_dict):
    pipe = bundle["pipeline"]
    risk_order = bundle["risk_order"]

    row = pd.DataFrame([{f: patient_dict.get(f, np.nan) for f in ALL_FEATURES}])
    proba = pipe.predict_proba(row)[0]
    classes = list(pipe.named_steps["clf"].classes_) if hasattr(pipe.named_steps["clf"], "classes_") else risk_order
    pred_label = pipe.predict(row)[0]

    proba_map = dict(zip(classes, proba))
    risk_score = round(float(proba_map.get(pred_label, max(proba))) * 100, 1)

    # Key contributing factors: use global feature importance, but only report
    # ones for features where this patient's value looks clinically "elevated"
    # relative to common reference thresholds — a simple, transparent heuristic
    # (not a per-patient SHAP explanation).
    flags = []
    if patient_dict.get("bmi", 0) and patient_dict["bmi"] >= 30:
        flags.append("High BMI")
    if patient_dict.get("waist") is not None:
        thresh = 94 if patient_dict.get("gender") == "Male" else 80
        if patient_dict["waist"] >= thresh:
            flags.append("Elevated waist circumference")
    if patient_dict.get("fbg", 0) and patient_dict["fbg"] >= 100:
        flags.append("Elevated fasting glucose")
    if patient_dict.get("tg", 0) and patient_dict["tg"] >= 150:
        flags.append("High triglycerides")
    if patient_dict.get("hdl") is not None and patient_dict["hdl"] < 40:
        flags.append("Low HDL")
    if patient_dict.get("sbp", 0) and patient_dict["sbp"] >= 130:
        flags.append("Elevated systolic BP")
    if patient_dict.get("duration", 0) and patient_dict["duration"] >= 24:
        flags.append("Long duration of therapy")
    if patient_dict.get("drug") == "Valproate":
        flags.append("Drug with higher metabolic burden (Valproate)")

    # Fall back to top global feature importances if no simple flags triggered
    if not flags:
        top_features = [f["feature"] for f in bundle["feature_importance"][:3]]
        flags = [f"(model-level top factor) {f}" for f in top_features]

    return {
        "risk_category": str(pred_label),
        "risk_score": risk_score,
        "class_probabilities": {k: round(float(v) * 100, 1) for k, v in proba_map.items()},
        "key_factors": flags[:5],
    }


def parse_args():
    p = argparse.ArgumentParser(description="Predict metabolic risk for a patient on a mood stabilizer")
    p.add_argument("--model", default="metabolic_risk_model.pkl")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--batch", help="CSV of patients to score in bulk")
    p.add_argument("--out", help="Output CSV path when using --batch")

    for f in NUMERIC_FEATURES:
        p.add_argument(f"--{f}", type=float)
    p.add_argument("--gender", choices=["Male", "Female"])
    p.add_argument("--drug", choices=["Lithium", "Valproate", "Carbamazepine", "Others"])
    return p.parse_args()


def interactive_input():
    print("Enter patient details (press Enter to leave a value missing):\n")
    data = {}
    prompts = {
        "age": "Age (years)", "gender": "Gender (Male/Female)", "bmi": "BMI",
        "waist": "Waist circumference (cm)", "drug": "Mood stabilizer (Lithium/Valproate/Carbamazepine/Others)",
        "dose": "Dose (mg/day)", "duration": "Duration of therapy (months)",
        "sbp": "Systolic BP (mmHg)", "dbp": "Diastolic BP (mmHg)",
        "fbg": "Fasting blood glucose (mg/dL)", "tg": "Triglycerides (mg/dL)",
        "hdl": "HDL (mg/dL)", "ldl": "LDL (mg/dL)",
        "ham_d": "HAM-D score (optional)", "cssrs": "C-SSRS score (optional)",
    }
    for key, label in prompts.items():
        val = input(f"{label}: ").strip()
        if val == "":
            data[key] = np.nan
        elif key in ("gender", "drug"):
            data[key] = val
        else:
            data[key] = float(val)
    return data


def main():
    args = parse_args()
    bundle = load_bundle(args.model)

    if args.batch:
        df = pd.read_csv(args.batch)
        pipe = bundle["pipeline"]
        preds = pipe.predict(df[ALL_FEATURES])
        proba = pipe.predict_proba(df[ALL_FEATURES])
        classes = pipe.named_steps["clf"].classes_
        df_out = df.copy()
        df_out["risk_category"] = preds
        for i, c in enumerate(classes):
            df_out[f"prob_{c}"] = np.round(proba[:, i] * 100, 1)
        out_path = args.out or "predictions.csv"
        df_out.to_csv(out_path, index=False)
        print(f"Wrote {len(df_out)} predictions to {out_path}")
        return

    if args.interactive:
        patient = interactive_input()
    else:
        patient = {f: getattr(args, f) for f in ALL_FEATURES}
        if all(v is None for v in patient.values()):
            print("No patient data given. Use flags, --interactive, or --batch. Run with -h for help.")
            return

    result = predict_one(bundle, patient)
    print("\n--- Metabolic Risk Prediction ---")
    print(f"Risk Category   : {result['risk_category']}")
    print(f"Risk Score       : {result['risk_score']}/100 (confidence in predicted class)")
    print(f"Class Probabilities: {json.dumps(result['class_probabilities'])}")
    print(f"Key Factors      : {', '.join(result['key_factors'])}")


if __name__ == "__main__":
    main()
