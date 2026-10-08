"""
Lab To-Do: tasks generated from the package's lab-event template when the procedure is
scheduled (Binflux EWS: "orders auto-create the daily to-do events"). Consent gating, done/failed,
and the labelled items each task needs.
"""
from __future__ import annotations

from datetime import date, time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module1.backend.models.user_models import User
from module2.backend.models.lab_models import TreatmentCycle

from ..models.journey_models import TreatmentPackage, LabTask, LabItem, CycleConsent
from . import events
from .common import add_days, parse_time, now, new_label_code, patient_name, row

# which items belong to the partner (male) rather than the cycle's patient
PARTNER_ITEMS = {"sperm_tube", "prep_tube"}
PARTNER_TASKS = {"sperm_collection", "sperm_prep", "semen_analysis", "sperm_freeze"}


def generate_tasks(db: Session, c: TreatmentCycle, pkg: TreatmentPackage | None, d0: date, actor_id=None) -> list[LabTask]:
    """Regenerate pending tasks for the cycle from the package template; keep done/failed ones."""
    if not pkg:
        return []
    db.query(LabTask).filter(LabTask.cycle_id == c.id, LabTask.status == "pending").delete(synchronize_session=False)
    kept = {(t.key, t.lab_day) for t in db.query(LabTask).filter(LabTask.cycle_id == c.id).all()}
    out = []
    for i, e in enumerate(pkg.lab_events or []):
        key, day = e["key"], int(e.get("day", 0))
        if (key, day) in kept:
            continue
        # fresh ET day follows the cycle's planned_et_day when set
        if key == "et" and c.planned_et_day is not None and pkg.anchor == "opu":
            day = int(c.planned_et_day)
        t = LabTask(
            cycle_id=c.id, patient_id=c.partner_id if (key in PARTNER_TASKS and c.partner_id) else c.patient_id,
            key=key, task_type=e.get("type", key), title_en=e.get("title_en", key), title_th=e.get("title_th"),
            lab_day=day, scheduled_date=add_days(d0, day), scheduled_time=parse_time(e.get("time")),
            sort_order=i, requires_witness=bool(e.get("requires_witness")), items_required=e.get("items") or [],
            write_back=e.get("write_back"), required_consents=e.get("consents") or [],
            physician_order=c.physician_order, status="pending",
            notes="optional" if e.get("optional") else None,
        )
        db.add(t)
        out.append(t)
    db.flush()
    for t in out:
        ensure_items(db, c, t)
    events.emit(db, "lab.task.generated", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id,
                payload={"count": len(out), "d0": str(d0)})
    return out


def ensure_items(db: Session, c: TreatmentCycle, t: LabTask) -> list[LabItem]:
    """One labelled item per required type per cycle (culture dish is shared across days)."""
    items = []
    for item_type in t.items_required or []:
        owner = c.partner_id if (item_type in PARTNER_ITEMS and c.partner_id) else c.patient_id
        if item_type == "wristband" and t.key in PARTNER_TASKS and c.partner_id:
            owner = c.partner_id
        q = db.query(LabItem).filter(LabItem.cycle_id == c.id, LabItem.item_type == item_type,
                                     LabItem.patient_id == owner, LabItem.is_active == True)
        # cryo devices are per freezing event, not shared
        if item_type == "cryo_device":
            q = q.filter(LabItem.lab_day == t.lab_day)
        it = q.first()
        if not it:
            it = LabItem(label_code=new_label_code(), cycle_id=c.id, patient_id=owner, item_type=item_type,
                         lab_day=t.lab_day, description=f"{item_type.replace('_', ' ')} · {c.cycle_number}", lab_task_id=t.id)
            db.add(it)
        items.append(it)
    db.flush()
    return items


def consent_block(db: Session, t: LabTask) -> list[str]:
    """Return the consent codes still unsigned for this task (empty → not blocked)."""
    if not t.required_consents:
        return []
    signed = {cc.consent_type for cc in db.query(CycleConsent).filter(CycleConsent.cycle_id == t.cycle_id,
                                                                     CycleConsent.status == "signed").all()}
    return [c for c in t.required_consents if c not in signed]


# roles that can be assigned a lab step (shown in the assignee picker)
ASSIGNABLE_ROLES = ("embryologist", "lab_supervisor", "lab_technician", "nurse", "physician")


def staff_name(u: User | None, lang: str = "en") -> str | None:
    if not u:
        return None
    if lang == "th" and (u.first_name_th or u.last_name_th):
        return f"{u.first_name_th or ''} {u.last_name_th or ''}".strip()
    return f"{u.first_name_en} {u.last_name_en}".strip()


def staff_view(u: User) -> dict:
    return {"id": str(u.id), "name_en": staff_name(u, "en"), "name_th": staff_name(u, "th"), "role": u.role,
            "initials": "".join(x[0] for x in (u.first_name_en, u.last_name_en) if x).upper()}


def assignable_staff(db: Session) -> list[dict]:
    us = db.query(User).filter(User.is_active.is_(True), User.role.in_(ASSIGNABLE_ROLES)).order_by(User.role, User.first_name_en).all()
    return [staff_view(u) for u in us]


def task_view(db: Session, t: LabTask, c: TreatmentCycle | None = None, patients: dict | None = None, users: dict | None = None) -> dict:
    d = row(t)
    c = c or db.query(TreatmentCycle).filter(TreatmentCycle.id == t.cycle_id).first()
    patients = patients or {}
    users = users or {}
    p = patients.get(str(c.patient_id)) or db.query(Patient).filter(Patient.id == c.patient_id).first()
    partner = patients.get(str(c.partner_id)) or (db.query(Patient).filter(Patient.id == c.partner_id).first() if c.partner_id else None)
    a = (users.get(str(t.assigned_to)) or db.query(User).filter(User.id == t.assigned_to).first()) if t.assigned_to else None
    blocked = consent_block(db, t)
    d.update({
        "cycle_number": c.cycle_number, "cycle_type": c.cycle_type, "cycle_status": c.status,
        "hn": p.hn_number if p else None, "patient_en": patient_name(p, "en"), "patient_th": patient_name(p, "th"),
        "partner_hn": partner.hn_number if partner else None, "partner_en": patient_name(partner, "en") if partner else None,
        "dob": str(p.date_of_birth) if p and p.date_of_birth else None,
        "blocked_by_consent": blocked, "effective_status": "blocked" if (blocked and t.status == "pending") else t.status,
        "assignee": staff_view(a) if a else None,
    })
    return d


def assign(db: Session, t: LabTask, user_id: str | None, actor_id) -> LabTask:
    """Assign (or unassign with user_id=None) the staff member responsible for this step."""
    if user_id:
        u = db.query(User).filter(User.id == user_id).first()
        if not u or not u.is_active:
            raise HTTPException(404, "Staff member not found / ไม่พบเจ้าหน้าที่")
        if u.role not in ASSIGNABLE_ROLES and u.role not in ("admin", "it_admin"):
            raise HTTPException(400, f"Role {u.role} cannot be assigned lab steps")
        t.assigned_to, t.assigned_at, t.assigned_by = str(u.id), now(), str(actor_id) if actor_id else None
    else:
        t.assigned_to, t.assigned_at, t.assigned_by = None, None, None
    db.flush()
    events.emit(db, "lab.task.assigned", cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id,
                payload={"task_id": t.id, "key": t.key, "lab_day": t.lab_day, "assigned_to": t.assigned_to})
    return t


def mark_done(db: Session, t: LabTask, actor_id, *, via: str = "manual", notes: str | None = None) -> LabTask:
    if t.status == "done":
        return t
    blocked = consent_block(db, t)
    if blocked:
        raise HTTPException(409, f"Blocked by unsigned consent: {', '.join(blocked)} / ยังไม่ได้ลงนามยินยอม")
    if t.requires_witness and via == "manual":
        raise HTTPException(409, "This step requires witnessing (scan or manual double-witness) / ขั้นตอนนี้ต้องมีพยาน")
    t.status, t.done_at, t.done_by = "done", now(), str(actor_id) if actor_id else None
    if notes:
        t.notes = (t.notes + "\n" if t.notes else "") + notes
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == t.cycle_id).first()
    if c and c.status in ("procedure_scheduled", "triggered") and t.lab_day == 0:
        c.status = "lab_active"
    if t.key == "et":
        c.status = "transferred"
    db.flush()
    events.emit(db, "lab.task.done", cycle_id=t.cycle_id, patient_id=c.patient_id if c else None, actor_id=actor_id,
                payload={"task_id": t.id, "key": t.key, "lab_day": t.lab_day, "via": via})
    return t


def mark_failed(db: Session, t: LabTask, actor_id, reason: str) -> LabTask:
    t.status, t.failed_reason, t.done_by, t.done_at = "failed", reason, str(actor_id) if actor_id else None, now()
    db.flush()
    events.emit(db, "lab.task.failed", cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id,
                payload={"task_id": t.id, "key": t.key, "lab_day": t.lab_day, "reason": reason})
    return t


def add_task(db: Session, c: TreatmentCycle, body: dict, actor_id=None) -> LabTask:
    """Ad-hoc task added by the lab (e.g. an extra Day-6 vitrification)."""
    from .packages import LAB_EVENT_TYPES
    key = body.get("key") or "procedure"
    t_en, t_th, items, wb = LAB_EVENT_TYPES.get(key, ("Task", "งาน", ["wristband"], None))
    t = LabTask(cycle_id=c.id, patient_id=c.partner_id if (key in PARTNER_TASKS and c.partner_id) else c.patient_id,
                key=key, task_type=key, title_en=body.get("title_en") or t_en, title_th=body.get("title_th") or t_th,
                lab_day=body.get("lab_day"), scheduled_date=body.get("scheduled_date") or now().date(),
                scheduled_time=parse_time(body.get("scheduled_time")), requires_witness=bool(body.get("requires_witness", True)),
                items_required=body.get("items") or items, write_back=wb, required_consents=body.get("consents") or [],
                physician_order=c.physician_order, sort_order=50)
    db.add(t)
    db.flush()
    ensure_items(db, c, t)
    events.emit(db, "lab.task.generated", cycle_id=c.id, patient_id=c.patient_id, actor_id=actor_id, payload={"count": 1, "adhoc": key})
    return t
