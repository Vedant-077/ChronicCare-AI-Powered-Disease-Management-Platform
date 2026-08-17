# models.py
# Each class here becomes a TABLE in the database.
# Think of a table like an Excel sheet: the class = sheet name,
# each attribute (Column) = a column header.

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """
    One row per patient account (login credentials + basic info).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # NEVER store plain passwords
    disease_type = Column(String, nullable=True)  # e.g. "Diabetes", "Hypertension"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # This lets us do `user.diagnoses` in Python to get all their history rows
    diagnoses = relationship("DiagnosisHistory", back_populates="owner", cascade="all, delete")
    medicines = relationship("Medicine", back_populates="owner", cascade="all, delete")
    risk_assessments = relationship("RiskAssessment", back_populates="owner", cascade="all, delete")


class DiagnosisHistory(Base):
    """
    One row per past diagnosis / vitals reading for a patient.
    Linked to a User via user_id (a "foreign key").
    """
    __tablename__ = "diagnosis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reading_type = Column(String, nullable=False)   # e.g. "Blood Sugar", "Blood Pressure"
    value = Column(String, nullable=False)           # e.g. "140 mg/dL" or "130/85 mmHg"
    notes = Column(String, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="diagnoses")


class Medicine(Base):
    """
    One row per medicine a patient takes.
    `times` stores the reminder times as a comma-separated string
    of 24-hour clock times, e.g. "08:00,14:00,20:00" -- kept simple
    on purpose instead of a separate table, since a medicine rarely
    has more than a handful of times per day.
    """
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)   # e.g. "500mg"
    times = Column(String, nullable=False)   # e.g. "08:00,20:00"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="medicines")
    notifications = relationship("Notification", back_populates="medicine", cascade="all, delete")


class Notification(Base):
    """
    One row per reminder that has actually fired. The background
    scheduler creates these; the frontend polls for unread ones.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Integer, default=0)  # 0 = unread, 1 = read (SQLite has no native bool)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medicine = relationship("Medicine", back_populates="notifications")


class RiskAssessment(Base):
    """
    One row per time a patient ran the risk-prediction model. We save the
    inputs used AND the result, so the dashboard can always show "your most
    recent check" and, later, a trend over time -- without re-running the
    model just to display history.
    """
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    glucose = Column(Float, nullable=False)
    blood_pressure = Column(Float, nullable=False)
    bmi = Column(Float, nullable=False)
    age = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)     # "Low" / "Medium" / "High"
    confidence = Column(Float, nullable=False)       # model's confidence %, 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="risk_assessments")
