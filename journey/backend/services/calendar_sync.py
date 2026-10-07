"""
Google Calendar mirror for appointments (Module 6) and cycle procedures.

Setup (one-time, see journey/README.md):
  1. Google Cloud project → enable "Google Calendar API".
  2. Create a service account, download its JSON key → GOOGLE_SERVICE_ACCOUNT_JSON=/path/key.json
  3. In Google Calendar, share the clinic calendar with the service-account e-mail
     ("Make changes to events") → GOOGLE_CALENDAR_ID=<calendar id>
  4. Optional: GOOGLE_CALENDAR_PROCEDURES_ID for OPU/ET/OR on a second calendar.

Direction: FCMS → Google (FCMS is the source of truth; edits in Google are not pulled back,
except `import_busy()` which turns Google events that FCMS does not know about into
Module 6 schedule_exceptions so the slot search avoids them).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module1.backend.models.user_models import User
from module6.backend.models.crm_models import Appointment, ScheduleException

from ..core.config import jsettings
from .common import TZ, now, combine, patient_name

log = logging.getLogger("fcms.journey.gcal")

PROCEDURE_TYPES = {"egg_collection", "embryo_transfer", "iui", "hysteroscopy", "prp", "procedure"}
TYPE_LABEL = {
    "new_patient": "New patient", "follow_up": "Follow-up", "consultation": "Consultation", "ultrasound": "Ultrasound",
    "blood_test": "Blood test", "egg_collection": "OPU", "embryo_transfer": "Embryo transfer", "iui": "IUI",
    "virtual_consultation": "Virtual consultation", "hysteroscopy": "Hysteroscopy", "prp": "PRP", "procedure": "Procedure",
    "other": "Visit",
}
COLOR = {"egg_collection": "11", "embryo_transfer": "10", "iui": "9", "virtual_consultation": "7", "ultrasound": "5"}  # Google colorId


def enabled() -> bool:
    return jsettings.google_calendar_enabled


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    scopes = ["https://www.googleapis.com/auth/calendar"]
    creds = service_account.Credentials.from_service_account_file(jsettings.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=scopes)
    if jsettings.GOOGLE_IMPERSONATE_USER:
        creds = creds.with_subject(jsettings.GOOGLE_IMPERSONATE_USER)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _calendar_for(appt: Appointment) -> str:
    if appt.appointment_type in PROCEDURE_TYPES and jsettings.GOOGLE_CALENDAR_PROCEDURES_ID:
        return jsettings.GOOGLE_CALENDAR_PROCEDURES_ID
    return jsettings.GOOGLE_CALENDAR_ID


def event_body(db: Session, appt: Appointment) -> dict:
    p = db.query(Patient).filter(Patient.id == appt.patient_id).first()
    prov = db.query(User).filter(User.id == appt.provider_id).first() if appt.provider_id else None
    start = combine(appt.appointment_date, appt.appointment_time)
    end = combine(appt.appointment_date, appt.end_time) if appt.end_time else start + timedelta(minutes=appt.duration_minutes or 30)
    label = TYPE_LABEL.get(appt.appointment_type, appt.appointment_type)
    # Minimal PHI in the calendar title: type + HN + first name only (PDPA)
    title = f"{label} · {p.hn_number if p else ''} {p.first_name_en if p else ''}".strip()
    desc_lines = [
        f"Booking {appt.booking_number}", f"Patient: {patient_name(p)} ({p.hn_number})" if p else "",
        f"Provider: {prov.first_name_en} {prov.last_name_en}" if prov else "",
        f"Room: {appt.room}" if appt.room else "", f"Status: {appt.status}",
        f"Notes: {appt.notes}" if appt.notes else "", "— FCMS · LIFE by Dr. Pat",
    ]
    body = {
        "summary": title,
        "description": "\n".join(l for l in desc_lines if l),
        "start": {"dateTime": start.isoformat(), "timeZone": jsettings.CLINIC_TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": jsettings.CLINIC_TIMEZONE},
        "location": appt.room or jsettings.CLINIC_NAME_EN,
        "extendedProperties": {"private": {"fcms_appointment_id": str(appt.id), "fcms_booking": appt.booking_number or ""}},
        "reminders": {"useDefault": True},
    }
    if appt.appointment_type in COLOR:
        body["colorId"] = COLOR[appt.appointment_type]
    return body


def sync_appointment(db: Session, appt: Appointment) -> str:
    """Create / update / delete the mirrored Google event. Returns a status string."""
    if not enabled():
        return "skipped: Google Calendar not configured"
    svc = _service()
    cal = _calendar_for(appt)
    try:
        if appt.status in ("cancelled", "rescheduled", "no_show"):
            if appt.google_event_id:
                try:
                    svc.events().delete(calendarId=cal, eventId=appt.google_event_id).execute()
                except Exception as e:  # already gone
                    log.info("gcal delete: %s", e)
                appt.google_event_id = None
                appt.google_synced_at = now()
            return "deleted"
        body = event_body(db, appt)
        if appt.google_event_id:
            svc.events().patch(calendarId=cal, eventId=appt.google_event_id, body=body).execute()
            appt.google_synced_at = now()
            return "updated"
        ev = svc.events().insert(calendarId=cal, body=body).execute()
        appt.google_event_id = ev.get("id")
        appt.google_synced_at = now()
        return "created"
    except Exception as e:
        log.exception("gcal sync failed")
        return f"error: {type(e).__name__}: {str(e)[:160]}"


def sync_all(db: Session, since: date | None = None, limit: int = 500) -> dict:
    since = since or now().date()
    q = db.query(Appointment).filter(Appointment.appointment_date >= since).order_by(Appointment.appointment_date).limit(limit)
    out = {"created": 0, "updated": 0, "deleted": 0, "errors": 0, "skipped": 0}
    for a in q.all():
        r = sync_appointment(db, a)
        key = r.split(":")[0]
        out[key if key in out else ("errors" if key == "error" else "skipped")] += 1
    db.commit()
    return out


def import_busy(db: Session, days_ahead: int = 60, provider_id: str | None = None) -> int:
    """Pull Google events FCMS did not create → schedule_exceptions (blocks) so slot search avoids them."""
    if not enabled():
        return 0
    svc = _service()
    t0 = now()
    t1 = t0 + timedelta(days=days_ahead)
    res = svc.events().list(calendarId=jsettings.GOOGLE_CALENDAR_ID, timeMin=t0.isoformat(), timeMax=t1.isoformat(),
                            singleEvents=True, orderBy="startTime", maxResults=500).execute()
    count = 0
    phys = provider_id or (db.query(User).filter(User.role == "physician", User.is_active == True).first() or User()).id
    if not phys:
        return 0
    for ev in res.get("items", []):
        priv = (ev.get("extendedProperties") or {}).get("private") or {}
        if priv.get("fcms_appointment_id"):
            continue  # ours
        st, en = ev.get("start", {}), ev.get("end", {})
        if "dateTime" not in st:
            continue  # all-day events are not blocks
        s = datetime.fromisoformat(st["dateTime"]).astimezone(TZ)
        e = datetime.fromisoformat(en["dateTime"]).astimezone(TZ)
        exists = db.query(ScheduleException).filter(ScheduleException.provider_id == str(phys),
                                                    ScheduleException.exception_date == s.date(),
                                                    ScheduleException.reason == f"gcal:{ev.get('id')}").first()
        if exists:
            continue
        db.add(ScheduleException(provider_id=str(phys), exception_date=s.date(), exception_type="reduced_hours",
                                 start_time=s.time(), end_time=e.time(), reason=f"gcal:{ev.get('id')}",
                                 reason_th=ev.get("summary", "Google Calendar")))
        count += 1
    db.commit()
    return count
