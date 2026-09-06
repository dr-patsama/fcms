"""
FCMS Module 6 — CRM ORM Models / โมเดลฐานข้อมูล CRM
Appointments, virtual consultations, reminders, communication logs, patient preferences.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text, Time,
    ForeignKey, Numeric, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

def gen_uuid():
    return str(uuid.uuid4())

from module1.backend.core.database import Base


# ── Appointment / การนัดหมาย ──────────────────────────────

class Appointment(Base):
    """Patient appointment / booking record."""
    __tablename__ = "appointments"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    booking_number    = Column(String(20), unique=True, nullable=False)  # BK-2026-00001
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    # Scheduling
    appointment_date  = Column(Date, nullable=False, index=True)
    appointment_time  = Column(Time, nullable=False)
    end_time          = Column(Time)
    duration_minutes  = Column(Integer, default=30)
    # Type & details
    appointment_type  = Column(String(30), nullable=False, index=True)
    # new_patient | follow_up | consultation | ultrasound | blood_test
    # egg_collection | embryo_transfer | iui | virtual_consultation
    # hysteroscopy | prp | procedure | other
    appointment_type_th = Column(String(50))
    department        = Column(String(30))
    # clinic | embryology_lab | andrology_lab | general_lab | operating_room | virtual
    room              = Column(String(50))
    # Provider
    provider_id       = Column(UUID, ForeignKey("users.id"), index=True)
    # Status
    status            = Column(String(20), default="scheduled", index=True)
    # scheduled | confirmed | checked_in | in_progress | completed
    # no_show | cancelled | rescheduled
    priority          = Column(String(10), default="normal")  # normal | urgent | vip
    # Source
    booking_source    = Column(String(20), default="staff")
    # staff | online | phone | line | whatsapp | walk_in
    # Notes
    chief_complaint   = Column(Text)
    chief_complaint_th = Column(Text)
    notes             = Column(Text)
    notes_th          = Column(Text)
    preparation_instructions = Column(Text)    # e.g. fasting, bladder prep
    preparation_instructions_th = Column(Text)
    # Cancellation
    cancelled_by      = Column(UUID, ForeignKey("users.id"))
    cancelled_at      = Column(DateTime(timezone=True))
    cancel_reason     = Column(Text)
    # Rescheduled from
    rescheduled_from  = Column(UUID, ForeignKey("appointments.id"))
    # Audit
    created_by        = Column(UUID, ForeignKey("users.id"))
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    reminders = relationship("AppointmentReminder", back_populates="appointment", cascade="all, delete-orphan")


# ── Virtual Consultation / การปรึกษาทางไกล ────────────────

class VirtualConsultation(Base):
    """Virtual consultation session (video call)."""
    __tablename__ = "virtual_consultations"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    appointment_id    = Column(UUID, ForeignKey("appointments.id"), nullable=False, index=True)
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    provider_id       = Column(UUID, ForeignKey("users.id"), nullable=False)
    # Session
    session_token     = Column(String(200), unique=True)
    room_url          = Column(String(500))          # Video platform room link
    platform          = Column(String(30), default="internal")
    # internal | zoom | google_meet | line_video | other
    # Timing
    scheduled_start   = Column(DateTime(timezone=True), nullable=False)
    scheduled_end     = Column(DateTime(timezone=True))
    actual_start      = Column(DateTime(timezone=True))
    actual_end        = Column(DateTime(timezone=True))
    duration_minutes  = Column(Integer)
    # Status
    status            = Column(String(20), default="scheduled")
    # scheduled | waiting | in_progress | completed | cancelled | no_show
    # Clinical
    consultation_notes = Column(Text)
    consultation_notes_th = Column(Text)
    diagnosis         = Column(Text)
    follow_up_plan    = Column(Text)
    follow_up_plan_th = Column(Text)
    attachments       = Column(JSON)   # [{filename, url, type}]
    # Quality
    connection_quality = Column(String(20))  # excellent | good | fair | poor
    patient_satisfaction = Column(Integer)    # 1-5
    # Audit
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())


# ── Appointment Reminders / แจ้งเตือนการนัดหมาย ──────────

class AppointmentReminder(Base):
    """Scheduled reminder for an appointment."""
    __tablename__ = "appointment_reminders"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    appointment_id    = Column(UUID, ForeignKey("appointments.id"), nullable=False, index=True)
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False)
    # Channel & timing
    channel           = Column(String(20), nullable=False)
    # sms | line | email | whatsapp
    scheduled_at      = Column(DateTime(timezone=True), nullable=False)
    trigger_offset    = Column(String(20))  # 24h | 1h | 48h | 7d | custom
    # Content
    template_key      = Column(String(50))  # confirmation | reminder_24h | reminder_1h | follow_up
    message_en        = Column(Text)
    message_th        = Column(Text)
    # Delivery
    status            = Column(String(20), default="pending")
    # pending | sent | delivered | failed | cancelled
    sent_at           = Column(DateTime(timezone=True))
    delivered_at      = Column(DateTime(timezone=True))
    failure_reason    = Column(Text)
    external_id       = Column(String(100))  # SMS/LINE/WhatsApp message ID
    # Audit
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    appointment = relationship("Appointment", back_populates="reminders")


# ── Communication Log / บันทึกการสื่อสาร ──────────────────

class CommunicationLog(Base):
    """Log of all outbound communications to patients."""
    __tablename__ = "communication_logs"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    # Channel
    channel           = Column(String(20), nullable=False, index=True)
    # sms | line | email | whatsapp | phone_call
    direction         = Column(String(10), default="outbound")  # outbound | inbound
    # Content
    subject           = Column(String(200))
    message_en        = Column(Text)
    message_th        = Column(Text)
    template_key      = Column(String(50))
    # Delivery
    recipient         = Column(String(200))  # phone, email, LINE ID
    status            = Column(String(20), default="sent")
    # sent | delivered | read | failed | bounced
    external_id       = Column(String(100))
    # Reference
    reference_type    = Column(String(30))  # appointment | follow_up | promotion | result_ready
    reference_id      = Column(UUID)
    # Audit
    sent_by           = Column(UUID, ForeignKey("users.id"))
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── Patient Contact Preferences / ช่องทางการติดต่อ ────────

class PatientContactPreference(Base):
    """Patient's preferred contact channels and times."""
    __tablename__ = "patient_contact_preferences"

    id                   = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id           = Column(UUID, ForeignKey("patients.id"), unique=True, nullable=False)
    # Contact details
    phone_primary        = Column(String(20))
    phone_secondary      = Column(String(20))
    email                = Column(String(100))
    line_id              = Column(String(50))
    whatsapp_number      = Column(String(20))
    # Preferences
    preferred_channel    = Column(String(20), default="line")
    # sms | line | email | whatsapp | phone_call
    preferred_language   = Column(String(5), default="th")  # th | en
    preferred_time       = Column(String(20), default="anytime")
    # morning | afternoon | evening | anytime
    # Consent
    consent_sms          = Column(Boolean, default=True)
    consent_line         = Column(Boolean, default=True)
    consent_email        = Column(Boolean, default=True)
    consent_whatsapp     = Column(Boolean, default=True)
    consent_marketing    = Column(Boolean, default=False)
    # Audit
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())
    created_at           = Column(DateTime(timezone=True), server_default=func.now())


# ── Provider Schedule / ตารางแพทย์ ────────────────────────

class ProviderSchedule(Base):
    """Weekly schedule slots for providers."""
    __tablename__ = "provider_schedules"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    provider_id       = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    day_of_week       = Column(Integer, nullable=False)  # 0=Mon ... 6=Sun
    start_time        = Column(Time, nullable=False)
    end_time          = Column(Time, nullable=False)
    slot_duration     = Column(Integer, default=30)  # minutes
    max_patients      = Column(Integer, default=1)
    appointment_types = Column(JSON)  # ["consultation", "ultrasound", "virtual_consultation"]
    location          = Column(String(50))  # clinic | virtual | operating_room
    is_active         = Column(Boolean, default=True)
    # Overrides
    effective_from    = Column(Date)
    effective_until   = Column(Date)
    notes             = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


# ── Provider Schedule Exception / วันหยุด/วันพิเศษ ────────

class ScheduleException(Base):
    """Block-off dates, holidays, or special hours."""
    __tablename__ = "schedule_exceptions"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    provider_id       = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    exception_date    = Column(Date, nullable=False, index=True)
    exception_type    = Column(String(20), nullable=False)
    # day_off | holiday | reduced_hours | extended_hours | conference
    start_time        = Column(Time)   # for reduced/extended hours
    end_time          = Column(Time)
    reason            = Column(Text)
    reason_th         = Column(Text)
    created_by        = Column(UUID, ForeignKey("users.id"))
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
