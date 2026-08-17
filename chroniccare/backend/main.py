# main.py
# This is the entry point. It defines every URL ("endpoint") our app responds to.
# Run it with:  uvicorn main:app --reload

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import engine, get_db
from auth import hash_password, verify_password, create_access_token, get_current_user
from scheduler import start_scheduler
from ml.predictor import predict_risk

# This line creates all tables (users, diagnosis_history) in the database
# file the first time the app runs. If they already exist, it does nothing.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ChronicCare API")

# CORS lets our React frontend (running on a different port) call this API.
# In production you'd restrict allow_origins to your real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "ChronicCare API is running"}


@app.on_event("startup")
def on_startup():
    # Kicks off the medicine-reminder background job when the server starts.
    start_scheduler()


# ---------------- AUTH ----------------

@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hash_password(user.password),
        disease_type=user.disease_type,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


# ---------------- PATIENT PROFILE (CRUD) ----------------

@app.get("/profile/me", response_model=schemas.UserOut)
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.put("/profile/me", response_model=schemas.UserOut)
def update_my_profile(
    updates: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if updates.full_name is not None:
        current_user.full_name = updates.full_name
    if updates.disease_type is not None:
        current_user.disease_type = updates.disease_type
    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------- DIAGNOSIS HISTORY (CRUD) ----------------

@app.post("/diagnosis", response_model=schemas.DiagnosisOut)
def add_diagnosis(
    entry: schemas.DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    new_entry = models.DiagnosisHistory(
        user_id=current_user.id,
        reading_type=entry.reading_type,
        value=entry.value,
        notes=entry.notes,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


@app.get("/diagnosis", response_model=List[schemas.DiagnosisOut])
def list_diagnosis(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.DiagnosisHistory)
        .filter(models.DiagnosisHistory.user_id == current_user.id)
        .order_by(models.DiagnosisHistory.recorded_at.desc())
        .all()
    )


@app.delete("/diagnosis/{entry_id}")
def delete_diagnosis(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.DiagnosisHistory)
        .filter(models.DiagnosisHistory.id == entry_id, models.DiagnosisHistory.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted successfully"}


# ---------------- MEDICINES ----------------

@app.post("/medicines", response_model=schemas.MedicineOut)
def add_medicine(
    medicine: schemas.MedicineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    new_medicine = models.Medicine(
        user_id=current_user.id,
        name=medicine.name,
        dosage=medicine.dosage,
        times=medicine.times,
    )
    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)
    return new_medicine


@app.get("/medicines", response_model=List[schemas.MedicineOut])
def list_medicines(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Medicine)
        .filter(models.Medicine.user_id == current_user.id)
        .order_by(models.Medicine.created_at.desc())
        .all()
    )


@app.delete("/medicines/{medicine_id}")
def delete_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    medicine = (
        db.query(models.Medicine)
        .filter(models.Medicine.id == medicine_id, models.Medicine.user_id == current_user.id)
        .first()
    )
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    db.delete(medicine)
    db.commit()
    return {"message": "Deleted successfully"}


# ---------------- NOTIFICATIONS ----------------

@app.get("/notifications", response_model=List[schemas.NotificationOut])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Notification).filter(models.Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.Notification.is_read == 0)
    return query.order_by(models.Notification.created_at.desc()).all()


@app.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notification = (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id, models.Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = 1
    db.commit()
    return {"message": "Marked as read"}


# ---------------- RISK PREDICTION ----------------

@app.post("/risk/predict", response_model=schemas.RiskAssessmentOut)
def predict_patient_risk(
    payload: schemas.RiskPredictRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Runs the saved scikit-learn model on the 4 numbers the patient enters,
    saves the result to their history, and returns it. The model itself is
    loaded once from ml/risk_model.pkl (see ml/predictor.py) -- this endpoint
    does NOT retrain anything, it just asks the already-trained model for a
    prediction, which is why it responds instantly.
    """
    risk_level, confidence = predict_risk(
        glucose=payload.glucose,
        bp=payload.blood_pressure,
        bmi=payload.bmi,
        age=payload.age,
    )

    new_assessment = models.RiskAssessment(
        user_id=current_user.id,
        glucose=payload.glucose,
        blood_pressure=payload.blood_pressure,
        bmi=payload.bmi,
        age=payload.age,
        risk_level=risk_level,
        confidence=confidence,
    )
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    return new_assessment


@app.get("/risk/history", response_model=List[schemas.RiskAssessmentOut])
def get_risk_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.user_id == current_user.id)
        .order_by(models.RiskAssessment.created_at.desc())
        .all()
    )


@app.get("/risk/latest", response_model=schemas.RiskAssessmentOut)
def get_latest_risk(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    latest = (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.user_id == current_user.id)
        .order_by(models.RiskAssessment.created_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No risk assessment yet")
    return latest
