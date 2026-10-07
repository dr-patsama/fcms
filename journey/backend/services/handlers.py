"""
Event handlers — the glue that makes the Binflux-style handoffs automatic.
Imported once by the API package so the @on registrations run.

  cycle.created        → consent.pending notification to the patient
  plan.published/updated → patient notification + dose reminders scheduled (one per dose, at slot time)
  trigger.set          → trigger-time push
  procedure.scheduled  → patient push with instructions + Google Calendar mirror of the appointment
  visit.booked / rescheduled / cancelled (from Module 6 hook) → patient push + Google Calendar
  queue.called         → patient push
  results.released / album.released / outcome.recorded → patient push
  lab.task.done (vitrification) → cryo storage terms synced
  consent.signed       → nothing to push; the lab board unblocks automatically
"""
from __future__ import annotations

from datetime import datetime, time

from sqlalchemy.orm import Session

from module2.backend.models.lab_models import TreatmentCycle
from module6.backend.models.crm_models import Appointment

from ..models.journey_models import CycleEvent, CycleMedicationDose, CycleMedication, PatientNotification
from . import notifications, calendar_sync, cryo
from .events import on
from .common import TZ, now

SLOT_TIME = {"AM": time(8, 0), "NOON": time(12, 0), "PM": time(20, 0), "HS": time(21, 0)}


def _slot_dt(d, slot: str | None) -> datetime:
    if slot and ":" in slot:
        h, m = slot.split(":")[:2]
        t = time(int(h), int(m))
    else:
        t = SLOT_TIME.get((slot or "PM").upper(), time(20, 0))
    return datetime.combine(d, t, TZ)


@on("cycle.created")
def h_cycle_created(db: Session, ev: CycleEvent):
    notifications.notify(db, ev.patient_id, "consent.pending", {"cycle": ev.payload.get("cycle_number")}, cycle_id=ev.cycle_id)
    return "consent.pending sent"


@on("plan.published", "plan.updated")
def h_plan(db: Session, ev: CycleEvent):
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == ev.cycle_id).first()
    notifications.notify(db, ev.patient_id, ev.type, {"cycle": c.cycle_number, "date": ev.payload.get("start")}, cycle_id=ev.cycle_id)
    # (re)schedule dose reminders: drop unsent future reminders, create one per future dose 15 min before slot
    db.query(PatientNotification).filter(PatientNotification.cycle_id == ev.cycle_id, PatientNotification.type == "dose.reminder",
                                         PatientNotification.sent_at == None).delete(synchronize_session=False)
    meds = {m.id: m for m in db.query(CycleMedication).filter(CycleMedication.cycle_id == ev.cycle_id).all()}
    n = 0
    for d in db.query(CycleMedicationDose).filter(CycleMedicationDose.cycle_id == ev.cycle_id, CycleMedicationDose.taken_at == None).all():
        at = _slot_dt(d.calendar_date, d.slot)
        if at < now():
            continue
        m = meds.get(d.medication_id)
        notifications.notify(db, ev.patient_id, "dose.reminder",
                             {"drug": m.drug_en if m else "", "dose": float(d.dose) if d.dose is not None else "", "unit": d.unit or ""},
                             cycle_id=ev.cycle_id, scheduled_for=at, deliver=False)
        n += 1
    return f"plan push + {n} dose reminders scheduled"


@on("trigger.set")
def h_trigger(db: Session, ev: CycleEvent):
    t = datetime.fromisoformat(ev.payload["trigger_at"]).astimezone(TZ)
    notifications.notify(db, ev.patient_id, "trigger.set", {"date": t.strftime("%d/%m/%Y"), "time": t.strftime("%H:%M")}, cycle_id=ev.cycle_id)
    return "trigger push sent"


@on("procedure.scheduled", "procedure.rescheduled")
def h_procedure(db: Session, ev: CycleEvent):
    appt = db.query(Appointment).filter(Appointment.id == ev.payload.get("appointment_id")).first()
    instructions = (appt.preparation_instructions_th or appt.preparation_instructions or "") if appt else ""
    notifications.notify(db, ev.patient_id, ev.type, {"date": ev.payload.get("d0"), "time": ev.payload.get("time"), "instructions": instructions},
                         cycle_id=ev.cycle_id)
    g = calendar_sync.sync_appointment(db, appt) if appt else "no appointment"
    return f"push sent; gcal: {g}"


@on("visit.booked", "visit.rescheduled")
def h_visit(db: Session, ev: CycleEvent):
    appt = db.query(Appointment).filter(Appointment.id == ev.payload.get("appointment_id")).first()
    if not appt:
        return "no appointment"
    notifications.notify(db, ev.patient_id, "visit.booked", {"date": str(appt.appointment_date), "time": appt.appointment_time.strftime("%H:%M")},
                         cycle_id=ev.cycle_id)
    # visit reminder the day before at 18:00
    remind_at = datetime.combine(appt.appointment_date, time(18, 0), TZ) - __import__("datetime").timedelta(days=1)
    if remind_at > now():
        notifications.notify(db, ev.patient_id, "visit.reminder", {"date": str(appt.appointment_date), "time": appt.appointment_time.strftime("%H:%M")},
                             cycle_id=ev.cycle_id, scheduled_for=remind_at, deliver=False)
    return f"push sent; gcal: {calendar_sync.sync_appointment(db, appt)}"


@on("visit.cancelled")
def h_visit_cancelled(db: Session, ev: CycleEvent):
    appt = db.query(Appointment).filter(Appointment.id == ev.payload.get("appointment_id")).first()
    if not appt:
        return "no appointment"
    db.query(PatientNotification).filter(PatientNotification.type == "visit.reminder", PatientNotification.sent_at == None,
                                         PatientNotification.patient_id == appt.patient_id).delete(synchronize_session=False)
    return f"gcal: {calendar_sync.sync_appointment(db, appt)}"


@on("queue.called")
def h_queue(db: Session, ev: CycleEvent):
    notifications.notify(db, ev.patient_id, "queue.called", {"queue": ev.payload.get("queue")}, channels=["line"])
    return "queue push sent"


@on("results.released", "album.released", "outcome.recorded")
def h_release(db: Session, ev: CycleEvent):
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == ev.cycle_id).first()
    notifications.notify(db, ev.patient_id, ev.type, {"cycle": c.cycle_number if c else ""}, cycle_id=ev.cycle_id)
    return "push sent"


@on("lab.task.done")
def h_task_done(db: Session, ev: CycleEvent):
    if ev.payload.get("key") in ("vitrification", "oocyte_vitrification", "sperm_freeze"):
        c = db.query(TreatmentCycle).filter(TreatmentCycle.id == ev.cycle_id).first()
        terms = cryo.sync_terms_from_lab(db, c)
        return f"{len(terms)} storage term(s) opened"
    return "ok"
