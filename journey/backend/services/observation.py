"""
Cycle workspace aggregation and the Day0–Day7 observation writes (on top of Module 2 tables).
Binflux tabs: OPU | D0 | D1 … D7 | summary table | album | cryo list | PGT.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from module1.backend.core.config import settings
from module1.backend.models.emr_models import Patient
from module1.backend.models.user_models import User
from module2.backend.models.lab_models import (
    TreatmentCycle, OocyteRetrieval, Oocyte, FertilizationRecord, FertilizationStatus, Embryo, EmbryoAssessment,
    EmbryoCryopreservation, EmbryoWarming, EmbryoTransfer, EmbryoDisposition, BlastocystExpansion, ICMGrade, TEGrade,
    SpermPreparation, SemenAnalysis,
)
from module6.backend.models.crm_models import Appointment

from ..models.journey_models import (
    TreatmentPackage, CycleDay, CycleMedication, CycleMedicationDose, CycleMonitoring, CycleConsent, ConsentTemplate,
    CycleOutcome, LabTask, LabItem, EmbryoPhoto, CryoStorageTerm, CycleEvent,
)
from . import events
from .common import row, rows, now, today, patient_name, age_years, next_number, to_json
from .lab_tasks import task_view
from .witness import scan_record, errors_count


# ─────────────────────────────────────────────────────────────────────────────
# Workspace read model
# ─────────────────────────────────────────────────────────────────────────────
def workspace(db: Session, c: TreatmentCycle) -> dict:
    p = db.query(Patient).filter(Patient.id == c.patient_id).first()
    partner = db.query(Patient).filter(Patient.id == c.partner_id).first() if c.partner_id else None
    pkg = db.query(TreatmentPackage).filter(TreatmentPackage.id == c.package_id).first() if c.package_id else None
    phys = db.query(User).filter(User.id == c.physician_id).first() if c.physician_id else None
    meds = db.query(CycleMedication).filter(CycleMedication.cycle_id == c.id).order_by(CycleMedication.sort_order).all()
    doses = db.query(CycleMedicationDose).filter(CycleMedicationDose.cycle_id == c.id).all()
    days = db.query(CycleDay).filter(CycleDay.cycle_id == c.id).order_by(CycleDay.day_index).all()
    mon = db.query(CycleMonitoring).filter(CycleMonitoring.cycle_id == c.id).order_by(CycleMonitoring.calendar_date).all()
    tasks = db.query(LabTask).filter(LabTask.cycle_id == c.id).order_by(LabTask.scheduled_date, LabTask.sort_order).all()
    consents = db.query(CycleConsent).filter(CycleConsent.cycle_id == c.id).all()
    templates = {t.id: t for t in db.query(ConsentTemplate).all()}
    appts = db.query(Appointment).filter(Appointment.cycle_id == c.id).order_by(Appointment.appointment_date).all()
    outcome = db.query(CycleOutcome).filter(CycleOutcome.cycle_id == c.id).first()
    photos = db.query(EmbryoPhoto).filter(EmbryoPhoto.cycle_id == c.id).order_by(EmbryoPhoto.taken_at).all()
    terms = db.query(CryoStorageTerm).filter(CryoStorageTerm.cycle_id == c.id).all()
    evs = db.query(CycleEvent).filter(CycleEvent.cycle_id == c.id).order_by(CycleEvent.created_at.desc()).limit(50).all()

    dose_map = {}
    for d in doses:
        dose_map.setdefault(str(d.medication_id), {})[str(d.calendar_date)] = row(d)

    return {
        "cycle": {**row(c), "package": row(pkg) if pkg else None,
                  "physician": f"{phys.first_name_en} {phys.last_name_en}" if phys else None,
                  "errors_count": errors_count(db, c.id)},
        "patient": {**row(p), "name_en": patient_name(p), "name_th": patient_name(p, "th"), "age": age_years(p.date_of_birth)} if p else None,
        "partner": {**row(partner), "name_en": patient_name(partner), "name_th": patient_name(partner, "th"), "age": age_years(partner.date_of_birth)} if partner else None,
        "chart": {"medications": [{**row(m), "doses": dose_map.get(str(m.id), {})} for m in meds], "days": rows(days)},
        "monitoring": rows(mon),
        "appointments": rows(appts),
        "tasks": [task_view(db, t, c) for t in tasks],
        "consents": [{**row(cc), "title_en": templates[cc.template_id].title_en if cc.template_id in templates else cc.consent_type,
                      "title_th": templates[cc.template_id].title_th if cc.template_id in templates else cc.consent_type} for cc in consents],
        "observation": observation(db, c),
        "photos": rows(photos),
        "cryo_terms": rows(terms),
        "outcome": row(outcome),
        "scan_record": scan_record(db, c.id),
        "events": rows(evs),
    }


def observation(db: Session, c: TreatmentCycle) -> dict:
    """Day-by-day view over Module 2 entities."""
    opu = db.query(OocyteRetrieval).filter(OocyteRetrieval.cycle_id == c.id).first()
    oocytes = db.query(Oocyte).filter(Oocyte.retrieval_id == opu.id).order_by(Oocyte.oocyte_number).all() if opu else []
    ferts = {f.oocyte_id: f for f in db.query(FertilizationRecord).filter(FertilizationRecord.oocyte_id.in_([o.id for o in oocytes])).all()} if oocytes else {}
    embryos = db.query(Embryo).filter(Embryo.cycle_id == c.id).order_by(Embryo.embryo_code).all()
    sperm_prep = db.query(SpermPreparation).filter(SpermPreparation.cycle_id == c.id).first()
    semen = None
    if c.partner_id:
        semen = db.query(SemenAnalysis).filter(SemenAnalysis.patient_id == c.partner_id).order_by(SemenAnalysis.created_at.desc()).first()
    table = []
    for o in oocytes:
        f = ferts.get(o.id)
        e = next((x for x in embryos if x.fertilization_record_id == (f.id if f else None)), None)
        entry = {"oocyte_number": o.oocyte_number, "oocyte_id": o.id, "maturity": o.maturity_stage,
                 "inseminated": o.is_inseminated, "method": o.insemination_method, "insemination_time": to_json(o.insemination_time),
                 "fertilization": f.status.value if f else None, "fert_check_time": to_json(f.check_time) if f else None,
                 "embryo_code": e.embryo_code if e else None, "embryo_id": e.id if e else None,
                 "disposition": e.disposition.value if e and e.disposition else None, "pgta": e.pgta_result if e else None,
                 "days": {}}
        if e:
            for a in e.assessments:
                entry["days"][str(a.assessment_day)] = {**row(a), "grade": a.overall_grade or _gardner(a)}
            entry["cryo"] = row(e.cryopreservation) if e.cryopreservation else None
            entry["warming"] = row(e.warming) if e.warming else None
            entry["transfer"] = row(e.transfer) if e.transfer else None
        table.append(entry)
    # embryos not traced to an oocyte (imported / legacy)
    traced = {t["embryo_id"] for t in table if t["embryo_id"]}
    for e in embryos:
        if e.id in traced:
            continue
        table.append({"oocyte_number": None, "embryo_code": e.embryo_code, "embryo_id": e.id, "pgta": e.pgta_result,
                      "disposition": e.disposition.value if e.disposition else None,
                      "days": {str(a.assessment_day): {**row(a), "grade": a.overall_grade or _gardner(a)} for a in e.assessments},
                      "cryo": row(e.cryopreservation) if e.cryopreservation else None,
                      "warming": row(e.warming) if e.warming else None, "transfer": row(e.transfer) if e.transfer else None})
    summary = {
        "follicles_aspirated": opu.total_follicles_aspirated if opu else None,
        "oocytes_retrieved": opu.total_oocytes_retrieved if opu else len(oocytes) or None,
        "mii": opu.mii_count if opu else sum(1 for o in oocytes if o.maturity_stage == "MII"),
        "inseminated": sum(1 for o in oocytes if o.is_inseminated),
        "2pn": sum(1 for f in ferts.values() if f.status == FertilizationStatus.NORMAL_2PN),
        "embryos": len(embryos),
        "blastocysts": sum(1 for e in embryos if any(a.expansion for a in e.assessments)),
        "frozen": sum(1 for e in embryos if e.cryopreservation),
        "transferred": sum(1 for e in embryos if e.transfer),
        "biopsied": sum(1 for e in embryos if e.is_pgta_tested),
    }
    return {"opu": row(opu), "sperm_prep": row(sperm_prep), "semen_analysis": row(semen), "table": table, "summary": summary}


def _gardner(a: EmbryoAssessment) -> str | None:
    if a.expansion:
        return f"{a.expansion.value}{a.icm_grade.value if a.icm_grade else ''}{a.te_grade.value if a.te_grade else ''}"
    if a.cell_count:
        return f"{a.cell_count}c" + (f" {int(a.fragmentation_pct)}%" if a.fragmentation_pct is not None else "")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Writes
# ─────────────────────────────────────────────────────────────────────────────
def upsert_opu(db: Session, c: TreatmentCycle, body: dict, user: User) -> dict:
    """OPU record + create oocyte rows from counts (MII/MI/GV/degenerated)."""
    opu = db.query(OocyteRetrieval).filter(OocyteRetrieval.cycle_id == c.id).first()
    if not opu:
        opu = OocyteRetrieval(patient_id=c.patient_id, cycle_id=c.id, procedure_date=c.d0_date or today(),
                              physician_id=c.physician_id or str(user.id), embryologist_id=str(user.id))
        db.add(opu)
    for f in ("procedure_date", "start_time", "end_time", "anesthesia_type", "total_follicles_aspirated", "total_oocytes_retrieved",
              "mii_count", "mi_count", "gv_count", "degenerated_count", "follicular_fluid_ml", "complications", "notes"):
        if f in body:
            setattr(opu, f, body[f])
    db.flush()
    existing = db.query(Oocyte).filter(Oocyte.retrieval_id == opu.id).count()
    want = int(body.get("total_oocytes_retrieved") or opu.total_oocytes_retrieved or 0)
    stages = ["MII"] * int(opu.mii_count or 0) + ["MI"] * int(opu.mi_count or 0) + ["GV"] * int(opu.gv_count or 0) + ["DEG"] * int(opu.degenerated_count or 0)
    for n in range(existing + 1, want + 1):
        db.add(Oocyte(retrieval_id=opu.id, oocyte_number=n, maturity_stage=stages[n - 1] if n - 1 < len(stages) else None))
        db.flush()   # one row at a time: Module 2 ids are str defaults on uuid columns
    events.emit(db, "observation.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"day": 0, "kind": "opu", "oocytes": want})
    db.commit()
    return observation(db, c)


def set_fertilization(db: Session, c: TreatmentCycle, items: list[dict], user: User) -> dict:
    """items: [{oocyte_id, status: 2PN|1PN|3PN|0PN|DG, pronuclei_count}] → fertilization records + embryo rows for 2PN."""
    for it in items:
        o = db.query(Oocyte).filter(Oocyte.id == it["oocyte_id"]).first()
        if not o:
            continue
        f = db.query(FertilizationRecord).filter(FertilizationRecord.oocyte_id == o.id).first()
        if not f:
            f = FertilizationRecord(oocyte_id=o.id, patient_id=c.patient_id, embryologist_id=str(user.id))
            db.add(f)
        f.status = FertilizationStatus(it["status"])
        f.pronuclei_count = it.get("pronuclei_count")
        f.check_time = f.check_time or now()
        db.flush()
        if f.status == FertilizationStatus.NORMAL_2PN and not f.embryo:
            db.add(Embryo(embryo_code=next_number(db, Embryo, Embryo.embryo_code, "EMB", width=5), patient_id=c.patient_id,
                          partner_id=c.partner_id, cycle_id=c.id, fertilization_record_id=f.id, current_day=1))
            db.flush()
    events.emit(db, "observation.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"day": 1, "kind": "fertilization", "count": len(items)})
    db.commit()
    return observation(db, c)


def add_assessment(db: Session, c: TreatmentCycle, embryo_id: str, body: dict, user: User) -> dict:
    e = db.query(Embryo).filter(Embryo.id == embryo_id, Embryo.cycle_id == c.id).first()
    if not e:
        raise HTTPException(404, "Embryo not found in this cycle")
    day = int(body.get("assessment_day") or (e.current_day or 1))
    a = db.query(EmbryoAssessment).filter(EmbryoAssessment.embryo_id == e.id, EmbryoAssessment.assessment_day == day).first()
    if not a:
        a = EmbryoAssessment(embryo_id=e.id, assessment_day=day, embryologist_id=str(user.id))
        db.add(a)
    a.assessment_time = now()
    for f in ("cell_count", "fragmentation_pct", "symmetry", "multinucleation", "overall_grade", "is_suitable_transfer", "is_suitable_freeze", "notes"):
        if f in body:
            setattr(a, f, body[f])
    if body.get("expansion"):
        a.expansion = BlastocystExpansion(str(body["expansion"]))
    if body.get("icm_grade"):
        a.icm_grade = ICMGrade(body["icm_grade"])
    if body.get("te_grade"):
        a.te_grade = TEGrade(body["te_grade"])
    if not a.overall_grade:
        a.overall_grade = _gardner(a)
    e.current_day = max(e.current_day or 1, day)
    if body.get("disposition"):
        e.disposition = EmbryoDisposition(body["disposition"])
    if "pgta_result" in body:
        e.is_pgta_tested = True
        e.pgta_result = body["pgta_result"]
    db.flush()
    events.emit(db, "observation.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"day": day, "kind": "assessment", "embryo": e.embryo_code, "grade": a.overall_grade})
    db.commit()
    return observation(db, c)


def freeze_embryo(db: Session, c: TreatmentCycle, embryo_id: str, body: dict, user: User) -> dict:
    e = db.query(Embryo).filter(Embryo.id == embryo_id, Embryo.cycle_id == c.id).first()
    if not e:
        raise HTTPException(404, "Embryo not found in this cycle")
    cp = e.cryopreservation or EmbryoCryopreservation(embryo_id=e.id, embryologist_id=str(user.id), freeze_date=now())
    for f in ("method", "device", "device_label", "tank_id", "canister", "goblet", "position", "cryo_medium", "notes"):
        if f in body:
            setattr(cp, f, body[f])
    cp.method = cp.method or "vitrification"
    cp.device = cp.device or "cryotop"
    db.add(cp)
    e.disposition = EmbryoDisposition.FROZEN
    db.flush()
    # label the device as a lab item so warming can be witnessed by scan
    from .lab_tasks import ensure_items  # noqa
    from ..models.journey_models import LabItem as _LI
    from .common import new_label_code
    if not db.query(_LI).filter(_LI.reference_table == "embryo_cryopreservations", _LI.reference_id == cp.id).first():
        db.add(_LI(label_code=new_label_code(), cycle_id=c.id, patient_id=c.patient_id, item_type="cryo_device",
                   description=f"{e.embryo_code} · {cp.device} · {cp.tank_id or ''}/{cp.canister or ''}/{cp.goblet or ''}/{cp.position or ''}",
                   reference_table="embryo_cryopreservations", reference_id=cp.id))
    db.flush()
    from .cryo import sync_terms_from_lab
    sync_terms_from_lab(db, c, actor_id=user.id)
    db.commit()
    return observation(db, c)


def warm_embryo(db: Session, c: TreatmentCycle, embryo_id: str, body: dict, user: User) -> dict:
    e = db.query(Embryo).filter(Embryo.id == embryo_id).first()
    if not e:
        raise HTTPException(404, "Embryo not found")
    from module2.backend.models.lab_models import WarmingStatus
    w = e.warming or EmbryoWarming(embryo_id=e.id, embryologist_id=str(user.id), warming_date=now(), status=WarmingStatus.SURVIVED)
    if body.get("status"):
        w.status = WarmingStatus(body["status"])
    for f in ("blastomeres_intact_pct", "post_warm_grade", "warming_medium", "notes"):
        if f in body:
            setattr(w, f, body[f])
    db.add(w)
    e.disposition = EmbryoDisposition.THAWED
    db.flush()
    events.emit(db, "observation.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"kind": "warming", "embryo": e.embryo_code, "status": w.status.value})
    db.commit()
    return observation(db, c)


def transfer_embryos(db: Session, c: TreatmentCycle, body: dict, user: User) -> dict:
    """body: {embryo_ids: [...], transfer_type, endometrial_thickness, catheter_type, difficulty, ultrasound_guided, notes}"""
    ids = body.get("embryo_ids") or []
    if not ids:
        raise HTTPException(400, "embryo_ids required")
    for eid in ids:
        e = db.query(Embryo).filter(Embryo.id == eid).first()
        if not e:
            continue
        tr = e.transfer or EmbryoTransfer(embryo_id=e.id, patient_id=c.patient_id, cycle_id=c.id, transfer_date=now(),
                                          physician_id=c.physician_id or str(user.id), embryologist_id=str(user.id))
        for f in ("transfer_type", "endometrial_thickness", "catheter_type", "difficulty", "ultrasound_guided", "embryo_position_mm", "notes"):
            if f in body:
                setattr(tr, f, body[f])
        tr.transfer_type = tr.transfer_type or ("frozen" if c.cycle_type.startswith("fet") else "fresh")
        db.add(tr)
        e.disposition = EmbryoDisposition.FRESH_TRANSFER if tr.transfer_type == "fresh" else EmbryoDisposition.THAWED
    c.status = "luteal"
    db.flush()
    events.emit(db, "observation.recorded", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"kind": "transfer", "count": len(ids)})
    db.commit()
    return observation(db, c)


# ─────────────────────────────────────────────────────────────────────────────
# Photos / album
# ─────────────────────────────────────────────────────────────────────────────
def photo_dir() -> Path:
    p = Path(settings.UPLOAD_DIR) / "embryo_photos"
    p.mkdir(parents=True, exist_ok=True)
    return p


async def save_photo(db: Session, c: TreatmentCycle, file: UploadFile, user: User, *, embryo_id=None, oocyte_id=None,
                     lab_day=None, caption_en=None, caption_th=None, source="upload", release=False) -> EmbryoPhoto:
    ext = Path(file.filename or "photo.jpg").suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
        raise HTTPException(400, "Unsupported image type")
    name = f"{c.cycle_number}_{lab_day if lab_day is not None else 'x'}_{uuid.uuid4().hex[:8]}{ext}"
    path = photo_dir() / name
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")
    path.write_bytes(data)
    ph = EmbryoPhoto(cycle_id=c.id, embryo_id=embryo_id, oocyte_id=oocyte_id, lab_day=lab_day, path=str(path),
                     caption_en=caption_en, caption_th=caption_th, source=source, taken_by=str(user.id))
    db.add(ph)
    db.flush()
    if embryo_id:
        e = db.query(Embryo).filter(Embryo.id == embryo_id).first()
        a = db.query(EmbryoAssessment).filter(EmbryoAssessment.embryo_id == embryo_id, EmbryoAssessment.assessment_day == (lab_day or 0)).first() if e else None
        if a and not a.image_path:
            a.image_path = str(path)
    if release:
        release_photos(db, c, [ph.id], user)
    db.commit()
    db.refresh(ph)
    return ph


def release_photos(db: Session, c: TreatmentCycle, photo_ids: list[str], user: User) -> int:
    n = 0
    for pid in photo_ids:
        ph = db.query(EmbryoPhoto).filter(EmbryoPhoto.id == pid, EmbryoPhoto.cycle_id == c.id).first()
        if ph and not ph.released_to_patient:
            ph.released_to_patient, ph.released_at, ph.released_by = True, now(), str(user.id)
            n += 1
    if n:
        events.emit(db, "album.released", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id, payload={"count": n})
    db.commit()
    return n
