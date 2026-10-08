"""
FCMS Journey layer — staff API (/api/v1/journey)
Packages · cycles (spine) · stimulation chart · monitoring · trigger · procedure scheduling ·
lab tasks · labels · witnessing · observation · photos · consents · outcome · report · cryo ·
notifications · Google Calendar · KPIs · jobs
"""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import Response, FileResponse, StreamingResponse
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from module1.backend.core.database import get_db
from module1.backend.core.auth import get_current_user, require_roles, require_module_access, role_level
from module1.backend.models.user_models import User, AuditLog
from module1.backend.models.emr_models import Patient
from module2.backend.models.lab_models import TreatmentCycle

from ..models.journey_models import (
    TreatmentPackage, ConsentTemplate, CycleMedication, CycleMedicationDose, CycleConsent, LabTask, LabItem,
    WitnessIncident, CryoStorageTerm, PatientNotification, CycleEvent, PortalBookingRequest, EmbryoPhoto,
)
from ..services import handlers  # noqa: F401  — registers event handlers
from ..services import cycles as cyc, lab_tasks as lt, witness as wit, labels as lbl, observation as obs, consents as cons
from ..services import cryo, notifications, calendar_sync, kpi, report as rpt, packages as pk, events
from ..services.common import row, rows, parse_date, parse_time, patient_name, age_years, today, now, TZ
from ..core.config import jsettings

router = APIRouter(prefix="/api/v1/journey", tags=["Journey — cycle spine, lab chain, patient lane"])

CLINICAL = ["physician", "nurse", "embryologist", "lab_supervisor", "lab_technician"]
LAB = ["physician", "embryologist", "lab_supervisor", "lab_technician", "nurse"]
DESK = ["physician", "nurse", "receptionist", "billing_staff"]
ANY_STAFF = CLINICAL + ["receptionist", "billing_staff", "sonographer", "pharmacist", "marketing_staff"]


def _audit(db: Session, user: User, action: str, resource_type: str, resource_id=None, detail: str = "", request: Request | None = None):
    db.add(AuditLog(id=str(uuid.uuid4()), user_id=user.id if user else None, action=action, module="journey",
                    resource_type=resource_type, resource_id=str(resource_id) if resource_id else None, detail=detail,
                    ip_address=request.client.host if request and request.client else None,
                    user_agent=request.headers.get("User-Agent") if request else None))


# ═══════════════════════════════════════════════════════════════════════════
# PACKAGES & CONSENT TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/packages")
def list_packages(include_inactive: bool = False, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    q = db.query(TreatmentPackage)
    if not include_inactive:
        q = q.filter(TreatmentPackage.is_active == True)
    return rows(q.order_by(TreatmentPackage.sort_order, TreatmentPackage.code).all())


@router.post("/packages/seed")
def seed_packages(db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "admin"))):
    return pk.seed_defaults(db)


@router.post("/packages")
async def create_package(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "admin"))):
    b = await request.json()
    if db.query(TreatmentPackage).filter(TreatmentPackage.code == b.get("code")).first():
        raise HTTPException(409, "Package code exists")
    p = TreatmentPackage(**{k: v for k, v in b.items() if hasattr(TreatmentPackage, k) and k != "id"})
    db.add(p)
    _audit(db, user, "CREATE", "package", None, b.get("code"), request)
    db.commit()
    db.refresh(p)
    return row(p)


@router.put("/packages/{package_id}")
async def update_package(package_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "admin"))):
    p = cyc.get_package(db, package_id)
    b = await request.json()
    for k, v in b.items():
        if hasattr(TreatmentPackage, k) and k not in ("id", "created_at"):
            setattr(p, k, v)
    _audit(db, user, "UPDATE", "package", p.id, p.code, request)
    db.commit()
    db.refresh(p)
    return row(p)


@router.get("/lab-event-types")
def lab_event_types(user: User = Depends(require_roles(ANY_STAFF))):
    return {k: {"title_en": v[0], "title_th": v[1], "items": v[2], "write_back": v[3]} for k, v in pk.LAB_EVENT_TYPES.items()}


@router.get("/consent-templates")
def consent_templates(db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    return rows(db.query(ConsentTemplate).order_by(ConsentTemplate.code).all())


@router.put("/consent-templates/{template_id}")
async def update_consent_template(template_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "admin"))):
    t = db.query(ConsentTemplate).filter(ConsentTemplate.id == template_id).first()
    if not t:
        raise HTTPException(404, "Template not found")
    b = await request.json()
    for k in ("title_en", "title_th", "body_en", "body_th", "version", "signer", "is_active"):
        if k in b:
            setattr(t, k, b[k])
    db.commit()
    return row(t)


# ═══════════════════════════════════════════════════════════════════════════
# PATIENTS (search + partner link)
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/patients/search")
def search_patients(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    like = f"%{q}%"
    ps = db.query(Patient).filter(Patient.is_active == True, or_(Patient.hn_number.ilike(like), Patient.first_name_en.ilike(like),
                                  Patient.last_name_en.ilike(like), Patient.first_name_th.ilike(like), Patient.last_name_th.ilike(like),
                                  Patient.phone.ilike(like))).limit(limit).all()
    out = []
    for p in ps:
        partner = cyc.partner_of(db, p.id)
        out.append({"id": p.id, "hn": p.hn_number, "name_en": patient_name(p), "name_th": patient_name(p, "th"), "gender": p.gender,
                    "dob": str(p.date_of_birth) if p.date_of_birth else None, "age": age_years(p.date_of_birth), "phone": p.phone,
                    "partner": {"id": partner.id, "hn": partner.hn_number, "name_en": patient_name(partner)} if partner else None})
    return out


@router.post("/patients/{patient_id}/partner")
async def set_partner(patient_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK + CLINICAL))):
    b = await request.json()
    cyc.link_partner(db, patient_id, b.get("partner_id"))
    _audit(db, user, "UPDATE", "patient_partner", patient_id, str(b.get("partner_id")), request)
    db.commit()
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# CYCLES
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/cycles")
def list_cycles(patient_id: Optional[str] = None, status: Optional[str] = None, q: Optional[str] = None, active_only: bool = False,
                limit: int = Query(100, le=500), db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    qry = db.query(TreatmentCycle, Patient).join(Patient, Patient.id == TreatmentCycle.patient_id)
    if patient_id:
        qry = qry.filter(TreatmentCycle.patient_id == patient_id)
    if status:
        qry = qry.filter(TreatmentCycle.status == status)
    if active_only:
        qry = qry.filter(TreatmentCycle.status.notin_(("closed", "cancelled")))
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(Patient.hn_number.ilike(like), Patient.first_name_en.ilike(like), Patient.last_name_en.ilike(like),
                             Patient.first_name_th.ilike(like), TreatmentCycle.cycle_number.ilike(like)))
    out = []
    pkgs = {str(p.id): p for p in db.query(TreatmentPackage).all()}
    for c, p in qry.order_by(desc(TreatmentCycle.created_at)).limit(limit).all():
        d = row(c)
        pkg = pkgs.get(str(c.package_id))
        d.update({"hn": p.hn_number, "patient_en": patient_name(p), "patient_th": patient_name(p, "th"), "age": age_years(p.date_of_birth),
                  "package_code": pkg.code if pkg else None, "package_name_en": pkg.name_en if pkg else None,
                  "pending_tasks": db.query(LabTask).filter(LabTask.cycle_id == c.id, LabTask.status == "pending").count(),
                  "pending_consents": db.query(CycleConsent).filter(CycleConsent.cycle_id == c.id, CycleConsent.status == "pending").count()})
        out.append(d)
    return out


@router.post("/cycles")
async def create_cycle(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    b = await request.json()
    for f in ("patient_id", "package_id"):
        if not b.get(f):
            raise HTTPException(400, f"{f} required")
    c = cyc.create_cycle(db, patient_id=b["patient_id"], package_id=b["package_id"], physician_id=b.get("physician_id") or (user.id if user.role == "physician" else None),
                         medication_start_date=b.get("medication_start_date"), partner_id=b.get("partner_id"),
                         physician_order=b.get("physician_order"), notes=b.get("notes"), actor_id=user.id, timeline_id=b.get("timeline_id"))
    _audit(db, user, "CREATE", "cycle", c.id, c.cycle_number, request)
    db.commit()
    return row(c)


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    return obs.workspace(db, cyc.get_cycle(db, cycle_id))


@router.patch("/cycles/{cycle_id}")
async def patch_cycle(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse", "embryologist"))):
    c = cyc.get_cycle(db, cycle_id)
    b = await request.json()
    for k in ("medication_start_date", "physician_order", "planned_et_day", "pgt", "freeze_all", "registry_report_status", "notes", "physician_id", "status", "embryologist_id"):
        if k in b:
            setattr(c, k, parse_date(b[k]) if k == "medication_start_date" else b[k])
    if "partner_id" in b:
        cyc.link_partner(db, c.patient_id, b["partner_id"])
        c.partner_id = b["partner_id"]
    if c.medication_start_date:
        c.start_date = c.medication_start_date
    _audit(db, user, "UPDATE", "cycle", c.id, ", ".join(b.keys()), request)
    db.commit()
    return row(c)


# ── Stimulation chart ────────────────────────────────────────────────────────
@router.post("/cycles/{cycle_id}/medications")
async def add_medication(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    c = cyc.get_cycle(db, cycle_id)
    b = await request.json()
    m = CycleMedication(cycle_id=c.id, drug_id=b.get("drug_id"), drug_code=b.get("drug_code"), drug_en=b["drug_en"], drug_th=b.get("drug_th"),
                        dose=b.get("dose"), unit=b.get("unit"), route=b.get("route"), slot=b.get("slot", "PM"),
                        start_day_index=int(b.get("start_day_index", 1)), end_day_index=int(b.get("end_day_index", b.get("start_day_index", 1))),
                        instructions_en=b.get("instructions_en"), instructions_th=b.get("instructions_th"),
                        sort_order=int(b.get("sort_order", 50)))
    db.add(m)
    db.commit()
    db.refresh(m)
    return row(m)


@router.put("/medications/{med_id}")
async def update_medication(med_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    m = db.query(CycleMedication).filter(CycleMedication.id == med_id).first()
    if not m:
        raise HTTPException(404, "Medication row not found")
    b = await request.json()
    for k in ("drug_en", "drug_th", "drug_code", "dose", "unit", "route", "slot", "start_day_index", "end_day_index", "instructions_en", "instructions_th", "sort_order"):
        if k in b:
            setattr(m, k, b[k])
    db.commit()
    return row(m)


@router.delete("/medications/{med_id}")
def delete_medication(med_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    m = db.query(CycleMedication).filter(CycleMedication.id == med_id).first()
    if m:
        db.delete(m)
        db.commit()
    return {"status": "deleted"}


@router.post("/cycles/{cycle_id}/publish")
def publish(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    c = cyc.get_cycle(db, cycle_id)
    return cyc.publish_plan(db, c, actor_id=user.id)


@router.post("/doses/{dose_id}/taken")
async def dose_taken(dose_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(CLINICAL))):
    d = db.query(CycleMedicationDose).filter(CycleMedicationDose.id == dose_id).first()
    if not d:
        raise HTTPException(404, "Dose not found")
    b = await request.json() if request.headers.get("content-length", "0") not in ("0", "") else {}
    d.taken_at = None if b.get("undo") else now()
    d.taken_source = None if b.get("undo") else "staff"
    db.commit()
    return row(d)


# ── Monitoring / trigger / scheduling ────────────────────────────────────────
@router.post("/cycles/{cycle_id}/monitoring")
async def monitoring(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse", "sonographer"))):
    c = cyc.get_cycle(db, cycle_id)
    return row(cyc.record_monitoring(db, c, await request.json(), actor_id=user.id))


@router.post("/cycles/{cycle_id}/trigger")
async def trigger(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    c = cyc.get_cycle(db, cycle_id)
    b = await request.json()
    at = datetime.fromisoformat(b["trigger_at"])
    return cyc.set_trigger(db, c, at, actor_id=user.id, drug=b.get("drug"))


@router.post("/cycles/{cycle_id}/schedule")
async def schedule(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    c = cyc.get_cycle(db, cycle_id)
    b = await request.json()
    d0 = parse_date(b.get("d0"))
    if not d0:
        raise HTTPException(400, "d0 (procedure date) required")
    out = cyc.schedule_procedure(db, c, d0, parse_time(b.get("time")), actor_id=user.id, room=b.get("room"), physician_order=b.get("physician_order"))
    _audit(db, user, "UPDATE", "cycle_schedule", c.id, f"D0 {d0}", request)
    db.commit()
    return out


# ── Observation (Day0–Day7) ──────────────────────────────────────────────────
@router.post("/cycles/{cycle_id}/opu")
async def opu(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return obs.upsert_opu(db, cyc.get_cycle(db, cycle_id), await request.json(), user)


@router.post("/cycles/{cycle_id}/fertilization")
async def fertilization(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    b = await request.json()
    return obs.set_fertilization(db, cyc.get_cycle(db, cycle_id), b.get("items") or [], user)


@router.post("/cycles/{cycle_id}/embryos/{embryo_id}/assessment")
async def assessment(cycle_id: str, embryo_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return obs.add_assessment(db, cyc.get_cycle(db, cycle_id), embryo_id, await request.json(), user)


@router.post("/cycles/{cycle_id}/embryos/{embryo_id}/freeze")
async def freeze(cycle_id: str, embryo_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return obs.freeze_embryo(db, cyc.get_cycle(db, cycle_id), embryo_id, await request.json(), user)


@router.post("/cycles/{cycle_id}/embryos/{embryo_id}/warm")
async def warm(cycle_id: str, embryo_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return obs.warm_embryo(db, cyc.get_cycle(db, cycle_id), embryo_id, await request.json(), user)


@router.post("/cycles/{cycle_id}/transfer")
async def transfer(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return obs.transfer_embryos(db, cyc.get_cycle(db, cycle_id), await request.json(), user)


# ── Photos / album ───────────────────────────────────────────────────────────
@router.post("/cycles/{cycle_id}/photos")
async def upload_photo(cycle_id: str, file: UploadFile = File(...), embryo_id: Optional[str] = Form(None), oocyte_id: Optional[str] = Form(None),
                       lab_day: Optional[int] = Form(None), caption_en: Optional[str] = Form(None), caption_th: Optional[str] = Form(None),
                       source: str = Form("upload"), release: bool = Form(False),
                       db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    ph = await obs.save_photo(db, cyc.get_cycle(db, cycle_id), file, user, embryo_id=embryo_id or None, oocyte_id=oocyte_id or None,
                              lab_day=lab_day, caption_en=caption_en, caption_th=caption_th, source=source, release=release)
    return row(ph)


@router.post("/cycles/{cycle_id}/photos/release")
async def release_photos(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    b = await request.json()
    return {"released": obs.release_photos(db, cyc.get_cycle(db, cycle_id), b.get("photo_ids") or [], user)}


@router.get("/photos/{photo_id}/file")
def photo_file(photo_id: str, t: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Image for <img src>: accepts ?t=<staff jwt> because img tags cannot send headers."""
    from module1.backend.core.security import decode_access_token
    from module1.backend.core.auth import canonical_role
    try:
        payload = decode_access_token(t or "")
    except Exception:
        raise HTTPException(401, "token required")
    if canonical_role(payload.get("role")) not in set(ANY_STAFF) and role_level(payload.get("role")) < 95:
        raise HTTPException(403, "Insufficient permissions")
    ph = db.query(EmbryoPhoto).filter(EmbryoPhoto.id == photo_id).first()
    if not ph or not Path(ph.path).exists():
        raise HTTPException(404, "Photo not found")
    return FileResponse(ph.path)


# ── Consents ─────────────────────────────────────────────────────────────────
@router.post("/consents/{consent_id}/sign")
async def sign_consent(consent_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK + CLINICAL))):
    cc = db.query(CycleConsent).filter(CycleConsent.id == consent_id).first()
    if not cc:
        raise HTTPException(404, "Consent not found")
    b = await request.json()
    cc = cons.sign(db, cc, signature_data_url=b.get("signature"), signer_patient_id=b.get("signer_patient_id") or cc.patient_id,
                   channel=b.get("channel", "clinic_tablet"), witness_user_id=user.id, ip=request.client.host if request.client else None, actor_id=user.id)
    _audit(db, user, "SIGN", "consent", cc.id, cc.consent_type, request)
    db.commit()
    return row(cc)


@router.get("/consents/{consent_id}/file")
def consent_file(consent_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    cc = db.query(CycleConsent).filter(CycleConsent.id == consent_id).first()
    if not cc or not cc.document_path or not Path(cc.document_path).exists():
        raise HTTPException(404, "Document not found")
    return FileResponse(cc.document_path, media_type="application/pdf")


# ── Outcome / close / report / events ────────────────────────────────────────
@router.post("/cycles/{cycle_id}/outcome")
async def outcome(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse"))):
    return row(cyc.record_outcome(db, cyc.get_cycle(db, cycle_id), await request.json(), actor_id=user.id))


@router.post("/cycles/{cycle_id}/close")
async def close(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician"))):
    b = await request.json()
    return row(cyc.close_cycle(db, cyc.get_cycle(db, cycle_id), b.get("reason"), actor_id=user.id))


@router.post("/cycles/{cycle_id}/cancel")
async def cancel(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician"))):
    b = await request.json()
    return row(cyc.cancel_cycle(db, cyc.get_cycle(db, cycle_id), b.get("reason"), actor_id=user.id))


@router.get("/cycles/{cycle_id}/report.pdf")
def report_pdf(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    c = cyc.get_cycle(db, cycle_id)
    pdf = rpt.cycle_report_pdf(db, c)
    events.emit(db, "report.generated", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id, payload={})
    db.commit()
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{c.cycle_number}-report.pdf"'})


@router.get("/cycles/{cycle_id}/events")
def cycle_events(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    return rows(db.query(CycleEvent).filter(CycleEvent.cycle_id == cycle_id).order_by(desc(CycleEvent.created_at)).limit(200).all())


# ═══════════════════════════════════════════════════════════════════════════
# LAB TO-DO, LABELS, WITNESSING
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/lab/tasks")
def lab_tasks(on: Optional[str] = None, lab_day: Optional[int] = None, status: Optional[str] = None, cycle_id: Optional[str] = None,
              q: Optional[str] = None, assignee: Optional[str] = None, days: int = 1, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["receptionist"]))):
    d = parse_date(on) or today()
    qry = db.query(LabTask).filter(LabTask.scheduled_date >= d, LabTask.scheduled_date < date.fromordinal(d.toordinal() + max(1, days)))
    if lab_day is not None:
        qry = qry.filter(LabTask.lab_day == lab_day)
    if status:
        qry = qry.filter(LabTask.status == status)
    if cycle_id:
        qry = db.query(LabTask).filter(LabTask.cycle_id == cycle_id)
    tasks = qry.order_by(LabTask.scheduled_date, LabTask.scheduled_time, LabTask.sort_order).all()
    cycles = {str(c.id): c for c in db.query(TreatmentCycle).filter(TreatmentCycle.id.in_({t.cycle_id for t in tasks})).all()} if tasks else {}
    pids = {c.patient_id for c in cycles.values()} | {c.partner_id for c in cycles.values() if c.partner_id}
    patients = {str(p.id): p for p in db.query(Patient).filter(Patient.id.in_(pids)).all()} if pids else {}
    uids = {t.assigned_to for t in tasks if t.assigned_to}
    users = {str(u.id): u for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    views = [lt.task_view(db, t, cycles[str(t.cycle_id)], patients, users) for t in tasks]
    if q:
        ql = q.lower()
        views = [v for v in views if ql in (v.get("hn") or "").lower() or ql in (v.get("patient_en") or "").lower() or ql in (v.get("patient_th") or "")]
    if assignee:
        views = [v for v in views if (assignee == "unassigned" and not v.get("assignee")) or (v.get("assignee") or {}).get("id") == assignee]
    groups = {}
    for v in views:
        groups.setdefault(v["task_type"], []).append(v)
    return {"date": str(d), "count": len(views), "groups": groups, "tasks": views}


@router.get("/lab/staff")
def lab_staff(db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["receptionist"]))):
    """Staff who can be assigned a lab step (embryologists, lab supervisors/technicians, nurses, physicians)."""
    return lt.assignable_staff(db)


@router.post("/lab/tasks/assign")
async def tasks_assign_bulk(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    """Assign several tasks at once (e.g. a whole column of the board): {task_ids: [...], user_id: <id> | null}."""
    b = await request.json()
    ids = b.get("task_ids") or []
    tasks = db.query(LabTask).filter(LabTask.id.in_(ids)).all() if ids else []
    for t in tasks:
        lt.assign(db, t, b.get("user_id"), user.id)
    db.commit()
    return {"assigned": len(tasks), "tasks": [lt.task_view(db, t) for t in tasks]}


@router.post("/lab/tasks/{task_id}/assign")
async def task_assign(task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    """Assign the staff member responsible for this step: {user_id: <id>} — or {user_id: null} to unassign; {me: true} assigns the caller."""
    t = db.query(LabTask).filter(LabTask.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    b = await request.json() if request.headers.get("content-length", "0") not in ("0", "") else {}
    lt.assign(db, t, str(user.id) if b.get("me") else b.get("user_id"), user.id)
    db.commit()
    return lt.task_view(db, t)


@router.get("/lab/tasks/{task_id}")
def lab_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["receptionist"]))):
    t = db.query(LabTask).filter(LabTask.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    return lt.task_view(db, t)


@router.post("/lab/tasks/{task_id}/done")
async def task_done(task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    t = db.query(LabTask).filter(LabTask.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    b = await request.json() if request.headers.get("content-length", "0") not in ("0", "") else {}
    lt.mark_done(db, t, user.id, via="manual", notes=b.get("notes"))
    db.commit()
    return lt.task_view(db, t)


@router.post("/lab/tasks/{task_id}/failed")
async def task_failed(task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    t = db.query(LabTask).filter(LabTask.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    b = await request.json()
    lt.mark_failed(db, t, user.id, b.get("reason") or "failed")
    db.commit()
    return lt.task_view(db, t)


@router.post("/cycles/{cycle_id}/tasks")
async def adhoc_task(cycle_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    c = cyc.get_cycle(db, cycle_id)
    t = lt.add_task(db, c, await request.json(), actor_id=user.id)
    db.commit()
    return lt.task_view(db, t, c)


@router.get("/cycles/{cycle_id}/items")
def cycle_items(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return rows(db.query(LabItem).filter(LabItem.cycle_id == cycle_id, LabItem.is_active == True).order_by(LabItem.lab_day, LabItem.item_type).all())


@router.post("/labels/print")
async def print_labels(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    """body: {task_ids: [...]} and/or {item_ids: [...]}, copies, width_mm, height_mm → PDF (one page per label)."""
    b = await request.json()
    items = lbl.items_for_tasks(db, b.get("task_ids") or [])
    if b.get("item_ids"):
        items += [it for it in db.query(LabItem).filter(LabItem.id.in_(b["item_ids"])).all() if it.id not in {i.id for i in items}]
    if b.get("item_types"):
        items = [it for it in items if it.item_type in b["item_types"]]
    if not items:
        raise HTTPException(400, "Nothing to print")
    copies = int(b.get("copies", 1))
    pdf = lbl.render_labels(db, items, width_mm=b.get("width_mm"), height_mm=b.get("height_mm"), copies=copies)
    lbl.mark_printed(db, items, user.id, copies)
    _audit(db, user, "PRINT", "labels", None, f"{len(items)} labels × {copies}", request)
    db.commit()
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="labels.pdf"'})


@router.post("/lab/tasks/{task_id}/witness/start")
async def witness_start(task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    b = await request.json() if request.headers.get("content-length", "0") not in ("0", "") else {}
    s = wit.start_session(db, task_id, user, device=b.get("device") or request.headers.get("User-Agent", "")[:120])
    return row(s)


@router.post("/witness/{session_id}/scan")
async def witness_scan(session_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    b = await request.json()
    return wit.scan(db, session_id, b.get("payload", ""), user)


@router.post("/lab/tasks/{task_id}/witness/manual")
async def witness_manual(task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    b = await request.json()
    return wit.manual_witness(db, task_id, user, b.get("second_email", ""), b.get("second_password", ""), b.get("note"))


@router.get("/cycles/{cycle_id}/scan-record")
def scan_rec(cycle_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    return wit.scan_record(db, cycle_id)


@router.get("/lab/incidents")
def incidents(open_only: bool = True, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    q = db.query(WitnessIncident)
    if open_only:
        q = q.filter(WitnessIncident.resolved_at == None)
    return rows(q.order_by(desc(WitnessIncident.created_at)).limit(200).all())


@router.post("/lab/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "embryologist", "lab_supervisor"))):
    inc = db.query(WitnessIncident).filter(WitnessIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(404, "Incident not found")
    b = await request.json()
    inc.resolved_by, inc.resolved_at, inc.resolution = user.id, now(), b.get("resolution")
    _audit(db, user, "RESOLVE", "witness_incident", inc.id, b.get("resolution", ""), request)
    db.commit()
    return row(inc)


# ═══════════════════════════════════════════════════════════════════════════
# CRYO ↔ BILLING
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/cryo/due")
def cryo_due(within_days: int = 90, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["billing_staff", "receptionist"]))):
    return cryo.due_list(db, within_days)


@router.get("/cryo/patient/{patient_id}")
def cryo_patient(patient_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    return cryo.inventory_for_patient(db, patient_id)


@router.post("/cryo/terms")
async def cryo_open_term(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["billing_staff"]))):
    b = await request.json()
    t = cryo.open_term(db, patient_id=b["patient_id"], cycle_id=b.get("cycle_id"), content_type=b.get("content_type", "embryo"),
                       reference_table=b.get("reference_table", "embryo_cryopreservations"), reference_ids=b.get("reference_ids") or [],
                       stored_at=parse_date(b.get("stored_at")), months=b.get("months"), actor_id=user.id)
    return row(t)


@router.post("/cryo/terms/{term_id}/renew")
async def cryo_renew(term_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["billing_staff", "receptionist"]))):
    t = db.query(CryoStorageTerm).filter(CryoStorageTerm.id == term_id).first()
    if not t:
        raise HTTPException(404, "Term not found")
    b = await request.json()
    if "annual_fee" in b:
        t.annual_fee = b["annual_fee"]
    return row(cryo.renew(db, t, b.get("months"), payment_method=b.get("payment_method"), reference=b.get("reference"), actor_id=user.id))


@router.post("/cryo/terms/{term_id}/status")
async def cryo_status(term_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(LAB))):
    t = db.query(CryoStorageTerm).filter(CryoStorageTerm.id == term_id).first()
    if not t:
        raise HTTPException(404, "Term not found")
    b = await request.json()
    return row(cryo.set_status(db, t, b["status"], actor_id=user.id, note=b.get("note")))


@router.post("/cryo/run-reminders")
def cryo_run(db: Session = Depends(get_db), user: User = Depends(require_roles(LAB + ["billing_staff"]))):
    return cryo.run_renewal_reminders(db)


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS, CALENDAR, JOBS, KPI
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/notifications")
def notifications_list(patient_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    q = db.query(PatientNotification)
    if patient_id:
        q = q.filter(PatientNotification.patient_id == patient_id)
    return rows(q.order_by(desc(PatientNotification.created_at)).limit(limit).all())


@router.post("/notifications/broadcast")
async def broadcast(request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles("physician", "nurse", "receptionist", "marketing_staff"))):
    b = await request.json()
    ids = b.get("patient_ids")
    if not ids:
        ids = [p.id for p in db.query(Patient).filter(Patient.is_active == True).all()]
    n = notifications.broadcast(db, ids, b.get("title_en", ""), b.get("title_th", ""), b.get("body_en", ""), b.get("body_th", ""), b.get("channels"))
    _audit(db, user, "BROADCAST", "notification", None, f"{n} patients", request)
    db.commit()
    return {"sent": n}


@router.post("/notifications/send-due")
def send_due(db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    return {"delivered": notifications.send_due(db)}


@router.get("/booking-requests")
def booking_requests(status: str = "requested", db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    out = []
    for r in db.query(PortalBookingRequest).filter(PortalBookingRequest.status == status).order_by(PortalBookingRequest.requested_date).all():
        d = row(r)
        p = db.query(Patient).filter(Patient.id == r.patient_id).first()
        d.update({"hn": p.hn_number if p else None, "patient_en": patient_name(p), "patient_th": patient_name(p, "th"), "phone": p.phone if p else None})
        out.append(d)
    return out


@router.post("/booking-requests/{req_id}/confirm")
async def confirm_booking(req_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    from module6.backend.models.crm_models import Appointment
    from ..services.crm_hooks import on_appointment
    r = db.query(PortalBookingRequest).filter(PortalBookingRequest.id == req_id).first()
    if not r:
        raise HTTPException(404, "Request not found")
    b = await request.json()
    d = parse_date(b.get("date")) or r.requested_date
    t = parse_time(b.get("time")) or r.requested_time or parse_time("13:00")
    appt = Appointment(id=str(uuid.uuid4()), booking_number=cyc._next_booking_number(db), patient_id=r.patient_id, appointment_date=d,
                       appointment_time=t, duration_minutes=int(b.get("duration_minutes", 30)), appointment_type=r.appointment_type,
                       department=b.get("department", "clinic"), provider_id=b.get("provider_id"), status="scheduled", booking_source="online",
                       chief_complaint=r.note, created_by=user.id)
    db.add(appt)
    db.flush()
    r.status, r.appointment_id, r.handled_by, r.handled_at = "confirmed", appt.id, user.id, now()
    on_appointment(db, appt, "created", actor_id=user.id)
    db.commit()
    return {"appointment_id": appt.id, "booking_number": appt.booking_number}


@router.post("/booking-requests/{req_id}/decline")
async def decline_booking(req_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    r = db.query(PortalBookingRequest).filter(PortalBookingRequest.id == req_id).first()
    if not r:
        raise HTTPException(404, "Request not found")
    r.status, r.handled_by, r.handled_at = "declined", user.id, now()
    db.commit()
    return {"status": "declined"}


@router.get("/calendar/status")
def calendar_status(user: User = Depends(require_roles(ANY_STAFF))):
    return {"enabled": calendar_sync.enabled(), "calendar_id": jsettings.GOOGLE_CALENDAR_ID,
            "procedures_calendar_id": jsettings.GOOGLE_CALENDAR_PROCEDURES_ID,
            "service_account_json": bool(jsettings.GOOGLE_SERVICE_ACCOUNT_JSON)}


@router.post("/calendar/sync-all")
def calendar_sync_all(since: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    if not calendar_sync.enabled():
        raise HTTPException(503, "Google Calendar not configured (GOOGLE_CALENDAR_ID + GOOGLE_SERVICE_ACCOUNT_JSON)")
    return calendar_sync.sync_all(db, parse_date(since))


@router.post("/calendar/import-busy")
def calendar_import(days_ahead: int = 60, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    if not calendar_sync.enabled():
        raise HTTPException(503, "Google Calendar not configured")
    return {"blocks_imported": calendar_sync.import_busy(db, days_ahead)}


@router.post("/jobs/daily")
def jobs_daily(db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    """Run the scheduled housekeeping: due notifications, cryo reminders, Google busy import."""
    out = {"notifications_delivered": notifications.send_due(db), "cryo": cryo.run_renewal_reminders(db)}
    if calendar_sync.enabled():
        try:
            out["gcal_blocks_imported"] = calendar_sync.import_busy(db)
        except Exception as e:
            out["gcal_error"] = str(e)[:160]
    return out


@router.get("/connections")
def connections(user: User = Depends(require_roles(ANY_STAFF))):
    """Which external connections are configured (what the admin still has to set up)."""
    return {
        "line_messaging_push": jsettings.line_push_enabled,
        "line_login_liff": bool(jsettings.LINE_LIFF_ID and jsettings.LINE_LOGIN_CHANNEL_ID),
        "sms": (jsettings.SMS_PROVIDER or "none") != "none",
        "email_smtp": bool(jsettings.SMTP_HOST),
        "whatsapp": bool(jsettings.WHATSAPP_ACCESS_TOKEN),
        "google_calendar": calendar_sync.enabled(),
        "promptpay": bool(jsettings.PROMPTPAY_ID),
        "portal_base_url": jsettings.PORTAL_BASE_URL,
    }


@router.get("/kpi")
def kpis(start: Optional[str] = None, end: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require_roles(CLINICAL + ["billing_staff"]))):
    return kpi.compute(db, parse_date(start), parse_date(end))


@router.get("/kpi/monthly")
def kpi_monthly(months: int = 12, db: Session = Depends(get_db), user: User = Depends(require_roles(CLINICAL + ["billing_staff"]))):
    return kpi.monthly_series(db, months)


@router.get("/kpi/export.xlsx")
def kpi_export(start: Optional[str] = None, end: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require_roles(CLINICAL))):
    from openpyxl import Workbook
    k = kpi.compute(db, parse_date(start), parse_date(end))
    wb = Workbook()
    ws = wb.active
    ws.title = "KPI"
    ws.append(["Period", k["period"]["start"], k["period"]["end"]])
    ws.append([])
    ws.append(["Indicator", "Key", "Value", "Competence", "Benchmark", "Direction", "Status", "Type", "Source", "Note"])
    bm, labels, status = k.get("benchmarks", {}), k.get("labels", {}), k.get("status", {})
    for section in ("laboratory", "clinical", "operational"):
        ws.append([])
        ws.append([section.upper()])
        for key, val in k[section].items():
            if key == "counts":
                continue
            b = bm.get(key, {})
            ws.append([labels.get(key, key), key, val, b.get("competence"), b.get("benchmark"), b.get("direction"),
                       status.get(key), b.get("kind"), b.get("source"), b.get("note")])
        ws.append(["counts"] + [f"{a}={b}" for a, b in k[section]["counts"].items()])
    ws.append([])
    for ref in k.get("references", []):
        ws.append(["Reference", ref])
    ws2 = wb.create_sheet("Monthly")
    series = kpi.monthly_series(db, 12)
    if series:
        keys = list(series[0].keys())
        ws2.append([labels.get(x, x) for x in keys])
        ws2.append(keys)
        ws2.append(["competence"] + [bm.get(x, {}).get("competence") for x in keys[1:]])
        ws2.append(["benchmark"] + [bm.get(x, {}).get("benchmark") for x in keys[1:]])
        for r in series:
            ws2.append([r.get(x) for x in keys])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": 'attachment; filename="fcms-kpi.xlsx"'})


# ═══════════════════════════════════════════════════════════════════════════
# QUEUE (front desk → patient push)
# ═══════════════════════════════════════════════════════════════════════════
@router.post("/appointments/{appt_id}/call")
async def call_patient(appt_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles(DESK))):
    from module6.backend.models.crm_models import Appointment
    from ..services.crm_hooks import on_appointment, assign_queue_number
    a = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not a:
        raise HTTPException(404, "Appointment not found")
    assign_queue_number(db, a)
    a.status = "in_progress"
    on_appointment(db, a, "called", actor_id=user.id)
    _audit(db, user, "CALL", "appointment", a.id, f"queue {a.queue_number}", request)
    db.commit()
    return {"id": a.id, "queue_number": a.queue_number, "status": a.status}


@router.get("/queue/today")
def queue_today(db: Session = Depends(get_db), user: User = Depends(require_roles(ANY_STAFF))):
    from module6.backend.models.crm_models import Appointment
    t = today()
    out = []
    for a in db.query(Appointment).filter(Appointment.appointment_date == t, Appointment.status.notin_(("cancelled", "rescheduled"))).order_by(Appointment.appointment_time).all():
        p = db.query(Patient).filter(Patient.id == a.patient_id).first()
        out.append({**row(a), "hn": p.hn_number if p else None, "patient_en": patient_name(p), "patient_th": patient_name(p, "th")})
    return out
