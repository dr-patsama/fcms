"""
Cycle consents: e-signature capture (clinic tablet or patient app) → signed PDF with the
template text, signature image, signer identity, timestamp, and SHA-256 of the document.
Also mirrors into Module 1 consent_forms so the EMR consent list stays complete.
"""
from __future__ import annotations

import base64
import hashlib
import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from module1.backend.core.config import settings
from module1.backend.models.emr_models import Patient, ConsentForm
from module2.backend.models.lab_models import TreatmentCycle

from ..core.config import jsettings
from ..models.journey_models import CycleConsent, ConsentTemplate
from . import events
from .common import now, th_date, patient_name
from .labels import _fonts, _font


def consent_dir() -> Path:
    p = Path(settings.UPLOAD_DIR) / "consents"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _wrap(text: str, width_chars: int) -> list[str]:
    out = []
    for para in (text or "").split("\n"):
        line = ""
        for word in para.split(" "):
            if len(line) + len(word) + 1 > width_chars:
                out.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        out.append(line)
    return out


def build_pdf(db: Session, cc: CycleConsent, signature_png: bytes | None, signer_name: str, channel: str) -> bytes:
    _fonts()
    t = db.query(ConsentTemplate).filter(ConsentTemplate.id == cc.template_id).first() if cc.template_id else None
    p = db.query(Patient).filter(Patient.id == cc.patient_id).first()
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == cc.cycle_id).first()
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 25 * mm
    pdf.setFont(_font(True), 14)
    pdf.drawString(20 * mm, y, jsettings.CLINIC_NAME_EN)
    pdf.setFont(_font(), 10)
    pdf.drawString(20 * mm, y - 5 * mm, jsettings.CLINIC_NAME_TH)
    y -= 16 * mm
    pdf.setFont(_font(True), 13)
    pdf.drawString(20 * mm, y, (t.title_en if t else cc.consent_type))
    y -= 6 * mm
    pdf.setFont(_font(), 11)
    pdf.drawString(20 * mm, y, (t.title_th if t else ""))
    y -= 9 * mm
    pdf.setFont(_font(), 10)
    pdf.drawString(20 * mm, y, f"Patient: {patient_name(p)}  HN {p.hn_number if p else ''}   Cycle: {c.cycle_number if c else ''}   Version {cc.template_version or ''}")
    y -= 9 * mm
    for block in ((t.body_en if t else ""), (t.body_th if t else "")):
        for line in _wrap(block, 95):
            pdf.drawString(20 * mm, y, line)
            y -= 5 * mm
            if y < 60 * mm:
                pdf.showPage(); pdf.setFont(_font(), 10); y = h - 25 * mm
        y -= 4 * mm
    y -= 6 * mm
    pdf.setFont(_font(True), 10)
    pdf.drawString(20 * mm, y, f"Signed by: {signer_name}    Date: {th_date(now().date())} ({now().strftime('%Y-%m-%d %H:%M')})    Channel: {channel}")
    if signature_png:
        try:
            pdf.drawImage(ImageReader(io.BytesIO(signature_png)), 20 * mm, y - 32 * mm, 60 * mm, 25 * mm, mask="auto")
        except Exception:
            pass
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def sign(db: Session, cc: CycleConsent, *, signature_data_url: str | None, signer_patient_id: str | None,
         channel: str, witness_user_id=None, ip: str | None = None, actor_id=None) -> CycleConsent:
    if cc.status == "signed":
        return cc
    png = None
    if signature_data_url and "," in signature_data_url:
        png = base64.b64decode(signature_data_url.split(",", 1)[1])
    signer = db.query(Patient).filter(Patient.id == signer_patient_id).first() if signer_patient_id else None
    signer_name = patient_name(signer) if signer else "patient"
    pdf = build_pdf(db, cc, png, signer_name, channel)
    name = f"{cc.cycle_id}_{cc.consent_type}_{uuid.uuid4().hex[:6]}.pdf"
    path = consent_dir() / name
    path.write_bytes(pdf)
    sig_path = None
    if png:
        sig_path = consent_dir() / name.replace(".pdf", "_sig.png")
        sig_path.write_bytes(png)
    cc.status, cc.signed_at, cc.signed_channel = "signed", now(), channel
    cc.signed_by_patient_id = str(signer_patient_id) if signer_patient_id else None
    cc.document_path, cc.signature_path = str(path), str(sig_path) if sig_path else None
    cc.document_hash = hashlib.sha256(pdf).hexdigest()
    cc.witness_user_id = str(witness_user_id) if witness_user_id else None
    cc.ip_address = ip
    # mirror into Module 1
    cf = ConsentForm(patient_id=cc.patient_id, consent_type=cc.consent_type, version=cc.template_version, signed_at=cc.signed_at,
                     witness_name=None, document_path=str(path), is_active=True)
    db.add(cf)
    db.flush()
    cc.consent_form_id = cf.id
    events.emit(db, "consent.signed", cycle_id=cc.cycle_id, patient_id=cc.patient_id, actor_id=actor_id,
                payload={"consent_type": cc.consent_type, "channel": channel})
    db.commit()
    db.refresh(cc)
    return cc
