"""
FCMS Module 6 — CRM API Routes / เส้นทาง API CRM
Appointments, virtual consultations, reminders (SMS/LINE/Email/WhatsApp),
communication logs, provider scheduling, patient contact preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_, cast, Date
from datetime import datetime, timezone, date, time, timedelta
from typing import Optional
import uuid
import secrets

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/crm", tags=["CRM / ระบบบริหารลูกค้าสัมพันธ์"])

# ── Helpers ───────────────────────────────────────────────

_bk_counter = 0

def _next_booking_number(db: Session) -> str:
    global _bk_counter
    year = datetime.now().year
    _bk_counter += 1
    return f"BK-{year}-{_bk_counter:05d}"


def _audit(db, user, action, resource_type, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()), user_id=user.id if user else None,
        action=action, module="crm", resource_type=resource_type,
        resource_id=resource_id, detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


# ══════════════════════════════════════════════════════════
# 1. APPOINTMENTS / การนัดหมาย
# ══════════════════════════════════════════════════════════

@router.get("/appointments")
async def list_appointments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    appointment_type: Optional[str] = None,
    provider_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """List appointments with filters. / แสดงรายการนัดหมาย"""
    from ..models.crm_models import Appointment

    q = db.query(Appointment)
    if date_from:
        q = q.filter(Appointment.appointment_date >= date_from)
    if date_to:
        q = q.filter(Appointment.appointment_date <= date_to)
    if status:
        q = q.filter(Appointment.status == status)
    if appointment_type:
        q = q.filter(Appointment.appointment_type == appointment_type)
    if provider_id:
        q = q.filter(Appointment.provider_id == provider_id)
    if patient_id:
        q = q.filter(Appointment.patient_id == patient_id)

    total = q.count()
    appts = q.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.asc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "appointments": [{
            "id": a.id, "booking_number": a.booking_number,
            "patient_id": a.patient_id,
            "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
            "appointment_time": a.appointment_time.isoformat() if a.appointment_time else None,
            "duration_minutes": a.duration_minutes,
            "appointment_type": a.appointment_type,
            "appointment_type_th": a.appointment_type_th,
            "department": a.department, "room": a.room,
            "provider_id": a.provider_id,
            "status": a.status, "priority": a.priority,
            "booking_source": a.booking_source,
            "chief_complaint": a.chief_complaint,
            "notes": a.notes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in appts],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/appointments")
async def create_appointment(
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Create a new appointment. / สร้างนัดหมายใหม่"""
    from ..models.crm_models import Appointment
    body = await request.json()

    for f in ["patient_id", "appointment_date", "appointment_time", "appointment_type"]:
        if not body.get(f):
            raise HTTPException(400, f"{f} is required / จำเป็นต้องกรอก {f}")

    appt = Appointment(
        id=str(uuid.uuid4()),
        booking_number=_next_booking_number(db),
        patient_id=body["patient_id"],
        appointment_date=body["appointment_date"],
        appointment_time=body["appointment_time"],
        end_time=body.get("end_time"),
        duration_minutes=body.get("duration_minutes", 30),
        appointment_type=body["appointment_type"],
        appointment_type_th=body.get("appointment_type_th"),
        department=body.get("department"),
        room=body.get("room"),
        provider_id=body.get("provider_id"),
        priority=body.get("priority", "normal"),
        booking_source=body.get("booking_source", "staff"),
        chief_complaint=body.get("chief_complaint"),
        chief_complaint_th=body.get("chief_complaint_th"),
        notes=body.get("notes"),
        notes_th=body.get("notes_th"),
        preparation_instructions=body.get("preparation_instructions"),
        preparation_instructions_th=body.get("preparation_instructions_th"),
        created_by=current_user.id,
    )
    db.add(appt)
    _audit(db, current_user, "CREATE", "appointment", appt.id,
           f"Booking {appt.booking_number} — {body['appointment_type']} on {body['appointment_date']}", request)
    db.commit()
    db.refresh(appt)

    return {
        "id": appt.id, "booking_number": appt.booking_number,
        "message": "Appointment created / สร้างนัดหมายสำเร็จ",
    }


@router.get("/appointments/{appt_id}")
async def get_appointment(
    appt_id: str,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Get appointment detail with reminders. / รายละเอียดนัดหมาย"""
    from ..models.crm_models import Appointment, VirtualConsultation

    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")

    vc = db.query(VirtualConsultation).filter(
        VirtualConsultation.appointment_id == appt_id
    ).first()

    reminders = [{
        "id": r.id, "channel": r.channel,
        "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        "status": r.status, "template_key": r.template_key,
    } for r in appt.reminders] if appt.reminders else []

    result = {
        "id": appt.id, "booking_number": appt.booking_number,
        "patient_id": appt.patient_id,
        "appointment_date": appt.appointment_date.isoformat() if appt.appointment_date else None,
        "appointment_time": appt.appointment_time.isoformat() if appt.appointment_time else None,
        "end_time": appt.end_time.isoformat() if appt.end_time else None,
        "duration_minutes": appt.duration_minutes,
        "appointment_type": appt.appointment_type,
        "appointment_type_th": appt.appointment_type_th,
        "department": appt.department, "room": appt.room,
        "provider_id": appt.provider_id,
        "status": appt.status, "priority": appt.priority,
        "booking_source": appt.booking_source,
        "chief_complaint": appt.chief_complaint,
        "chief_complaint_th": appt.chief_complaint_th,
        "notes": appt.notes, "notes_th": appt.notes_th,
        "preparation_instructions": appt.preparation_instructions,
        "preparation_instructions_th": appt.preparation_instructions_th,
        "reminders": reminders,
        "virtual_consultation": {
            "id": vc.id, "status": vc.status, "platform": vc.platform,
            "room_url": vc.room_url,
        } if vc else None,
        "created_at": appt.created_at.isoformat() if appt.created_at else None,
    }
    return result


@router.patch("/appointments/{appt_id}")
async def update_appointment(
    appt_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Update appointment. / แก้ไขนัดหมาย"""
    from ..models.crm_models import Appointment
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")

    body = await request.json()
    updatable = [
        "appointment_date", "appointment_time", "end_time", "duration_minutes",
        "appointment_type", "appointment_type_th", "department", "room",
        "provider_id", "priority", "status", "chief_complaint", "chief_complaint_th",
        "notes", "notes_th", "preparation_instructions", "preparation_instructions_th",
    ]
    changes = []
    for field in updatable:
        if field in body:
            old = getattr(appt, field)
            setattr(appt, field, body[field])
            changes.append(f"{field}: {old} → {body[field]}")

    _audit(db, current_user, "UPDATE", "appointment", appt.id,
           "; ".join(changes[:5]), request)
    db.commit()
    return {"id": appt.id, "message": "Appointment updated / แก้ไขนัดหมายสำเร็จ"}


@router.post("/appointments/{appt_id}/check-in")
async def check_in_appointment(
    appt_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Check in a patient. / เช็คอินผู้ป่วย"""
    from ..models.crm_models import Appointment
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")
    if appt.status not in ("scheduled", "confirmed"):
        raise HTTPException(400, f"Cannot check in — status is {appt.status}")

    appt.status = "checked_in"
    _audit(db, current_user, "UPDATE", "appointment", appt.id, "Patient checked in", request)
    db.commit()
    return {"id": appt.id, "status": "checked_in", "message": "Checked in / เช็คอินสำเร็จ"}


@router.post("/appointments/{appt_id}/cancel")
async def cancel_appointment(
    appt_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Cancel appointment. / ยกเลิกนัดหมาย"""
    from ..models.crm_models import Appointment
    body = await request.json()

    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")
    if appt.status in ("completed", "cancelled"):
        raise HTTPException(400, f"Cannot cancel — status is {appt.status}")

    appt.status = "cancelled"
    appt.cancelled_by = current_user.id
    appt.cancelled_at = datetime.now(timezone.utc)
    appt.cancel_reason = body.get("reason", "")

    _audit(db, current_user, "UPDATE", "appointment", appt.id,
           f"Cancelled: {appt.cancel_reason}", request)
    db.commit()
    return {"id": appt.id, "status": "cancelled", "message": "Cancelled / ยกเลิกสำเร็จ"}


@router.post("/appointments/{appt_id}/reschedule")
async def reschedule_appointment(
    appt_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Reschedule — creates new appointment linked to old. / เลื่อนนัดหมาย"""
    from ..models.crm_models import Appointment
    body = await request.json()

    old = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not old:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")

    old.status = "rescheduled"

    new_appt = Appointment(
        id=str(uuid.uuid4()),
        booking_number=_next_booking_number(db),
        patient_id=old.patient_id,
        appointment_date=body["new_date"],
        appointment_time=body["new_time"],
        duration_minutes=old.duration_minutes,
        appointment_type=old.appointment_type,
        appointment_type_th=old.appointment_type_th,
        department=old.department, room=old.room,
        provider_id=old.provider_id,
        priority=old.priority,
        booking_source=old.booking_source,
        chief_complaint=old.chief_complaint,
        notes=old.notes,
        preparation_instructions=old.preparation_instructions,
        preparation_instructions_th=old.preparation_instructions_th,
        rescheduled_from=old.id,
        created_by=current_user.id,
    )
    db.add(new_appt)
    _audit(db, current_user, "CREATE", "appointment", new_appt.id,
           f"Rescheduled from {old.booking_number} to {body['new_date']}", request)
    db.commit()
    return {
        "old_id": old.id, "new_id": new_appt.id,
        "new_booking_number": new_appt.booking_number,
        "message": "Rescheduled / เลื่อนนัดหมายสำเร็จ",
    }


# ══════════════════════════════════════════════════════════
# 2. VIRTUAL CONSULTATION / การปรึกษาทางไกล
# ══════════════════════════════════════════════════════════

@router.post("/consultations")
async def create_virtual_consultation(
    request: Request,
    current_user: User = Depends(require_roles(["physician", "admin", "it_admin", "nurse"])),
    db: Session = Depends(get_db),
):
    """Create virtual consultation session. / สร้างเซสชันปรึกษาทางไกล"""
    from ..models.crm_models import VirtualConsultation
    body = await request.json()

    vc = VirtualConsultation(
        id=str(uuid.uuid4()),
        appointment_id=body["appointment_id"],
        patient_id=body["patient_id"],
        provider_id=body["provider_id"],
        session_token=secrets.token_urlsafe(32),
        platform=body.get("platform", "internal"),
        scheduled_start=body["scheduled_start"],
        scheduled_end=body.get("scheduled_end"),
        status="scheduled",
    )
    db.add(vc)
    _audit(db, current_user, "CREATE", "virtual_consultation", vc.id,
           f"VC for appointment {body['appointment_id']}", request)
    db.commit()
    db.refresh(vc)

    return {
        "id": vc.id, "session_token": vc.session_token,
        "message": "Virtual consultation created / สร้างเซสชันสำเร็จ",
    }


@router.get("/consultations")
async def list_consultations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    provider_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """List virtual consultations. / แสดงรายการปรึกษาทางไกล"""
    from ..models.crm_models import VirtualConsultation

    q = db.query(VirtualConsultation)
    if status:
        q = q.filter(VirtualConsultation.status == status)
    if provider_id:
        q = q.filter(VirtualConsultation.provider_id == provider_id)
    if date_from:
        q = q.filter(VirtualConsultation.scheduled_start >= date_from)
    if date_to:
        q = q.filter(VirtualConsultation.scheduled_start <= date_to)

    total = q.count()
    vcs = q.order_by(desc(VirtualConsultation.scheduled_start)).offset(
        (page - 1) * per_page).limit(per_page).all()

    return {
        "consultations": [{
            "id": vc.id, "appointment_id": vc.appointment_id,
            "patient_id": vc.patient_id, "provider_id": vc.provider_id,
            "platform": vc.platform, "status": vc.status,
            "scheduled_start": vc.scheduled_start.isoformat() if vc.scheduled_start else None,
            "actual_start": vc.actual_start.isoformat() if vc.actual_start else None,
            "duration_minutes": vc.duration_minutes,
        } for vc in vcs],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.patch("/consultations/{vc_id}")
async def update_consultation(
    vc_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["physician", "admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Update virtual consultation (notes, status). / อัปเดตเซสชัน"""
    from ..models.crm_models import VirtualConsultation
    vc = db.query(VirtualConsultation).filter(VirtualConsultation.id == vc_id).first()
    if not vc:
        raise HTTPException(404, "Consultation not found / ไม่พบเซสชัน")

    body = await request.json()
    updatable = [
        "status", "consultation_notes", "consultation_notes_th",
        "diagnosis", "follow_up_plan", "follow_up_plan_th",
        "connection_quality", "patient_satisfaction",
    ]
    for field in updatable:
        if field in body:
            setattr(vc, field, body[field])

    # Auto-set timing
    if body.get("status") == "in_progress" and not vc.actual_start:
        vc.actual_start = datetime.now(timezone.utc)
    elif body.get("status") == "completed" and not vc.actual_end:
        vc.actual_end = datetime.now(timezone.utc)
        if vc.actual_start:
            vc.duration_minutes = int((vc.actual_end - vc.actual_start).total_seconds() / 60)

    _audit(db, current_user, "UPDATE", "virtual_consultation", vc.id,
           f"Status: {vc.status}", request)
    db.commit()
    return {"id": vc.id, "message": "Consultation updated / อัปเดตสำเร็จ"}


# ══════════════════════════════════════════════════════════
# 3. REMINDERS / แจ้งเตือน
# ══════════════════════════════════════════════════════════

@router.post("/reminders")
async def create_reminder(
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Schedule a reminder for an appointment. / ตั้งแจ้งเตือนนัดหมาย"""
    from ..models.crm_models import AppointmentReminder
    body = await request.json()

    reminder = AppointmentReminder(
        id=str(uuid.uuid4()),
        appointment_id=body["appointment_id"],
        patient_id=body["patient_id"],
        channel=body["channel"],
        scheduled_at=body["scheduled_at"],
        trigger_offset=body.get("trigger_offset"),
        template_key=body.get("template_key"),
        message_en=body.get("message_en"),
        message_th=body.get("message_th"),
    )
    db.add(reminder)
    _audit(db, current_user, "CREATE", "reminder", reminder.id,
           f"Reminder {body['channel']} for appt {body['appointment_id']}", request)
    db.commit()

    return {"id": reminder.id, "message": "Reminder scheduled / ตั้งแจ้งเตือนสำเร็จ"}


@router.post("/reminders/bulk")
async def create_bulk_reminders(
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Create reminders for multiple channels/offsets at once. / ตั้งแจ้งเตือนหลายช่องทาง"""
    from ..models.crm_models import AppointmentReminder, Appointment
    body = await request.json()

    appt = db.query(Appointment).filter(Appointment.id == body["appointment_id"]).first()
    if not appt:
        raise HTTPException(404, "Appointment not found / ไม่พบนัดหมาย")

    appt_dt = datetime.combine(appt.appointment_date, appt.appointment_time)
    offset_map = {
        "1h": timedelta(hours=1), "2h": timedelta(hours=2),
        "24h": timedelta(hours=24), "48h": timedelta(hours=48),
        "7d": timedelta(days=7),
    }

    created = []
    for channel in body.get("channels", []):
        for offset_key in body.get("offsets", ["24h"]):
            offset = offset_map.get(offset_key, timedelta(hours=24))
            scheduled = appt_dt - offset

            reminder = AppointmentReminder(
                id=str(uuid.uuid4()),
                appointment_id=appt.id,
                patient_id=appt.patient_id,
                channel=channel,
                scheduled_at=scheduled,
                trigger_offset=offset_key,
                template_key=f"reminder_{offset_key}",
            )
            db.add(reminder)
            created.append({"channel": channel, "offset": offset_key,
                           "scheduled_at": scheduled.isoformat()})

    _audit(db, current_user, "CREATE", "bulk_reminders", appt.id,
           f"{len(created)} reminders for {appt.booking_number}", request)
    db.commit()

    return {"appointment_id": appt.id, "reminders_created": created,
            "total": len(created), "message": "Reminders created / ตั้งแจ้งเตือนสำเร็จ"}


@router.get("/reminders/pending")
async def list_pending_reminders(
    hours_ahead: int = Query(24, ge=1, le=168),
    channel: Optional[str] = None,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """List pending reminders due within N hours. / แจ้งเตือนที่รอส่ง"""
    from ..models.crm_models import AppointmentReminder

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=hours_ahead)

    q = db.query(AppointmentReminder).filter(
        AppointmentReminder.status == "pending",
        AppointmentReminder.scheduled_at <= cutoff,
        AppointmentReminder.scheduled_at >= now,
    )
    if channel:
        q = q.filter(AppointmentReminder.channel == channel)

    reminders = q.order_by(AppointmentReminder.scheduled_at.asc()).all()

    return {
        "reminders": [{
            "id": r.id, "appointment_id": r.appointment_id,
            "patient_id": r.patient_id,
            "channel": r.channel,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "template_key": r.template_key,
            "message_en": r.message_en, "message_th": r.message_th,
        } for r in reminders],
        "total": len(reminders),
    }


@router.post("/reminders/{reminder_id}/mark-sent")
async def mark_reminder_sent(
    reminder_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Mark reminder as sent. / บันทึกว่าส่งแจ้งเตือนแล้ว"""
    from ..models.crm_models import AppointmentReminder
    body = await request.json()

    reminder = db.query(AppointmentReminder).filter(AppointmentReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "Reminder not found / ไม่พบแจ้งเตือน")

    reminder.status = body.get("status", "sent")
    reminder.sent_at = datetime.now(timezone.utc)
    reminder.external_id = body.get("external_id")
    if body.get("status") == "failed":
        reminder.failure_reason = body.get("failure_reason")

    db.commit()
    return {"id": reminder.id, "status": reminder.status}


# ══════════════════════════════════════════════════════════
# 4. COMMUNICATION LOG / บันทึกการสื่อสาร
# ══════════════════════════════════════════════════════════

@router.post("/communications/send")
async def send_message(
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Send a message to patient (logs it, actual delivery via integration). / ส่งข้อความถึงผู้ป่วย"""
    from ..models.crm_models import CommunicationLog, PatientContactPreference
    body = await request.json()

    # Look up patient contact preference
    pref = db.query(PatientContactPreference).filter(
        PatientContactPreference.patient_id == body["patient_id"]
    ).first()

    log = CommunicationLog(
        id=str(uuid.uuid4()),
        patient_id=body["patient_id"],
        channel=body["channel"],
        direction="outbound",
        subject=body.get("subject"),
        message_en=body.get("message_en"),
        message_th=body.get("message_th"),
        template_key=body.get("template_key"),
        recipient=_get_recipient(pref, body["channel"]) if pref else body.get("recipient", ""),
        status="sent",
        reference_type=body.get("reference_type"),
        reference_id=body.get("reference_id"),
        sent_by=current_user.id,
    )
    db.add(log)
    _audit(db, current_user, "CREATE", "communication", log.id,
           f"Sent {body['channel']} to patient {body['patient_id']}", request)
    db.commit()

    return {
        "id": log.id, "channel": log.channel,
        "status": "sent",
        "message": "Message sent / ส่งข้อความสำเร็จ",
        "note": "Integration with SMS/LINE/WhatsApp/Email gateway required for actual delivery / ต้องเชื่อมต่อกับ gateway จริงเพื่อส่ง",
    }


def _get_recipient(pref, channel):
    m = {
        "sms": pref.phone_primary,
        "line": pref.line_id,
        "email": pref.email,
        "whatsapp": pref.whatsapp_number,
        "phone_call": pref.phone_primary,
    }
    return m.get(channel, "")


@router.get("/communications")
async def list_communications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: Optional[str] = None,
    channel: Optional[str] = None,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """List communication logs. / แสดงบันทึกการสื่อสาร"""
    from ..models.crm_models import CommunicationLog

    q = db.query(CommunicationLog)
    if patient_id:
        q = q.filter(CommunicationLog.patient_id == patient_id)
    if channel:
        q = q.filter(CommunicationLog.channel == channel)

    total = q.count()
    logs = q.order_by(desc(CommunicationLog.created_at)).offset(
        (page - 1) * per_page).limit(per_page).all()

    return {
        "communications": [{
            "id": l.id, "patient_id": l.patient_id,
            "channel": l.channel, "direction": l.direction,
            "subject": l.subject,
            "message_th": l.message_th[:100] if l.message_th else None,
            "status": l.status, "template_key": l.template_key,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        } for l in logs],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ══════════════════════════════════════════════════════════
# 5. PATIENT CONTACT PREFERENCES / ช่องทางการติดต่อ
# ══════════════════════════════════════════════════════════

@router.get("/patients/{patient_id}/contact-preferences")
async def get_contact_preferences(
    patient_id: str,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Get patient contact preferences. / ข้อมูลช่องทางการติดต่อ"""
    from ..models.crm_models import PatientContactPreference
    pref = db.query(PatientContactPreference).filter(
        PatientContactPreference.patient_id == patient_id
    ).first()

    if not pref:
        return {"patient_id": patient_id, "preferences": None}

    return {
        "patient_id": patient_id,
        "preferences": {
            "phone_primary": pref.phone_primary,
            "phone_secondary": pref.phone_secondary,
            "email": pref.email,
            "line_id": pref.line_id,
            "whatsapp_number": pref.whatsapp_number,
            "preferred_channel": pref.preferred_channel,
            "preferred_language": pref.preferred_language,
            "preferred_time": pref.preferred_time,
            "consent_sms": pref.consent_sms,
            "consent_line": pref.consent_line,
            "consent_email": pref.consent_email,
            "consent_whatsapp": pref.consent_whatsapp,
            "consent_marketing": pref.consent_marketing,
        },
    }


@router.put("/patients/{patient_id}/contact-preferences")
async def upsert_contact_preferences(
    patient_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Create/update patient contact preferences. / บันทึกช่องทางการติดต่อ"""
    from ..models.crm_models import PatientContactPreference
    body = await request.json()

    pref = db.query(PatientContactPreference).filter(
        PatientContactPreference.patient_id == patient_id
    ).first()

    if not pref:
        pref = PatientContactPreference(id=str(uuid.uuid4()), patient_id=patient_id)
        db.add(pref)

    updatable = [
        "phone_primary", "phone_secondary", "email", "line_id", "whatsapp_number",
        "preferred_channel", "preferred_language", "preferred_time",
        "consent_sms", "consent_line", "consent_email", "consent_whatsapp", "consent_marketing",
    ]
    for field in updatable:
        if field in body:
            setattr(pref, field, body[field])

    _audit(db, current_user, "UPDATE", "contact_preferences", patient_id,
           f"Contact preferences updated", request)
    db.commit()
    return {"patient_id": patient_id, "message": "Preferences saved / บันทึกสำเร็จ"}


# ══════════════════════════════════════════════════════════
# 6. PROVIDER SCHEDULING / ตารางแพทย์
# ══════════════════════════════════════════════════════════

@router.get("/schedule/{provider_id}")
async def get_provider_schedule(
    provider_id: str,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Get provider's weekly schedule. / ตารางแพทย์"""
    from ..models.crm_models import ProviderSchedule, ScheduleException

    slots = db.query(ProviderSchedule).filter(
        ProviderSchedule.provider_id == provider_id,
        ProviderSchedule.is_active == True,
    ).order_by(ProviderSchedule.day_of_week, ProviderSchedule.start_time).all()

    today = date.today()
    exceptions = db.query(ScheduleException).filter(
        ScheduleException.provider_id == provider_id,
        ScheduleException.exception_date >= today,
    ).order_by(ScheduleException.exception_date).limit(30).all()

    return {
        "provider_id": provider_id,
        "weekly_schedule": [{
            "id": s.id, "day_of_week": s.day_of_week,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "slot_duration": s.slot_duration,
            "max_patients": s.max_patients,
            "appointment_types": s.appointment_types,
            "location": s.location,
        } for s in slots],
        "exceptions": [{
            "id": e.id, "date": e.exception_date.isoformat(),
            "type": e.exception_type,
            "reason": e.reason, "reason_th": e.reason_th,
        } for e in exceptions],
    }


@router.post("/schedule")
async def create_schedule_slot(
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "physician"])),
    db: Session = Depends(get_db),
):
    """Create provider schedule slot. / สร้างตารางแพทย์"""
    from ..models.crm_models import ProviderSchedule
    body = await request.json()

    slot = ProviderSchedule(
        id=str(uuid.uuid4()),
        provider_id=body["provider_id"],
        day_of_week=body["day_of_week"],
        start_time=body["start_time"],
        end_time=body["end_time"],
        slot_duration=body.get("slot_duration", 30),
        max_patients=body.get("max_patients", 1),
        appointment_types=body.get("appointment_types"),
        location=body.get("location"),
        effective_from=body.get("effective_from"),
        effective_until=body.get("effective_until"),
        notes=body.get("notes"),
    )
    db.add(slot)
    _audit(db, current_user, "CREATE", "schedule", slot.id,
           f"Schedule for provider {body['provider_id']} day {body['day_of_week']}", request)
    db.commit()
    return {"id": slot.id, "message": "Schedule created / สร้างตารางสำเร็จ"}


@router.post("/schedule/exception")
async def create_schedule_exception(
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "physician"])),
    db: Session = Depends(get_db),
):
    """Block off date or modify hours. / บล็อกวันหรือแก้ไขเวลา"""
    from ..models.crm_models import ScheduleException
    body = await request.json()

    exc = ScheduleException(
        id=str(uuid.uuid4()),
        provider_id=body["provider_id"],
        exception_date=body["exception_date"],
        exception_type=body["exception_type"],
        start_time=body.get("start_time"),
        end_time=body.get("end_time"),
        reason=body.get("reason"),
        reason_th=body.get("reason_th"),
        created_by=current_user.id,
    )
    db.add(exc)
    _audit(db, current_user, "CREATE", "schedule_exception", exc.id,
           f"Exception {body['exception_type']} on {body['exception_date']}", request)
    db.commit()
    return {"id": exc.id, "message": "Schedule exception created / บันทึกวันหยุดสำเร็จ"}


@router.get("/schedule/available-slots")
async def get_available_slots(
    provider_id: str,
    target_date: str,
    appointment_type: Optional[str] = None,
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """Get available booking slots for a provider on a date. / ช่วงเวลาว่าง"""
    from ..models.crm_models import ProviderSchedule, ScheduleException, Appointment

    target = date.fromisoformat(target_date)
    dow = target.weekday()

    # Check exceptions
    exc = db.query(ScheduleException).filter(
        ScheduleException.provider_id == provider_id,
        ScheduleException.exception_date == target,
        ScheduleException.exception_type == "day_off",
    ).first()
    if exc:
        return {"date": target_date, "available": False, "reason": "Day off / วันหยุด", "slots": []}

    # Get schedule for this day
    schedules = db.query(ProviderSchedule).filter(
        ProviderSchedule.provider_id == provider_id,
        ProviderSchedule.day_of_week == dow,
        ProviderSchedule.is_active == True,
    ).all()

    if not schedules:
        return {"date": target_date, "available": False, "reason": "No schedule / ไม่มีตาราง", "slots": []}

    # Get existing appointments
    existing = db.query(Appointment).filter(
        Appointment.provider_id == provider_id,
        Appointment.appointment_date == target,
        Appointment.status.notin_(["cancelled", "rescheduled", "no_show"]),
    ).all()
    booked_times = {a.appointment_time for a in existing}

    # Generate slots
    slots = []
    for sched in schedules:
        current = datetime.combine(target, sched.start_time)
        end = datetime.combine(target, sched.end_time)
        while current + timedelta(minutes=sched.slot_duration) <= end:
            t = current.time()
            is_available = t not in booked_times
            if appointment_type and sched.appointment_types:
                if appointment_type not in sched.appointment_types:
                    current += timedelta(minutes=sched.slot_duration)
                    continue
            slots.append({
                "time": t.isoformat(),
                "duration": sched.slot_duration,
                "available": is_available,
                "location": sched.location,
            })
            current += timedelta(minutes=sched.slot_duration)

    return {"date": target_date, "provider_id": provider_id,
            "available": any(s["available"] for s in slots), "slots": slots}


# ══════════════════════════════════════════════════════════
# 7. DASHBOARD / แดชบอร์ด
# ══════════════════════════════════════════════════════════

@router.get("/dashboard")
async def crm_dashboard(
    current_user: User = Depends(require_module_access("crm")),
    db: Session = Depends(get_db),
):
    """CRM Dashboard stats. / สถิติแดชบอร์ด CRM"""
    from ..models.crm_models import Appointment, VirtualConsultation, AppointmentReminder

    today = date.today()
    tomorrow = today + timedelta(days=1)

    today_appts = db.query(Appointment).filter(
        Appointment.appointment_date == today,
        Appointment.status.notin_(["cancelled", "rescheduled"]),
    ).count()
    tomorrow_appts = db.query(Appointment).filter(
        Appointment.appointment_date == tomorrow,
        Appointment.status.notin_(["cancelled", "rescheduled"]),
    ).count()
    checked_in = db.query(Appointment).filter(
        Appointment.appointment_date == today,
        Appointment.status == "checked_in",
    ).count()
    waiting_vc = db.query(VirtualConsultation).filter(
        VirtualConsultation.status.in_(["scheduled", "waiting"]),
        cast(VirtualConsultation.scheduled_start, Date) == today,
    ).count()
    pending_reminders = db.query(AppointmentReminder).filter(
        AppointmentReminder.status == "pending",
    ).count()
    no_shows_week = db.query(Appointment).filter(
        Appointment.status == "no_show",
        Appointment.appointment_date >= today - timedelta(days=7),
    ).count()

    # By type breakdown
    by_type = db.query(
        Appointment.appointment_type, func.count(Appointment.id)
    ).filter(
        Appointment.appointment_date == today,
        Appointment.status.notin_(["cancelled", "rescheduled"]),
    ).group_by(Appointment.appointment_type).all()

    # By source breakdown
    by_source = db.query(
        Appointment.booking_source, func.count(Appointment.id)
    ).filter(
        Appointment.appointment_date >= today - timedelta(days=30),
        Appointment.status.notin_(["cancelled"]),
    ).group_by(Appointment.booking_source).all()

    return {
        "today_appointments": today_appts,
        "tomorrow_appointments": tomorrow_appts,
        "checked_in_today": checked_in,
        "waiting_virtual": waiting_vc,
        "pending_reminders": pending_reminders,
        "no_shows_7d": no_shows_week,
        "today_by_type": [{"type": t[0], "count": t[1]} for t in by_type],
        "monthly_by_source": [{"source": s[0], "count": s[1]} for s in by_source],
        "today": today.isoformat(),
    }


# ── Translation endpoint ──────────────────────────────────
@router.get("/translations")
async def get_crm_translations():
    """Return CRM UI translations. / คืนค่าคำแปล"""
    from ..schemas.crm_schemas import (
        APPOINTMENT_TYPE_OPTIONS, APPOINTMENT_STATUS_OPTIONS,
        BOOKING_SOURCE_OPTIONS, CHANNEL_OPTIONS,
        REMINDER_TEMPLATE_OPTIONS, DEPARTMENT_OPTIONS,
        PLATFORM_OPTIONS, DAY_OF_WEEK_OPTIONS,
    )
    return {
        "appointment_types": APPOINTMENT_TYPE_OPTIONS,
        "appointment_statuses": APPOINTMENT_STATUS_OPTIONS,
        "booking_sources": BOOKING_SOURCE_OPTIONS,
        "channels": CHANNEL_OPTIONS,
        "reminder_templates": REMINDER_TEMPLATE_OPTIONS,
        "departments": DEPARTMENT_OPTIONS,
        "platforms": PLATFORM_OPTIONS,
        "days_of_week": DAY_OF_WEEK_OPTIONS,
    }
