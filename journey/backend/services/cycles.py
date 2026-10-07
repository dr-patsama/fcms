"""
Cycle spine services: create a cycle from a package, stimulation chart, publish plan,
monitoring, trigger, procedure scheduling (→ lab tasks), outcome, close.
All state changes emit domain events (events.py) which drive the other lanes.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient, FertilityHistory
from module2.backend.models.lab_models import TreatmentCycle
from module6.backend.models.crm_models import Appointment

from ..models.journey_models import (
    TreatmentPackage, CycleDay, CycleMedication, CycleMedicationDose, CycleMonitoring,
    CycleConsent, ConsentTemplate, CycleOutcome, LabTask,
)
from . import events
from .common import TZ, next_number, today, parse_date, parse_time, combine, add_days, now

APPOINTMENT_TYPE_FOR_ANCHOR = {
    "opu": ("egg_collection", "เก็บไข่", "operating_room"),
    "et": ("embryo_transfer", "ย้ายตัวอ่อน", "operating_room"),
    "iui": ("iui", "ฉีดเชื้อ IUI", "operating_room"),
    "procedure": ("procedure", "หัตถการ", "operating_room"),
    "collection": ("other", "เก็บน้ำเชื้อ", "andrology_lab"),
}

CYCLE_STATUSES = ["planned", "stimulating", "triggered", "procedure_scheduled", "lab_active",
                  "transferred", "frozen", "luteal", "outcome_pending", "closed", "cancelled"]


# ─────────────────────────────────────────────────────────────────────────────
# Lookups
# ─────────────────────────────────────────────────────────────────────────────
def get_cycle(db: Session, cycle_id: str) -> TreatmentCycle:
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == str(cycle_id)).first()
    if not c:
        raise HTTPException(404, "Cycle not found / ไม่พบรอบการรักษา")
    return c


def get_package(db: Session, package_id: str) -> TreatmentPackage:
    p = db.query(TreatmentPackage).filter(TreatmentPackage.id == str(package_id)).first()
    if not p:
        raise HTTPException(404, "Package not found")
    return p


def partner_of(db: Session, patient_id: str):
    fh = db.query(FertilityHistory).filter(FertilityHistory.patient_id == str(patient_id)).first()
    if fh and fh.partner_id:
        return db.query(Patient).filter(Patient.id == fh.partner_id).first()
    # reverse link
    fh2 = db.query(FertilityHistory).filter(FertilityHistory.partner_id == str(patient_id)).first()
    if fh2:
        return db.query(Patient).filter(Patient.id == fh2.patient_id).first()
    return None


def link_partner(db: Session, patient_id: str, partner_id: str | None):
    """Symmetric partner link stored on both fertility_histories (Binflux: 'bind spouse')."""
    for a, b in ((patient_id, partner_id), (partner_id, patient_id)):
        if not a:
            continue
        fh = db.query(FertilityHistory).filter(FertilityHistory.patient_id == str(a)).first()
        if not fh:
            fh = FertilityHistory(patient_id=str(a))
            db.add(fh)
        fh.partner_id = str(b) if b else None
    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Create cycle from package
# ─────────────────────────────────────────────────────────────────────────────
def create_cycle(db: Session, *, patient_id: str, package_id: str, physician_id: str | None,
                 medication_start_date=None, partner_id: str | None = None, physician_order: str | None = None,
                 notes: str | None = None, actor_id=None, timeline_id: str | None = None) -> TreatmentCycle:
    pkg = get_package(db, package_id)
    patient = db.query(Patient).filter(Patient.id == str(patient_id)).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    if partner_id:
        link_partner(db, patient_id, partner_id)
    partner = db.query(Patient).filter(Patient.id == partner_id).first() if partner_id else partner_of(db, patient_id)

    c = TreatmentCycle(
        id=str(uuid.uuid4()),
        cycle_number=next_number(db, TreatmentCycle, TreatmentCycle.cycle_number, "CYC"),
        patient_id=str(patient_id), partner_id=str(partner.id) if partner else None,
        cycle_type=pkg.cycle_type, package_id=str(pkg.id), physician_id=str(physician_id) if physician_id else None,
        status="planned", outcome="ongoing",
        medication_start_date=parse_date(medication_start_date),
        planned_et_day=pkg.default_et_day, pgt=bool(pkg.pgt), freeze_all=bool(pkg.freeze_all),
        physician_order=physician_order, notes=notes, created_by=str(actor_id) if actor_id else None,
        timeline_id=timeline_id,
        start_date=parse_date(medication_start_date) or today(),
    )
    db.add(c)
    db.flush()

    # stimulation chart pre-filled from the package template
    for i, m in enumerate(pkg.medication_template or []):
        db.add(CycleMedication(cycle_id=c.id, drug_code=m.get("drug_code"), drug_en=m["drug_en"], drug_th=m.get("drug_th"),
                               dose=m.get("dose"), unit=m.get("unit"), route=m.get("route"), slot=m.get("slot", "PM"),
                               start_day_index=int(m.get("start", 1)), end_day_index=int(m.get("end", m.get("start", 1))),
                               sort_order=i))
    # required consents
    templates = {t.code: t for t in db.query(ConsentTemplate).filter(ConsentTemplate.is_active == True).all()}
    for code in pkg.consents or []:
        t = templates.get(code)
        db.add(CycleConsent(cycle_id=c.id, patient_id=c.patient_id, consent_type=code,
                            template_id=t.id if t else None, template_version=t.version if t else None))
    db.flush()
    events.emit(db, "cycle.created", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"cycle_number": c.cycle_number, "package": pkg.code, "cycle_type": pkg.cycle_type,
                         "medication_start_date": str(c.medication_start_date) if c.medication_start_date else None})
    db.commit()
    db.refresh(c)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# Stimulation chart → publish plan (cycle_days + doses)
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_days(db: Session, c: TreatmentCycle, upto_index: int):
    if not c.medication_start_date:
        raise HTTPException(400, "Set medication_start_date before publishing the plan / กรุณาระบุวันเริ่มยา")
    existing = {d.day_index: d for d in db.query(CycleDay).filter(CycleDay.cycle_id == c.id).all()}
    for i in range(1, upto_index + 1):
        if i not in existing:
            d = CycleDay(cycle_id=c.id, calendar_date=add_days(c.medication_start_date, i - 1), day_index=i,
                         stimulation_day=i if not c.cycle_type.startswith("fet") else None)
            db.add(d)
            existing[i] = d
    db.flush()
    return existing


def publish_plan(db: Session, c: TreatmentCycle, actor_id=None, horizon_days: int = 16) -> dict:
    meds = db.query(CycleMedication).filter(CycleMedication.cycle_id == c.id).order_by(CycleMedication.sort_order).all()
    last = max([m.end_day_index for m in meds] + [horizon_days])
    days = _ensure_days(db, c, last)

    # (re)generate untaken doses; keep ones already ticked
    existing = db.query(CycleMedicationDose).filter(CycleMedicationDose.cycle_id == c.id).all()
    taken = {(d.medication_id, d.calendar_date, d.slot): d for d in existing if d.taken_at}
    for d in existing:
        if not d.taken_at:
            db.delete(d)
    db.flush()
    created = 0
    for m in meds:
        for i in range(m.start_day_index, m.end_day_index + 1):
            day = days[i]
            key = (m.id, day.calendar_date, m.slot)
            if key in taken:
                continue
            db.add(CycleMedicationDose(medication_id=m.id, cycle_id=c.id, calendar_date=day.calendar_date,
                                       day_index=i, slot=m.slot, dose=m.dose, unit=m.unit))
            created += 1
    first_published = not existing
    c.plan_published_at = now()
    if c.status == "planned":
        c.status = "stimulating"
    db.flush()
    events.emit(db, "plan.published" if first_published else "plan.updated", cycle_id=c.id, patient_id=c.patient_id,
                actor_id=actor_id, payload={"doses": created, "start": str(c.medication_start_date), "days": last})
    db.commit()
    return {"doses_created": created, "days": last}


# ─────────────────────────────────────────────────────────────────────────────
# Monitoring, trigger
# ─────────────────────────────────────────────────────────────────────────────
def record_monitoring(db: Session, c: TreatmentCycle, body: dict, actor_id=None) -> CycleMonitoring:
    d = parse_date(body.get("calendar_date")) or today()
    m = db.query(CycleMonitoring).filter(CycleMonitoring.cycle_id == c.id, CycleMonitoring.calendar_date == d).first()
    if not m:
        m = CycleMonitoring(cycle_id=c.id, calendar_date=d)
        db.add(m)
    if c.medication_start_date:
        m.day_index = (d - c.medication_start_date).days + 1
    for f in ("follicles_right", "follicles_left", "endometrium_mm", "endometrium_pattern", "e2", "lh", "p4", "fsh", "hcg",
              "orthanc_study_uid", "decision_en", "decision_th", "visit_id", "released_to_patient"):
        if f in body:
            setattr(m, f, body[f])
    m.recorded_by = str(actor_id) if actor_id else None
    db.flush()
    events.emit(db, "monitoring.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"date": str(d), "day_index": m.day_index,
                         "follicles": len(m.follicles_right or []) + len(m.follicles_left or []),
                         "e2": float(m.e2) if m.e2 is not None else None, "released": bool(m.released_to_patient)})
    if m.released_to_patient:
        events.emit(db, "results.released", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                    payload={"date": str(d), "kind": "monitoring"})
    db.commit()
    db.refresh(m)
    return m


def set_trigger(db: Session, c: TreatmentCycle, trigger_at: datetime, actor_id=None, drug: str | None = None) -> dict:
    if trigger_at.tzinfo is None:
        trigger_at = trigger_at.replace(tzinfo=TZ)
    c.trigger_at = trigger_at
    if c.status in ("planned", "stimulating"):
        c.status = "triggered"
    # trigger dose row on the chart (so the patient app shows it with the exact time)
    day_index = (trigger_at.date() - c.medication_start_date).days + 1 if c.medication_start_date else 1
    trig = db.query(CycleMedication).filter(CycleMedication.cycle_id == c.id, CycleMedication.drug_code == "TRIGGER").first()
    if not trig:
        trig = CycleMedication(cycle_id=c.id, drug_code="TRIGGER", drug_en=drug or "Trigger injection",
                               drug_th="ยากระตุ้นไข่สุก (trigger)", dose=1, unit="dose", route="SC",
                               start_day_index=day_index, end_day_index=day_index, sort_order=99)
        db.add(trig)
    trig.slot = trigger_at.astimezone(TZ).strftime("%H:%M")
    trig.start_day_index = trig.end_day_index = day_index
    if drug:
        trig.drug_en = drug
    db.flush()
    publish_plan(db, c, actor_id=actor_id)
    suggested_opu = trigger_at + timedelta(hours=36)
    events.emit(db, "trigger.set", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"trigger_at": trigger_at.isoformat(), "suggested_opu": suggested_opu.isoformat()})
    db.commit()
    return {"trigger_at": trigger_at.isoformat(), "suggested_opu": suggested_opu.isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# Procedure scheduling → appointment + lab day numbering + lab tasks
# ─────────────────────────────────────────────────────────────────────────────
def schedule_procedure(db: Session, c: TreatmentCycle, d0: date, at: time | None, actor_id=None,
                       room: str | None = None, physician_order: str | None = None) -> dict:
    from .lab_tasks import generate_tasks  # local import to avoid cycle
    pkg = get_package(db, c.package_id) if c.package_id else None
    anchor = pkg.anchor if pkg else "opu"
    appt_type, appt_type_th, dept = APPOINTMENT_TYPE_FOR_ANCHOR.get(anchor, APPOINTMENT_TYPE_FOR_ANCHOR["procedure"])

    rescheduled = c.d0_date is not None and c.d0_date != d0
    c.d0_date = d0
    if physician_order is not None:
        c.physician_order = physician_order
    c.status = "procedure_scheduled"

    # appointment (Module 6) for the procedure — reuse the existing one if any
    appt = db.query(Appointment).filter(Appointment.cycle_id == c.id, Appointment.appointment_type == appt_type,
                                        Appointment.status.in_(("scheduled", "confirmed"))).first()
    t = at or time(8, 0)
    if appt:
        appt.appointment_date, appt.appointment_time = d0, t
    else:
        appt = Appointment(id=str(uuid.uuid4()), booking_number=_next_booking_number(db), patient_id=c.patient_id,
                           appointment_date=d0, appointment_time=t, duration_minutes=60, appointment_type=appt_type,
                           appointment_type_th=appt_type_th, department=dept, room=room, provider_id=c.physician_id,
                           status="scheduled", booking_source="staff", cycle_id=c.id, created_by=str(actor_id) if actor_id else None,
                           notes=f"{c.cycle_number} · {pkg.name_en if pkg else c.cycle_type}")
        db.add(appt)
    db.flush()

    # lab-day numbering on cycle_days (D0 = d0)
    if c.medication_start_date:
        last_index = max((d0 - c.medication_start_date).days + 1 + 7, 1)
        days = _ensure_days(db, c, last_index)
        for d in days.values():
            delta = (d.calendar_date - d0).days
            d.lab_day = delta if 0 <= delta <= 7 else None
            if delta == 0:
                d.is_procedure = True
                d.label_en = appt_type.replace("_", " ").title()
                d.label_th = appt_type_th
                d.appointment_id = appt.id
    tasks = generate_tasks(db, c, pkg, d0, actor_id=actor_id)
    events.emit(db, "procedure.rescheduled" if rescheduled else "procedure.scheduled", cycle_id=c.id, patient_id=c.patient_id,
                actor_id=actor_id, payload={"anchor": anchor, "d0": str(d0), "time": t.strftime("%H:%M"),
                                            "appointment_id": appt.id, "appointment_type": appt_type, "tasks": len(tasks)})
    db.commit()
    return {"appointment_id": appt.id, "d0": str(d0), "tasks_generated": len(tasks)}


def _next_booking_number(db: Session) -> str:
    return next_number(db, Appointment, Appointment.booking_number, "BK", width=5)


# ─────────────────────────────────────────────────────────────────────────────
# Outcome & close
# ─────────────────────────────────────────────────────────────────────────────
def record_outcome(db: Session, c: TreatmentCycle, body: dict, actor_id=None) -> CycleOutcome:
    o = db.query(CycleOutcome).filter(CycleOutcome.cycle_id == c.id).first()
    if not o:
        o = CycleOutcome(cycle_id=c.id, patient_id=c.patient_id)
        db.add(o)
    for f in ("cancelled_before_opu", "cancel_reason", "hcg_date", "hcg_value", "hcg_positive", "biochemical_only",
              "clinical_pregnancy", "gestational_sacs", "fetal_hearts", "ongoing_pregnancy", "miscarriage", "ectopic",
              "live_birth", "delivery_date", "babies", "birth_details", "ohss_grade", "opu_complication", "notes"):
        if f in body:
            v = body[f]
            if f in ("hcg_date", "delivery_date"):
                v = parse_date(v)
            setattr(o, f, v)
    o.recorded_by = str(actor_id) if actor_id else None
    # mirror the Module 2 summary field
    if o.cancelled_before_opu:
        c.outcome, c.status = "cancelled", "cancelled"
    elif o.live_birth:
        c.outcome = "live_birth"
    elif o.clinical_pregnancy or o.hcg_positive:
        c.outcome = "pregnant"
    elif o.hcg_positive is False:
        c.outcome = "failed"
    if c.status not in ("closed", "cancelled"):
        c.status = "outcome_pending" if o.hcg_positive is None else c.status
    db.flush()
    events.emit(db, "outcome.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"hcg_positive": o.hcg_positive, "clinical_pregnancy": o.clinical_pregnancy,
                         "live_birth": o.live_birth, "cancelled_before_opu": o.cancelled_before_opu})
    db.commit()
    db.refresh(o)
    return o


def close_cycle(db: Session, c: TreatmentCycle, reason: str | None, actor_id=None) -> TreatmentCycle:
    c.status = "closed"
    c.closed_at = now()
    c.closure_reason = reason
    c.end_date = today()
    events.emit(db, "cycle.closed", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id, payload={"reason": reason})
    db.commit()
    return c


def cancel_cycle(db: Session, c: TreatmentCycle, reason: str | None, actor_id=None) -> TreatmentCycle:
    c.status = "cancelled"
    c.outcome = "cancelled"
    c.closed_at = now()
    c.closure_reason = reason
    c.end_date = today()
    # drop pending lab tasks and cancel linked appointments
    db.query(LabTask).filter(LabTask.cycle_id == c.id, LabTask.status == "pending").delete(synchronize_session=False)
    for a in db.query(Appointment).filter(Appointment.cycle_id == c.id, Appointment.status.in_(("scheduled", "confirmed"))).all():
        a.status = "cancelled"
        a.cancel_reason = f"Cycle cancelled: {reason or ''}"
        a.cancelled_at = now()
    events.emit(db, "cycle.closed", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"reason": reason, "cancelled": True})
    db.commit()
    return c
