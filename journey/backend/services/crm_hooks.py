"""
Hooks called from Module 6 (CRM) appointment endpoints so bookings made at the front desk flow into
the journey layer: patient push, visit reminder, Google Calendar mirror, queue numbers.
Each call is wrapped in try/except by the caller — the CRM endpoint never fails because of these.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from module6.backend.models.crm_models import Appointment

from . import events


def on_appointment(db: Session, appt: Appointment, action: str, actor_id=None):
    """action: created | updated | cancelled | rescheduled | checked_in | called"""
    t = {"created": "visit.booked", "rescheduled": "visit.rescheduled", "updated": "visit.rescheduled",
         "cancelled": "visit.cancelled", "checked_in": "visit.checked_in", "called": "queue.called"}.get(action)
    if not t:
        return None
    db.flush()
    db.refresh(appt)   # CRM routes assign raw request strings; reload so dates/times are typed
    payload = {"appointment_id": str(appt.id), "booking_number": appt.booking_number, "type": appt.appointment_type,
               "date": str(appt.appointment_date), "time": appt.appointment_time.strftime("%H:%M") if appt.appointment_time else None,
               "queue": appt.queue_number}
    return events.emit(db, t, cycle_id=appt.cycle_id, patient_id=appt.patient_id, payload=payload, actor_id=actor_id)


def assign_queue_number(db: Session, appt: Appointment) -> int:
    """Next queue number for the day (per department) at check-in."""
    if appt.queue_number:
        return appt.queue_number
    mx = db.query(func.max(Appointment.queue_number)).filter(Appointment.appointment_date == appt.appointment_date).scalar() or 0
    appt.queue_number = int(mx) + 1
    db.flush()
    return appt.queue_number
