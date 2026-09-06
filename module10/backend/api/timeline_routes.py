"""
FCMS Module 10 — Cycle Plan / Timeline Generator API

Keeps the exact wire contract the Timeline Generator UI already uses
(GET /list → array of documents; POST /save with type json|jpg|pdf|delete),
but persists to PostgreSQL and links each timeline to the EMR patient by HN.
Also exposes REST-style endpoints for other modules (patient app, CRM, OR).
"""
import base64
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..core.config import settings
from ..models.user_models import User, AuditLog
from ..models.timeline_models import CycleTimeline, CycleTimelineFile
from module1.backend.models.emr_models import Patient

router = APIRouter(prefix="/api/v1/timeline", tags=["Cycle Plan / Timeline Generator"])

CLINICAL = ["physician", "nurse", "embryologist", "receptionist", "admin", "it_admin"]
CYCLE_TYPES = {"OPU", "FET", "ORA", "IUI"}


# ── helpers ──────────────────────────────────────────────────────────────────
def _upload_root() -> Path:
    p = Path(settings.UPLOAD_DIR) / "timelines"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_name(name: str) -> str:
    name = (name or "timeline").strip()
    return re.sub(r"[^\w\-. ก-๙]", "_", name)[:200]


def _parse_date(s) -> Optional[date]:
    try:
        return date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _cycle_type(doc: dict) -> Optional[str]:
    v = (doc.get("currentView") or "").replace("Input", "").replace("Output", "").upper()
    return v if v in CYCLE_TYPES else None


ACTION_MAP = {"timeline.save": "UPDATE", "timeline.delete": "DELETE", "timeline.link_patient": "UPDATE",
              "timeline.export.jpg": "CREATE", "timeline.export.pdf": "CREATE"}


def _audit(db, user, action, entity_id, request: Request, detail: str = ""):
    db.add(AuditLog(user_id=user.id, action=ACTION_MAP.get(action, "UPDATE"), module="timeline",
                    resource_type="cycle_timeline", resource_id=str(entity_id)[:50],
                    detail=f"{action} {detail}".strip(),
                    ip_address=request.client.host if request.client else None,
                    user_agent=(request.headers.get("user-agent") or "")[:500]))


def _find_patient(db, hn: str) -> Optional[Patient]:
    if not hn:
        return None
    return db.query(Patient).filter(Patient.hn_number == hn.strip()).first()


def _upsert_document(db, doc: dict, user: User) -> CycleTimeline:
    pd = doc.get("patientData") or {}
    ti = doc.get("timelineInputs") or {}
    legacy_id = doc.get("id")
    row = None
    if legacy_id is not None:
        row = db.query(CycleTimeline).filter(CycleTimeline.legacy_id == int(legacy_id)).first()
    if row is None:
        row = CycleTimeline(legacy_id=int(legacy_id) if legacy_id is not None else None, created_by=user.id)
        db.add(row)
    patient = _find_patient(db, pd.get("hn"))
    row.patient_id = patient.id if patient else None
    row.hn = (pd.get("hn") or "").strip() or None
    row.first_name = pd.get("name")
    row.last_name = pd.get("lastName")
    row.cycle_type = _cycle_type(doc)
    row.protocol = ti.get("protocol")
    row.lmp = _parse_date(pd.get("lmp"))
    row.day1_date = _parse_date(ti.get("ovulationDate")) if ti.get("protocol") == "Luteal stimulation" else row.lmp
    row.generated_at = _parse_dt(doc.get("timestamp"))
    row.document = doc
    row.is_active = True
    db.flush()
    return row


def _parse_dt(s) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")) if s else None
    except ValueError:
        return None


# ── legacy contract (used by the generator UI) ──────────────────────────────
@router.get("/list")
def list_documents(
    hn: Optional[str] = Query(None, description="Filter by HN"),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("emr")),
):
    """Returns generator documents newest-first — same shape the UI already parses."""
    q = db.query(CycleTimeline).filter(CycleTimeline.is_active == True)
    if hn:
        q = q.filter(CycleTimeline.hn == hn.strip())
    rows = q.order_by(desc(CycleTimeline.generated_at), desc(CycleTimeline.created_at)).limit(limit).all()
    return [r.document for r in rows]


@router.post("/save")
async def save(request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_roles(CLINICAL))):
    body = await request.json()
    kind = body.get("type")
    filename = _safe_name(body.get("filename") or "")
    content = body.get("content")

    if kind == "json":
        if not isinstance(content, dict):
            raise HTTPException(400, "content must be the timeline document")
        row = _upsert_document(db, content, user)
        _audit(db, user, "timeline.save", row.id, request, f"{row.cycle_type} {row.hn}")
        db.commit()
        return {"status": "success", "id": str(row.id), "legacy_id": row.legacy_id,
                "patient_linked": row.patient_id is not None,
                "path": f"FCMS · {row.cycle_type or 'timeline'} · {row.hn or ''}".strip()}

    if kind in ("jpg", "pdf"):
        if not content:
            raise HTTPException(400, "empty content")
        encoded = content.split(",", 1)[1] if "," in content else content
        data = base64.b64decode(encoded)
        legacy_id = body.get("id")
        row = None
        if legacy_id is not None:
            row = db.query(CycleTimeline).filter(CycleTimeline.legacy_id == int(legacy_id)).first()
        if row is None:  # fall back: newest doc whose filename prefix matches HN
            hn = filename.split(" ")[0] if filename else None
            row = (db.query(CycleTimeline).filter(CycleTimeline.hn == hn, CycleTimeline.is_active == True)
                   .order_by(desc(CycleTimeline.created_at)).first()) if hn else None
        folder = _upload_root() / (str(row.id) if row else "_unlinked")
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = folder / f"{filename}_{stamp}.{kind}"
        path.write_bytes(data)
        if row:
            db.add(CycleTimelineFile(timeline_id=row.id, kind=kind, filename=path.name, path=str(path)))
            _audit(db, user, f"timeline.export.{kind}", row.id, request, path.name)
            db.commit()
        return {"status": "success", "filepath": str(path), "path": f"FCMS uploads/timelines/{path.parent.name}/{path.name}"}

    if kind == "delete":
        legacy_id = body.get("id")
        row = db.query(CycleTimeline).filter(CycleTimeline.legacy_id == int(legacy_id)).first() if legacy_id is not None else None
        if row:
            row.is_active = False
            _audit(db, user, "timeline.delete", row.id, request)
            db.commit()
        return {"status": "success"}

    raise HTTPException(400, f"unknown type '{kind}'")


# ── REST endpoints for other modules ────────────────────────────────────────
@router.get("/")
def search_timelines(
    hn: Optional[str] = None, patient_id: Optional[str] = None,
    cycle_type: Optional[str] = None, q: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db), user: User = Depends(require_module_access("emr")),
):
    qry = db.query(CycleTimeline).filter(CycleTimeline.is_active == True)
    if hn:
        qry = qry.filter(CycleTimeline.hn == hn.strip())
    if patient_id:
        qry = qry.filter(CycleTimeline.patient_id == patient_id)
    if cycle_type:
        qry = qry.filter(CycleTimeline.cycle_type == cycle_type.upper())
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(CycleTimeline.hn.ilike(like), CycleTimeline.first_name.ilike(like),
                             CycleTimeline.last_name.ilike(like)))
    rows = qry.order_by(desc(CycleTimeline.generated_at)).limit(limit).all()
    return [{
        "id": str(r.id), "legacy_id": r.legacy_id, "patient_id": str(r.patient_id) if r.patient_id else None,
        "hn": r.hn, "first_name": r.first_name, "last_name": r.last_name,
        "cycle_type": r.cycle_type, "protocol": r.protocol, "lmp": r.lmp, "day1_date": r.day1_date,
        "generated_at": r.generated_at, "files": [{"kind": f.kind, "filename": f.filename, "id": str(f.id)} for f in r.files],
    } for r in rows]


@router.get("/{timeline_id}")
def get_timeline(timeline_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_module_access("emr"))):
    r = db.query(CycleTimeline).filter(CycleTimeline.id == timeline_id, CycleTimeline.is_active == True).first()
    if not r:
        raise HTTPException(404, "Timeline not found")
    return {"id": str(r.id), "hn": r.hn, "cycle_type": r.cycle_type, "protocol": r.protocol,
            "patient_id": str(r.patient_id) if r.patient_id else None, "document": r.document,
            "files": [{"kind": f.kind, "filename": f.filename, "id": str(f.id)} for f in r.files]}


@router.get("/files/{file_id}")
def download_file(file_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_module_access("emr"))):
    f = db.query(CycleTimelineFile).filter(CycleTimelineFile.id == file_id).first()
    if not f or not os.path.exists(f.path):
        raise HTTPException(404, "File not found")
    return FileResponse(f.path, filename=f.filename)


@router.post("/{timeline_id}/link-patient")
def link_patient(timeline_id: str, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(CLINICAL))):
    """Re-attempt HN → patient link (e.g. after the patient was registered in EMR)."""
    r = db.query(CycleTimeline).filter(CycleTimeline.id == timeline_id).first()
    if not r:
        raise HTTPException(404, "Timeline not found")
    p = _find_patient(db, r.hn)
    if not p:
        raise HTTPException(404, f"No patient with HN {r.hn}")
    r.patient_id = p.id
    _audit(db, user, "timeline.link_patient", r.id, request, str(p.id))
    db.commit()
    return {"status": "linked", "patient_id": str(p.id)}
