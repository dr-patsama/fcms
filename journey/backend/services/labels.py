"""
QR label printing for lab items (dish-prep stickers, tubes, cryo devices, wristbands).
One PDF page per label at the configured label size (default 40×20 mm, the FCMS lab label size),
so a roll label printer prints them straight through. Cloud font → Thai + English on one label.
Buddhist-calendar date as per FCMS label rules.
"""
from __future__ import annotations

import io
from pathlib import Path

import qrcode
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module2.backend.models.lab_models import TreatmentCycle

from ..core.config import jsettings
from ..models.journey_models import LabItem, LabTask
from .common import now, th_date, patient_name, age_years, to_json

_FONT_READY = False
FONT_DIR = Path(__file__).resolve().parents[3] / "design-system" / "fonts"


def _fonts():
    global _FONT_READY
    if _FONT_READY:
        return
    try:
        pdfmetrics.registerFont(TTFont("Cloud", str(FONT_DIR / "Cloud-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Cloud-Bold", str(FONT_DIR / "Cloud-Bold.ttf")))
        _FONT_READY = True
    except Exception:
        _FONT_READY = False


def _font(bold=False):
    return ("Cloud-Bold" if bold else "Cloud") if _FONT_READY else ("Helvetica-Bold" if bold else "Helvetica")


def _qr(data: str, box=4) -> ImageReader:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box, border=0)
    q.add_data(data)
    q.make(fit=True)
    img = q.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


ITEM_LABEL = {
    "wristband": ("WRISTBAND", "สายรัดข้อมือ"), "opu_tube": ("OPU TUBE", "หลอดเก็บไข่"),
    "oocyte_dish": ("OOCYTE DISH", "จานไข่"), "culture_dish": ("CULTURE DISH", "จานเลี้ยงตัวอ่อน"),
    "sperm_tube": ("SEMEN", "น้ำเชื้อ"), "prep_tube": ("PREP SPERM", "น้ำเชื้อเตรียม"),
    "cryo_device": ("CRYO", "แช่แข็ง"), "straw": ("STRAW", "หลอดแช่แข็ง"), "warming_dish": ("WARMING", "ละลาย"),
    "biopsy_tube": ("BIOPSY", "ชิ้นเนื้อ"), "et_dish": ("ET DISH", "จานย้ายตัวอ่อน"), "iui_catheter": ("IUI", "IUI"),
}


def render_labels(db: Session, items: list[LabItem], *, width_mm: float | None = None, height_mm: float | None = None,
                  copies: int = 1) -> bytes:
    _fonts()
    w = (width_mm or jsettings.LABEL_LAB_WIDTH_MM) * mm
    h = (height_mm or jsettings.LABEL_LAB_HEIGHT_MM) * mm
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    patients = {}
    cycles = {}
    for it in items:
        p = patients.get(it.patient_id) or db.query(Patient).filter(Patient.id == it.patient_id).first()
        patients[it.patient_id] = p
        cy = cycles.get(it.cycle_id) or db.query(TreatmentCycle).filter(TreatmentCycle.id == it.cycle_id).first()
        cycles[it.cycle_id] = cy
        for _ in range(max(1, copies)):
            _draw_label(c, w, h, it, p, cy)
            c.showPage()
    c.save()
    return buf.getvalue()


def _draw_label(c: canvas.Canvas, w, h, it: LabItem, p: Patient, cy: TreatmentCycle):
    pad = 1.2 * mm
    qr_size = h - 2 * pad
    c.drawImage(_qr(it.label_code), pad, pad, qr_size, qr_size)
    x = pad + qr_size + 1.5 * mm
    kind_en, kind_th = ITEM_LABEL.get(it.item_type, (it.item_type.upper(), ""))
    name = patient_name(p, "th") if (p and p.preferred_language == "th" and p.first_name_th) else patient_name(p, "en")
    age = age_years(p.date_of_birth) if p else None
    y = h - pad - 3.2 * mm
    c.setFont(_font(True), 7)
    c.drawString(x, y, (name or "")[:26])
    y -= 3.0 * mm
    c.setFont(_font(), 6)
    hn = p.hn_number if p else ""
    c.drawString(x, y, f"{hn}  {('อายุ ' + str(age)) if age is not None else ''}")
    y -= 3.0 * mm
    c.setFont(_font(True), 6.5)
    c.drawString(x, y, f"{kind_en} {('D' + str(it.lab_day)) if it.lab_day is not None else ''}  {cy.cycle_number if cy else ''}")
    y -= 2.8 * mm
    c.setFont(_font(), 5.5)
    c.drawString(x, y, f"{kind_th}  {th_date(now().date())}  {jsettings.CLINIC_NAME_EN}")
    y -= 2.6 * mm
    c.setFont(_font(), 5)
    c.drawString(x, y, it.label_code)


def items_for_tasks(db: Session, task_ids: list[str]) -> list[LabItem]:
    out, seen = [], set()
    for tid in task_ids:
        t = db.query(LabTask).filter(LabTask.id == tid).first()
        if not t:
            continue
        from .lab_tasks import ensure_items
        cy = db.query(TreatmentCycle).filter(TreatmentCycle.id == t.cycle_id).first()
        for it in ensure_items(db, cy, t):
            if it.id not in seen:
                seen.add(it.id)
                out.append(it)
    return out


def mark_printed(db: Session, items: list[LabItem], user_id, copies: int = 1):
    for it in items:
        it.printed_at = now()
        it.printed_by = str(user_id) if user_id else None
        it.print_count = (it.print_count or 0) + copies
    db.commit()
