# train_model.py
# Run this ONCE (python ml/train_model.py) to create risk_model.pkl.
# The API loads that saved file at startup -- it does NOT retrain on every request.
#
# WHY A SYNTHETIC DATASET, NOT A DOWNLOADED ONE:
# The original Day 3 plan was "train on a public dataset" (e.g. the Pima Indians
# Diabetes dataset). This sandbox has no internet access to download it, so
# instead this script generates its own training data using the SAME clinical
# risk factors and threshold logic that real diabetes-risk datasets are built
# around (fasting glucose, BMI, blood pressure, and age -- standard ADA/AHA
# risk indicators), plus randomized noise so it isn't just a hardcoded if/else.
# This keeps the ML pipeline (train -> save -> load -> predict) 100% real and
# testable, while being honest that the training data itself is synthetic.
# Swapping in a real downloaded CSV later is a small change -- see the note
# at the bottom of this file.

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

N_SAMPLES = 2000


def generate_synthetic_patients(n=N_SAMPLES):
    """
    Creates n fake patients with 4 features:
      glucose   -- fasting blood glucose, mg/dL      (normal ~70-99)
      bp        -- systolic blood pressure, mmHg      (normal <120)
      bmi       -- body mass index                    (normal 18.5-24.9)
      age       -- years

    Each feature is drawn from a realistic-ish distribution, then we compute
    a "risk score" from known clinical thresholds and add random noise, so
    the model has to actually learn the pattern instead of memorizing a rule.
    """
    glucose = np.random.normal(110, 30, n).clip(70, 300)
    bp = np.random.normal(125, 18, n).clip(80, 200)
    bmi = np.random.normal(27, 6, n).clip(15, 55)
    age = np.random.normal(45, 15, n).clip(18, 90)

    # Points-based risk score using standard clinical cutoffs:
    # glucose >=126 = diabetic range, 100-125 = prediabetic range (ADA)
    # BMI >=30 = obese, 25-29.9 = overweight (WHO)
    # systolic BP >=130 = elevated/high (AHA)
    # age is a compounding risk factor for chronic disease
    score = (
        (glucose >= 126) * 3 + ((glucose >= 100) & (glucose < 126)) * 1.5
        + (bmi >= 30) * 2 + ((bmi >= 25) & (bmi < 30)) * 1
        + (bp >= 140) * 2 + ((bp >= 130) & (bp < 140)) * 1
        + (age >= 60) * 1.5 + ((age >= 45) & (age < 60)) * 0.75
    )

    # Add random noise so it's not a deterministic rule, then bucket into 3 classes
    score = score + np.random.normal(0, 0.8, n)
    risk_level = pd.cut(
        score,
        bins=[-np.inf, 2.5, 5.5, np.inf],
        labels=["Low", "Medium", "High"],
    )

    df = pd.DataFrame({
        "glucose": glucose.round(1),
        "bp": bp.round(1),
        "bmi": bmi.round(1),
        "age": age.round(0),
        "risk_level": risk_level.astype(str),
    })
    return df


def train_and_save():
    df = generate_synthetic_patients()

    X = df[["glucose", "bp", "bmi", "age"]]
    y = df["risk_level"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=6,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Validation accuracy on held-out test data: {acc:.2%}")
    print("Class distribution in training data:")
    print(y.value_counts())

    out_path = os.path.join(os.path.dirname(__file__), "risk_model.pkl")
    joblib.dump(model, out_path)
    print(f"Saved trained model to {out_path}")


if __name__ == "__main__":
    train_and_save()

# ---- Swapping in a real dataset later ----
# Replace generate_synthetic_patients() with something like:
#   df = pd.read_csv("diabetes.csv")  # e.g. the Pima Indians Diabetes dataset
#   X = df[["Glucose", "BloodPressure", "BMI", "Age"]]
#   y = df["Outcome"].map({0: "Low", 1: "High"})   # then re-bucket as needed
# Everything downstream (train/test split, model, save) stays the same.
