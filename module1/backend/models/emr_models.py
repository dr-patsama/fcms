"""
FCMS Module 1 - Patient & EMR Models
Demographics, medical history, visits, SOAP notes, ICD-10, consents
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

def gen_uuid():
    return str(uuid.uuid4())

from ..core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    hn_number        = Column(String(20), unique=True, nullable=False)  # HN-2026-00001
    first_name_en    = Column(String(100), nullable=False)
    last_name_en     = Column(String(100), nullable=False)
    first_name_th    = Column(String(100))
    last_name_th     = Column(String(100))
    date_of_birth    = Column(Date)
    gender           = Column(String(10))         # male | female
    id_number        = Column(String(20))         # Thai ID or passport
    id_type          = Column(String(20))         # thai_id | passport
    phone            = Column(String(20))
    email            = Column(String(200))
    blood_type       = Column(String(5))
    allergies        = Column(Text)
    marital_status   = Column(String(20))
    occupation       = Column(String(100))
    nationality      = Column(String(50), default="Thai")
    address          = Column(Text)
    emergency_contact_name  = Column(String(200))
    emergency_contact_phone = Column(String(20))
    referring_doctor = Column(String(200))
    insurance_provider = Column(String(200))
    insurance_number = Column(String(50))
    avatar_url       = Column(String(500))
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    created_by       = Column(UUID, ForeignKey("users.id"))
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    visits            = relationship("Visit", back_populates="patient")
    medical_history   = relationship("MedicalHistory", back_populates="patient", uselist=False)
    fertility_history = relationship("FertilityHistory", back_populates="patient", uselist=False)
    consents          = relationship("ConsentForm", back_populates="patient")

    __table_args__ = (
        Index("ix_patients_hn",    "hn_number"),
        Index("ix_patients_name",  "last_name_en", "first_name_en"),
        Index("ix_patients_id_num","id_number"),
        Index("ix_patients_phone", "phone"),
    )


class MedicalHistory(Base):
    __tablename__ = "medical_histories"

    id                   = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id           = Column(UUID, ForeignKey("patients.id"), nullable=False, unique=True)
    chronic_diseases     = Column(JSON, default=[])
    previous_surgeries   = Column(JSON, default=[])
    current_medications  = Column(JSON, default=[])
    drug_allergies       = Column(JSON, default=[])
    family_history       = Column(JSON, default=[])
    smoking_status       = Column(String(20))
    alcohol_use          = Column(String(20))
    exercise_frequency   = Column(String(30))
    notes                = Column(Text)
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient", back_populates="medical_history")


class FertilityHistory(Base):
    __tablename__ = "fertility_histories"

    id                      = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id              = Column(UUID, ForeignKey("patients.id"), nullable=False, unique=True)
    gravida                 = Column(Integer, default=0)
    para                    = Column(Integer, default=0)
    abortion                = Column(Integer, default=0)
    living_children         = Column(Integer, default=0)
    menarche_age            = Column(Integer)
    cycle_length_days       = Column(Integer)
    cycle_regularity        = Column(String(20))   # regular | irregular
    last_menstrual_period   = Column(Date)
    previous_contraception  = Column(JSON, default=[])
    infertility_duration_months = Column(Integer)
    infertility_type        = Column(String(20))   # primary | secondary
    previous_treatments     = Column(JSON, default=[])  # [{type, date, outcome}]
    partner_id              = Column(UUID, ForeignKey("patients.id"))
    notes                   = Column(Text)
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient", back_populates="fertility_history", foreign_keys=[patient_id])


class Visit(Base):
    __tablename__ = "visits"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    visit_number    = Column(String(20), unique=True, nullable=False)  # V-2026-00001
    patient_id      = Column(UUID, ForeignKey("patients.id"), nullable=False)
    physician_id    = Column(UUID, ForeignKey("users.id"))
    visit_date      = Column(DateTime(timezone=True), server_default=func.now())
    visit_type      = Column(String(30))        # new | follow_up | procedure | emergency
    chief_complaint = Column(Text)
    status          = Column(String(20), default="checked_in")  # scheduled | checked_in | in_progress | completed | cancelled
    checkout_at     = Column(DateTime(timezone=True))
    created_by      = Column(UUID, ForeignKey("users.id"))
    notes           = Column(Text)

    patient     = relationship("Patient", back_populates="visits")
    soap_notes  = relationship("SOAPNote", back_populates="visit")
    diagnoses   = relationship("VisitDiagnosis", back_populates="visit")

    __table_args__ = (
        Index("ix_visits_patient", "patient_id"),
        Index("ix_visits_date",    "visit_date"),
        Index("ix_visits_status",  "status"),
    )


class SOAPNote(Base):
    """SOAP format clinical notes"""
    __tablename__ = "soap_notes"

    id           = Column(UUID, primary_key=True, default=gen_uuid)
    visit_id     = Column(UUID, ForeignKey("visits.id"), nullable=False)
    author_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    subjective   = Column(Text)
    objective    = Column(Text)
    assessment   = Column(Text)
    plan         = Column(Text)
    addendum     = Column(Text)
    is_signed    = Column(Boolean, default=False)
    signed_at    = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    visit = relationship("Visit", back_populates="soap_notes")


class VisitDiagnosis(Base):
    """ICD-10 diagnoses per visit"""
    __tablename__ = "visit_diagnoses"

    id          = Column(UUID, primary_key=True, default=gen_uuid)
    visit_id    = Column(UUID, ForeignKey("visits.id"), nullable=False)
    icd10_code  = Column(String(10), nullable=False)
    description = Column(String(300))
    is_primary  = Column(Boolean, default=False)
    notes       = Column(Text)

    visit = relationship("Visit", back_populates="diagnoses")


class ConsentForm(Base):
    __tablename__ = "consent_forms"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id    = Column(UUID, ForeignKey("patients.id"), nullable=False)
    consent_type  = Column(String(50), nullable=False)  # treatment | ivf | data_processing | research
    version       = Column(String(10))
    signed_at     = Column(DateTime(timezone=True))
    witness_name  = Column(String(200))
    document_path = Column(String(500))
    is_active     = Column(Boolean, default=True)
    revoked_at    = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="consents")
