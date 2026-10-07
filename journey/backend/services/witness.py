"""
Electronic witnessing (adapted from Infans EWS).

A witness session belongs to one lab task. The embryologist scans every item the step needs
(QR on each label → LabItem → cycle/patient). Rule: all items must resolve to the same cycle —
or, for sperm items, to the linked partner of that cycle. Match → the task is done and the
mapped EMR timestamp is written back. Mismatch → hard stop, incident, task stays pending.
Manual double-witness (second staff member authenticates) is recorded as `manual`.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module1.backend.models.user_models import User
from module1.backend.core.security import verify_password
from module2.backend.models.lab_models import (
    TreatmentCycle, OocyteRetrieval, Oocyte, FertilizationRecord, Embryo,
    EmbryoCryopreservation, EmbryoWarming, EmbryoTransfer, SpermPreparation, SemenAnalysis,
)

from ..models.journey_models import LabTask, LabItem, WitnessSession, WitnessScan, WitnessIncident
from . import events
from .common import now, next_number, row
from .lab_tasks import consent_block, mark_done


def _task(db: Session, task_id: str) -> LabTask:
    t = db.query(LabTask).filter(LabTask.id == str(task_id)).first()
    if not t:
        raise HTTPException(404, "Lab task not found")
    return t


def start_session(db: Session, task_id: str, user: User, device: str | None = None) -> WitnessSession:
    t = _task(db, task_id)
    if t.status == "done":
        raise HTTPException(409, "Task already done")
    blocked = consent_block(db, t)
    if blocked:
        raise HTTPException(409, f"Blocked by unsigned consent: {', '.join(blocked)}")
    # abandon any open session for this task
    for s in db.query(WitnessSession).filter(WitnessSession.lab_task_id == t.id, WitnessSession.completed_at == None).all():
        s.result, s.completed_at = "abandoned", now()
    s = WitnessSession(lab_task_id=t.id, cycle_id=t.cycle_id, user_id=str(user.id), device=device,
                       items_expected=list(t.items_required or []), items_scanned=[])
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _resolve(db: Session, payload: str, cycle: TreatmentCycle):
    """payload → (label_code, item_type, lab_item, resolved_cycle_id, resolved_patient_id, message)"""
    p = (payload or "").strip()
    if p.upper().startswith("LBL-"):
        it = db.query(LabItem).filter(LabItem.label_code == p.upper(), LabItem.is_active == True).first()
        if not it:
            return p, None, None, None, None, "Unknown label"
        return it.label_code, it.item_type, it, it.cycle_id, it.patient_id, None
    if p.upper().startswith("HN:") or p.upper().startswith("HN-"):
        hn = p[3:] if p[2] == ":" else p
        pt = db.query(Patient).filter(Patient.hn_number == hn).first()
        if not pt:
            return p, "wristband", None, None, None, "Unknown HN"
        # a patient wristband belongs to the cycle if it is the patient or the partner
        cyc_id = cycle.id if str(pt.id) in (str(cycle.patient_id), str(cycle.partner_id or "")) else None
        return p, "wristband", None, cyc_id, str(pt.id), None
    return p, None, None, None, None, "Unrecognised code"


def scan(db: Session, session_id: str, payload: str, user: User) -> dict:
    s = db.query(WitnessSession).filter(WitnessSession.id == str(session_id)).first()
    if not s or s.completed_at:
        raise HTTPException(404, "Session not open")
    t = _task(db, s.lab_task_id)
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == s.cycle_id).first()
    code, item_type, it, rc, rp, msg = _resolve(db, payload, c)
    matched = (rc is not None and str(rc) == str(c.id))
    sc = WitnessScan(session_id=s.id, raw_payload=payload, label_code=code, item_type=item_type,
                     lab_item_id=it.id if it else None, resolved_cycle_id=rc, resolved_patient_id=rp,
                     matched=matched, message=msg or ("match" if matched else "MISMATCH — different patient/cycle"))
    db.add(sc)
    scanned = list(s.items_scanned or [])
    if matched and item_type:
        scanned.append(item_type)
        s.items_scanned = scanned
    if not matched:
        s.error_count = (s.error_count or 0) + 1
        s.result, s.completed_at = "mismatch", now()
        inc = WitnessIncident(session_id=s.id, cycle_id=c.id, lab_task_id=t.id, severity="high", created_by=str(user.id),
                              description=f"Mismatch at {t.key} (D{t.lab_day}): scanned '{payload}' resolved to cycle "
                                          f"{rc or 'unknown'} / patient {rp or 'unknown'} — expected cycle {c.cycle_number}")
        db.add(inc)
        db.flush()
        events.emit(db, "witness.mismatch", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                    payload={"task_id": t.id, "key": t.key, "payload": payload, "resolved_cycle": rc, "incident_id": inc.id})
        db.commit()
        return {"status": "mismatch", "message": sc.message, "incident_id": inc.id, "session": row(s)}

    expected = set(s.items_expected or [])
    missing = sorted(expected - set(scanned))
    if missing:
        db.commit()
        return {"status": "partial", "message": f"Scanned {item_type}. Still needed: {', '.join(missing)}",
                "missing": missing, "session": row(s)}

    # all expected items matched → complete
    s.result, s.completed_at = "match", now()
    t.witness_session_id = s.id
    _write_back(db, t, c, user)
    mark_done(db, t, user.id, via="witness")
    events.emit(db, "witness.match", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"task_id": t.id, "key": t.key, "lab_day": t.lab_day, "session_id": s.id, "items": scanned})
    db.commit()
    return {"status": "match", "message": "All items match — step witnessed", "session": row(s)}


def manual_witness(db: Session, task_id: str, user: User, second_email: str, second_password: str, note: str | None = None) -> dict:
    """Two-person manual witness when no scanner/camera is available."""
    t = _task(db, task_id)
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == t.cycle_id).first()
    second = db.query(User).filter(User.email == second_email, User.is_active == True).first()
    if not second or not verify_password(second_password, second.password_hash):
        raise HTTPException(401, "Second witness credentials invalid")
    if str(second.id) == str(user.id):
        raise HTTPException(400, "Second witness must be a different person")
    blocked = consent_block(db, t)
    if blocked:
        raise HTTPException(409, f"Blocked by unsigned consent: {', '.join(blocked)}")
    s = WitnessSession(lab_task_id=t.id, cycle_id=t.cycle_id, user_id=str(user.id), second_user_id=str(second.id),
                       result="manual", completed_at=now(), items_expected=list(t.items_required or []),
                       items_scanned=["manual"], notes=note)
    db.add(s)
    db.flush()
    t.witness_session_id = s.id
    _write_back(db, t, c, user)
    mark_done(db, t, user.id, via="witness", notes=f"manual double-witness with {second.email}")
    events.emit(db, "witness.manual", cycle_id=c.id, patient_id=c.patient_id, actor_id=user.id,
                payload={"task_id": t.id, "key": t.key, "second_user": second.email})
    db.commit()
    return {"status": "manual", "session": row(s)}


def _write_back(db: Session, t: LabTask, c: TreatmentCycle, user: User):
    """Fill the mapped EMR timestamp (Infans: 'scan timepoints fill EMR fields')."""
    ts = now()
    wb = t.write_back
    if wb == "opu.start_time":
        r = db.query(OocyteRetrieval).filter(OocyteRetrieval.cycle_id == c.id).first()
        if not r:
            r = OocyteRetrieval(patient_id=c.patient_id, cycle_id=c.id, procedure_date=ts.date(),
                                physician_id=c.physician_id or str(user.id), embryologist_id=str(user.id))
            db.add(r)
        r.start_time = r.start_time or ts
    elif wb == "oocyte.insemination_time":
        method = "ICSI" if t.key == "icsi" else "IVF"
        r = db.query(OocyteRetrieval).filter(OocyteRetrieval.cycle_id == c.id).first()
        if r:
            for o in db.query(Oocyte).filter(Oocyte.retrieval_id == r.id, Oocyte.is_inseminated == False).all():
                o.is_inseminated, o.insemination_method, o.insemination_time = True, method, ts
    elif wb == "fertilization.check_time":
        for fr in db.query(FertilizationRecord).filter(FertilizationRecord.patient_id == c.patient_id,
                                                        FertilizationRecord.check_time == None).all():
            fr.check_time = ts
    elif wb == "sperm_prep.prepared_at":
        sp = db.query(SpermPreparation).filter(SpermPreparation.cycle_id == c.id).first()
        if not sp:
            sp = SpermPreparation(cycle_id=c.id, patient_id=c.partner_id or c.patient_id, embryologist_id=str(user.id))
            db.add(sp)
        sp.prepared_at = sp.prepared_at or ts
    elif wb == "semen.collected_at":
        owner = c.partner_id or c.patient_id
        sa = db.query(SemenAnalysis).filter(SemenAnalysis.patient_id == owner, SemenAnalysis.collected_at == None).first()
        if not sa:
            sa = SemenAnalysis(analysis_number=next_number(db, SemenAnalysis, SemenAnalysis.analysis_number, "SA"),
                               patient_id=owner, analyst_id=str(user.id))
            db.add(sa)
        sa.collected_at = ts
    elif wb == "cryo.freeze_date":
        for e in db.query(Embryo).filter(Embryo.cycle_id == c.id).all():
            if e.cryopreservation and not e.cryopreservation.verified_by_id:
                e.cryopreservation.verified_by_id = str(user.id)
    elif wb == "warming.warming_date":
        for w in db.query(EmbryoWarming).join(Embryo, Embryo.id == EmbryoWarming.embryo_id).filter(
                Embryo.patient_id == c.patient_id, EmbryoWarming.verified_by_id == None).all():
            w.verified_by_id = str(user.id)
    elif wb == "transfer.transfer_date":
        for tr in db.query(EmbryoTransfer).filter(EmbryoTransfer.cycle_id == c.id).all():
            tr.embryologist_id = tr.embryologist_id or str(user.id)
    # other keys (assessment.time, biopsy.time, iui.time, procedure.time): the task's done_at is the record
    db.flush()


def scan_record(db: Session, cycle_id: str) -> list[dict]:
    out = []
    for s in db.query(WitnessSession).filter(WitnessSession.cycle_id == str(cycle_id)).order_by(WitnessSession.started_at).all():
        d = row(s)
        d["scans"] = [row(x) for x in s.scans]
        t = db.query(LabTask).filter(LabTask.id == s.lab_task_id).first()
        d["task_key"], d["lab_day"] = (t.key, t.lab_day) if t else (None, None)
        u = db.query(User).filter(User.id == s.user_id).first()
        d["witness"] = f"{u.first_name_en} {u.last_name_en}" if u else None
        out.append(d)
    return out


def errors_count(db: Session, cycle_id: str) -> int:
    return db.query(WitnessIncident).filter(WitnessIncident.cycle_id == str(cycle_id)).count()
