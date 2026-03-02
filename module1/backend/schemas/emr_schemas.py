"""
FCMS Module 1 - Pydantic Schemas
Auth, Patient, Visit request/response models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
import uuid


# ─── AUTH ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str
    mfa_code: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str

class UserCreate(BaseModel):
    email: str
    password: str
    first_name_en: str
    last_name_en: str
    first_name_th: Optional[str] = None
    last_name_th: Optional[str] = None
    role: str
    license_number: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name_en: str
    last_name_en: str
    role: str
    is_active: bool
    is_mfa_enabled: bool
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class MFASetupResponse(BaseModel):
    secret: str
    uri: str


# ─── PATIENT ────────────────────────────────────────────

class PatientCreate(BaseModel):
    first_name_en: str
    last_name_en: str
    first_name_th: Optional[str] = None
    last_name_th: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    id_number: Optional[str] = None
    id_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    nationality: str = "Thai"
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    referring_doctor: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

class PatientUpdate(BaseModel):
    first_name_en: Optional[str] = None
    last_name_en: Optional[str] = None
    first_name_th: Optional[str] = None
    last_name_th: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

class PatientOut(BaseModel):
    id: uuid.UUID
    hn_number: str
    first_name_en: str
    last_name_en: str
    first_name_th: Optional[str]
    last_name_th: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    blood_type: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class PatientSearch(BaseModel):
    query: Optional[str] = None     # search name, HN, phone, ID
    gender: Optional[str] = None
    page: int = 1
    per_page: int = 20


# ─── MEDICAL HISTORY ────────────────────────────────────

class MedicalHistoryUpdate(BaseModel):
    chronic_diseases: Optional[List[str]] = None
    previous_surgeries: Optional[List[dict]] = None
    current_medications: Optional[List[dict]] = None
    drug_allergies: Optional[List[str]] = None
    family_history: Optional[List[dict]] = None
    smoking_status: Optional[str] = None
    alcohol_use: Optional[str] = None
    exercise_frequency: Optional[str] = None
    notes: Optional[str] = None

class FertilityHistoryUpdate(BaseModel):
    gravida: Optional[int] = None
    para: Optional[int] = None
    abortion: Optional[int] = None
    living_children: Optional[int] = None
    menarche_age: Optional[int] = None
    cycle_length_days: Optional[int] = None
    cycle_regularity: Optional[str] = None
    last_menstrual_period: Optional[date] = None
    previous_contraception: Optional[List[str]] = None
    infertility_duration_months: Optional[int] = None
    infertility_type: Optional[str] = None
    previous_treatments: Optional[List[dict]] = None
    partner_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


# ─── VISIT ───────────────────────────────────────────────

class VisitCreate(BaseModel):
    patient_id: uuid.UUID
    physician_id: Optional[uuid.UUID] = None
    visit_type: str = "follow_up"
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None

class VisitOut(BaseModel):
    id: uuid.UUID
    visit_number: str
    patient_id: uuid.UUID
    visit_type: str
    status: str
    visit_date: datetime
    chief_complaint: Optional[str]

    class Config:
        from_attributes = True


# ─── SOAP NOTES ──────────────────────────────────────────

class SOAPNoteCreate(BaseModel):
    visit_id: uuid.UUID
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None

class SOAPNoteOut(BaseModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    subjective: Optional[str]
    objective: Optional[str]
    assessment: Optional[str]
    plan: Optional[str]
    is_signed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── DIAGNOSIS ───────────────────────────────────────────

class DiagnosisCreate(BaseModel):
    visit_id: uuid.UUID
    icd10_code: str
    description: Optional[str] = None
    is_primary: bool = False
    notes: Optional[str] = None
