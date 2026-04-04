"""
FCMS Module 6 — CRM Pydantic Schemas / สคีมา CRM
Request/response validation for appointments, virtual consultations, reminders, communications.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal


# ── Appointments ──────────────────────────────────────────

class AppointmentCreate(BaseModel):
    patient_id: str
    appointment_date: date
    appointment_time: time
    end_time: Optional[time] = None
    duration_minutes: int = 30
    appointment_type: str = Field(..., min_length=1)
    appointment_type_th: Optional[str] = None
    department: Optional[str] = None
    room: Optional[str] = None
    provider_id: Optional[str] = None
    priority: str = "normal"
    booking_source: str = "staff"
    chief_complaint: Optional[str] = None
    chief_complaint_th: Optional[str] = None
    notes: Optional[str] = None
    notes_th: Optional[str] = None
    preparation_instructions: Optional[str] = None
    preparation_instructions_th: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    appointment_type: Optional[str] = None
    appointment_type_th: Optional[str] = None
    department: Optional[str] = None
    room: Optional[str] = None
    provider_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    chief_complaint: Optional[str] = None
    chief_complaint_th: Optional[str] = None
    notes: Optional[str] = None
    notes_th: Optional[str] = None
    preparation_instructions: Optional[str] = None
    preparation_instructions_th: Optional[str] = None


class AppointmentReschedule(BaseModel):
    new_date: date
    new_time: time
    reason: Optional[str] = None


class AppointmentCancel(BaseModel):
    reason: str = Field(..., min_length=1)


# ── Virtual Consultation ──────────────────────────────────

class VirtualConsultationCreate(BaseModel):
    appointment_id: str
    patient_id: str
    provider_id: str
    scheduled_start: datetime
    scheduled_end: Optional[datetime] = None
    platform: str = "internal"


class VirtualConsultationUpdate(BaseModel):
    status: Optional[str] = None
    consultation_notes: Optional[str] = None
    consultation_notes_th: Optional[str] = None
    diagnosis: Optional[str] = None
    follow_up_plan: Optional[str] = None
    follow_up_plan_th: Optional[str] = None
    connection_quality: Optional[str] = None
    patient_satisfaction: Optional[int] = None


# ── Reminders ─────────────────────────────────────────────

class ReminderCreate(BaseModel):
    appointment_id: str
    patient_id: str
    channel: str  # sms | line | email | whatsapp
    scheduled_at: datetime
    trigger_offset: Optional[str] = None
    template_key: Optional[str] = None
    message_en: Optional[str] = None
    message_th: Optional[str] = None


class BulkReminderRequest(BaseModel):
    appointment_id: str
    channels: List[str]  # ["sms", "line", "email"]
    offsets: List[str] = ["24h"]  # ["24h", "1h"]


# ── Communication ─────────────────────────────────────────

class SendMessageRequest(BaseModel):
    patient_id: str
    channel: str  # sms | line | email | whatsapp
    subject: Optional[str] = None
    message_en: Optional[str] = None
    message_th: Optional[str] = None
    template_key: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


# ── Contact Preferences ──────────────────────────────────

class ContactPreferenceUpdate(BaseModel):
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    preferred_channel: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_time: Optional[str] = None
    consent_sms: Optional[bool] = None
    consent_line: Optional[bool] = None
    consent_email: Optional[bool] = None
    consent_whatsapp: Optional[bool] = None
    consent_marketing: Optional[bool] = None


# ── Provider Schedule ─────────────────────────────────────

class ScheduleSlotCreate(BaseModel):
    provider_id: str
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    slot_duration: int = 30
    max_patients: int = 1
    appointment_types: Optional[List[str]] = None
    location: Optional[str] = None
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    notes: Optional[str] = None


class ScheduleExceptionCreate(BaseModel):
    provider_id: str
    exception_date: date
    exception_type: str  # day_off | holiday | reduced_hours | extended_hours | conference
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None
    reason_th: Optional[str] = None


# ── Bilingual Presets ─────────────────────────────────────

APPOINTMENT_TYPE_OPTIONS = [
    {"value": "new_patient",           "en": "New Patient",             "th": "ผู้ป่วยใหม่"},
    {"value": "follow_up",            "en": "Follow Up",               "th": "ติดตามผล"},
    {"value": "consultation",         "en": "Consultation",            "th": "ปรึกษาแพทย์"},
    {"value": "ultrasound",           "en": "Ultrasound",              "th": "อัลตราซาวด์"},
    {"value": "blood_test",           "en": "Blood Test",              "th": "ตรวจเลือด"},
    {"value": "egg_collection",       "en": "Egg Collection (OPU)",    "th": "เจาะไข่"},
    {"value": "embryo_transfer",      "en": "Embryo Transfer (ET)",    "th": "ย้ายตัวอ่อน"},
    {"value": "iui",                  "en": "IUI",                     "th": "ฉีดอสุจิเข้าโพรงมดลูก"},
    {"value": "virtual_consultation", "en": "Virtual Consultation",    "th": "ปรึกษาทางไกล"},
    {"value": "hysteroscopy",         "en": "Hysteroscopy",            "th": "ส่องกล้องโพรงมดลูก"},
    {"value": "prp",                  "en": "PRP Treatment",           "th": "รักษา PRP"},
    {"value": "semen_analysis",       "en": "Semen Analysis",          "th": "ตรวจวิเคราะห์อสุจิ"},
    {"value": "procedure",            "en": "Procedure",               "th": "หัตถการ"},
    {"value": "other",                "en": "Other",                   "th": "อื่นๆ"},
]

APPOINTMENT_STATUS_OPTIONS = [
    {"value": "scheduled",    "en": "Scheduled",    "th": "นัดหมายแล้ว"},
    {"value": "confirmed",    "en": "Confirmed",    "th": "ยืนยันแล้ว"},
    {"value": "checked_in",   "en": "Checked In",   "th": "เช็คอินแล้ว"},
    {"value": "in_progress",  "en": "In Progress",  "th": "กำลังดำเนินการ"},
    {"value": "completed",    "en": "Completed",    "th": "เสร็จสิ้น"},
    {"value": "no_show",      "en": "No Show",      "th": "ไม่มา"},
    {"value": "cancelled",    "en": "Cancelled",    "th": "ยกเลิก"},
    {"value": "rescheduled",  "en": "Rescheduled",  "th": "เลื่อนนัด"},
]

BOOKING_SOURCE_OPTIONS = [
    {"value": "staff",     "en": "Staff Booking",      "th": "เจ้าหน้าที่นัด"},
    {"value": "online",    "en": "Online Booking",      "th": "จองออนไลน์"},
    {"value": "phone",     "en": "Phone",               "th": "โทรศัพท์"},
    {"value": "line",      "en": "LINE",                "th": "ไลน์"},
    {"value": "whatsapp",  "en": "WhatsApp",            "th": "วอทส์แอป"},
    {"value": "walk_in",   "en": "Walk-in",             "th": "เข้ามาเอง"},
]

CHANNEL_OPTIONS = [
    {"value": "sms",        "en": "SMS",        "th": "SMS"},
    {"value": "line",       "en": "LINE",       "th": "ไลน์"},
    {"value": "email",      "en": "Email",      "th": "อีเมล"},
    {"value": "whatsapp",   "en": "WhatsApp",   "th": "วอทส์แอป"},
    {"value": "phone_call", "en": "Phone Call",  "th": "โทรศัพท์"},
]

REMINDER_TEMPLATE_OPTIONS = [
    {"value": "confirmation",   "en": "Booking Confirmation",  "th": "ยืนยันการนัดหมาย"},
    {"value": "reminder_7d",    "en": "7-Day Reminder",        "th": "แจ้งเตือน 7 วัน"},
    {"value": "reminder_24h",   "en": "24-Hour Reminder",      "th": "แจ้งเตือน 24 ชม."},
    {"value": "reminder_1h",    "en": "1-Hour Reminder",       "th": "แจ้งเตือน 1 ชม."},
    {"value": "follow_up",      "en": "Follow Up",             "th": "ติดตามผล"},
    {"value": "result_ready",   "en": "Result Ready",          "th": "ผลตรวจพร้อม"},
    {"value": "preparation",    "en": "Preparation Instructions", "th": "คำแนะนำเตรียมตัว"},
]

DEPARTMENT_OPTIONS = [
    {"value": "clinic",          "en": "Clinic Room",      "th": "ห้องตรวจ"},
    {"value": "embryology_lab",  "en": "Embryology Lab",   "th": "แล็บตัวอ่อน"},
    {"value": "andrology_lab",   "en": "Andrology Lab",    "th": "แล็บอสุจิ"},
    {"value": "general_lab",     "en": "General Lab",      "th": "แล็บทั่วไป"},
    {"value": "operating_room",  "en": "Operating Room",   "th": "ห้องผ่าตัด"},
    {"value": "virtual",         "en": "Virtual",          "th": "ทางไกล"},
]

PLATFORM_OPTIONS = [
    {"value": "internal",     "en": "Clinic System",  "th": "ระบบคลินิก"},
    {"value": "zoom",         "en": "Zoom",           "th": "Zoom"},
    {"value": "google_meet",  "en": "Google Meet",    "th": "Google Meet"},
    {"value": "line_video",   "en": "LINE Video",     "th": "LINE วิดีโอ"},
    {"value": "other",        "en": "Other",          "th": "อื่นๆ"},
]

DAY_OF_WEEK_OPTIONS = [
    {"value": 0, "en": "Monday",    "th": "จันทร์"},
    {"value": 1, "en": "Tuesday",   "th": "อังคาร"},
    {"value": 2, "en": "Wednesday", "th": "พุธ"},
    {"value": 3, "en": "Thursday",  "th": "พฤหัสบดี"},
    {"value": 4, "en": "Friday",    "th": "ศุกร์"},
    {"value": 5, "en": "Saturday",  "th": "เสาร์"},
    {"value": 6, "en": "Sunday",    "th": "อาทิตย์"},
]
