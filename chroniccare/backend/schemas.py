# schemas.py
# These define the "shape" of data going IN to our API (requests)
# and OUT of our API (responses). FastAPI uses these to auto-validate
# input and to generate the interactive docs at /docs.

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# ---- Auth ----

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    disease_type: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- User / Profile ----

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    disease_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True  # lets this read directly from a SQLAlchemy object


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    disease_type: Optional[str] = None


# ---- Diagnosis History ----

class DiagnosisCreate(BaseModel):
    reading_type: str
    value: str
    notes: Optional[str] = None


class DiagnosisOut(BaseModel):
    id: int
    reading_type: str
    value: str
    notes: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# ---- Medicines ----

class MedicineCreate(BaseModel):
    name: str
    dosage: Optional[str] = None
    times: str  # comma-separated "HH:MM" values, e.g. "08:00,20:00"


class MedicineOut(BaseModel):
    id: int
    name: str
    dosage: Optional[str] = None
    times: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Notifications ----

class NotificationOut(BaseModel):
    id: int
    medicine_id: int
    message: str
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Risk Prediction ----

class RiskPredictRequest(BaseModel):
    glucose: float           # fasting blood glucose, mg/dL
    blood_pressure: float    # systolic blood pressure, mmHg
    bmi: float                # body mass index
    age: float


class RiskAssessmentOut(BaseModel):
    id: int
    glucose: float
    blood_pressure: float
    bmi: float
    age: float
    risk_level: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True
