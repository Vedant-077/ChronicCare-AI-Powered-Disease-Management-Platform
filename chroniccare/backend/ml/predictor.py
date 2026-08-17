# predictor.py
# Loads the model file that train_model.py saved, ONCE, when the API starts up
# (loading a model from disk is slow-ish -- we don't want to do it on every
# single request). Then predict_risk() is just a fast, in-memory lookup.

import os
import joblib
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "risk_model.pkl")

_model = None  # cached in memory after first load


def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(
                "risk_model.pkl not found. Run `python ml/train_model.py` once "
                "from inside the backend/ folder to create it."
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_risk(glucose: float, bp: float, bmi: float, age: float):
    """
    Takes 4 raw numbers and returns (risk_level, confidence_percent).
    risk_level is one of "Low", "Medium", "High".
    confidence_percent is how sure the model is about that specific label (0-100).
    """
    model = load_model()

    # scikit-learn expects a 2D table even for a single patient. We use the same
    # column names train_model.py used, which also silences a sklearn warning
    # about missing feature names.
    features = pd.DataFrame(
        [[glucose, bp, bmi, age]], columns=["glucose", "bp", "bmi", "age"]
    )

    predicted_label = model.predict(features)[0]

    # predict_proba gives a probability for EACH possible class, e.g. [0.1, 0.7, 0.2]
    # for [High, Low, Medium] -- we grab the one matching our predicted label.
    probabilities = model.predict_proba(features)[0]
    class_names = list(model.classes_)
    confidence = probabilities[class_names.index(predicted_label)] * 100

    return predicted_label, round(float(confidence), 1)
