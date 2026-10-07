"""
Cryo inventory ↔ storage billing ↔ patient (Binflux: cryo inventory / due-date & billing lists /
expiry push / online payment). Storage terms wrap the Module 2 cryo rows; invoices are
Module 7 invoices; reminders go through notifications.py.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import desc
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module2.backend.models.lab_models import TreatmentCycle, Embryo, EmbryoCryopreservation, SpermCryopreservation
from module7.backend.models.accounting_models import Invoice, InvoiceItem, Payment

from ..core.config import jsettings
from ..models.journey_models import CryoStorageTerm, TreatmentPackage
from . import events, notifications
from .common import now, today, row, patient_name


def _add_months(d: date, months: int) -> date:
    y, m = d.year + (d.month - 1 + months) // 12, (d.month - 1 + months) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def storage_fee_for(db: Session, cycle: TreatmentCycle | None) -> Decimal:
    if cycle and cycle.package_id:
        pkg = db.query(TreatmentPackage).filter(TreatmentPackage.id == cycle.package_id).first()
        for b in (pkg.billing_items or []) if pkg else []:
            if b.get("when") == "storage_year":
                return Decimal(str(b.get("amount") or 0))
    return Decimal("0")


def open_term(db: Session, *, patient_id: str, cycle_id: str | None, content_type: str, reference_table: str,
              reference_ids: list[str], stored_at: date | None = None, months: int | None = None, actor_id=None) -> CryoStorageTerm:
    stored_at = stored_at or today()
    months = months or jsettings.CRYO_TERM_MONTHS
    cycle = db.query(TreatmentCycle).filter(TreatmentCycle.id == cycle_id).first() if cycle_id else None
    t = CryoStorageTerm(patient_id=str(patient_id), cycle_id=str(cycle_id) if cycle_id else None, content_type=content_type,
                        reference_table=reference_table, reference_ids=[str(x) for x in reference_ids],
                        device_count=len(reference_ids) or 1, stored_at=stored_at, paid_until=_add_months(stored_at, months),
                        term_months=months, annual_fee=storage_fee_for(db, cycle), status="active")
    db.add(t)
    db.flush()
    if t.annual_fee and t.annual_fee > 0:
        issue_storage_invoice(db, t, actor_id=actor_id, note="initial storage term")
    events.emit(db, "cryo.stored", cycle_id=cycle_id, patient_id=patient_id, actor_id=actor_id,
                payload={"term_id": t.id, "content_type": content_type, "count": t.device_count, "paid_until": str(t.paid_until)})
    db.commit()
    db.refresh(t)
    return t


def sync_terms_from_lab(db: Session, cycle: TreatmentCycle, actor_id=None) -> list[CryoStorageTerm]:
    """Create storage terms for cryo rows that do not have one yet (called on vitrification done / nightly)."""
    out = []
    covered = set()
    for t in db.query(CryoStorageTerm).filter(CryoStorageTerm.patient_id == cycle.patient_id).all():
        covered.update(t.reference_ids or [])
    embryo_cryos = [c for c in db.query(EmbryoCryopreservation).join(Embryo, Embryo.id == EmbryoCryopreservation.embryo_id)
                    .filter(Embryo.cycle_id == cycle.id).all() if str(c.id) not in covered]
    if embryo_cryos:
        # one storage term per cycle + content type: extend it when more embryos of the same cycle are frozen
        existing = db.query(CryoStorageTerm).filter(CryoStorageTerm.cycle_id == cycle.id, CryoStorageTerm.content_type == "embryo",
                                                    CryoStorageTerm.status.in_(("active", "due", "overdue"))).first()
        if existing:
            existing.reference_ids = list(existing.reference_ids or []) + [str(c.id) for c in embryo_cryos]
            existing.device_count = len(existing.reference_ids)
            db.commit()
            out.append(existing)
        else:
            out.append(open_term(db, patient_id=cycle.patient_id, cycle_id=cycle.id, content_type="embryo",
                                 reference_table="embryo_cryopreservations", reference_ids=[c.id for c in embryo_cryos],
                                 stored_at=min(c.freeze_date for c in embryo_cryos).date(), actor_id=actor_id))
    return out


def issue_storage_invoice(db: Session, t: CryoStorageTerm, actor_id=None, note: str | None = None) -> Invoice:
    from module7.backend.api.accounting_routes import _next_number
    fee = Decimal(str(t.annual_fee or 0))
    inv = Invoice(id=str(uuid.uuid4()), invoice_number=_next_number(db, Invoice, Invoice.invoice_number, "INV"),
                  patient_id=t.patient_id, invoice_date=today(), due_date=t.paid_until, status="issued",
                  subtotal=fee, discount_amount=0, vat_amount=0, total_amount=fee, paid_amount=0, balance_due=fee,
                  notes=f"Cryo storage {t.content_type} · {t.term_months} months · {note or ''}".strip(),
                  notes_th=f"ค่าฝากแช่แข็ง{notifications.CONTENT_TH.get(t.content_type, t.content_type)} {t.term_months} เดือน",
                  created_by=str(actor_id) if actor_id else None)
    db.add(inv)
    db.flush()
    db.add(InvoiceItem(invoice_id=inv.id, description=f"Storage fee — {t.content_type} ({t.device_count} device(s)), {t.term_months} months",
                       description_th=f"ค่าฝากแช่แข็ง{notifications.CONTENT_TH.get(t.content_type, '')} {t.device_count} ชิ้น {t.term_months} เดือน",
                       category="cryo_storage", quantity=1, unit_price=fee, vat_rate=0, line_total=fee))
    t.invoice_id = inv.id
    db.flush()
    events.emit(db, "invoice.issued", cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id,
                payload={"invoice_id": inv.id, "amount": float(fee), "term_id": t.id})
    return inv


def renew(db: Session, t: CryoStorageTerm, months: int | None = None, *, payment_method: str | None = None,
          reference: str | None = None, actor_id=None) -> CryoStorageTerm:
    months = months or t.term_months or jsettings.CRYO_TERM_MONTHS
    base = max(t.paid_until, today())
    t.paid_until = _add_months(base, months)
    t.status = "active"
    t.reminders_sent = 0
    fee = Decimal(str(t.annual_fee or 0))
    if fee > 0:
        inv = issue_storage_invoice(db, t, actor_id=actor_id, note="renewal")
        if payment_method:
            from module7.backend.api.accounting_routes import _next_number, _recalc_invoice_payment_state
            db.add(Payment(id=str(uuid.uuid4()), receipt_number=_next_number(db, Payment, Payment.receipt_number, "RC"),
                           invoice_id=inv.id, patient_id=t.patient_id, payment_date=today(), amount=fee, method=payment_method,
                           reference_number=reference, received_by=str(actor_id) if actor_id else None))
            db.flush()
            _recalc_invoice_payment_state(inv, db)
            events.emit(db, "payment.received", cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id,
                        payload={"invoice_id": inv.id, "amount": float(fee), "method": payment_method})
    events.emit(db, "cryo.renewed", cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id,
                payload={"term_id": t.id, "paid_until": str(t.paid_until)})
    db.commit()
    db.refresh(t)
    return t


def set_status(db: Session, t: CryoStorageTerm, status: str, actor_id=None, note: str | None = None) -> CryoStorageTerm:
    t.status = status
    if note:
        t.notes = (t.notes + "\n" if t.notes else "") + note
    ev = {"thawed": "cryo.thawed", "discarded": "cryo.discarded", "transferred_out": "cryo.discarded"}.get(status)
    if ev:
        events.emit(db, ev, cycle_id=t.cycle_id, patient_id=t.patient_id, actor_id=actor_id, payload={"term_id": t.id})
    db.commit()
    return t


def run_renewal_reminders(db: Session) -> dict:
    """Daily job: mark due/overdue, send reminders at the configured days-before (60/30/7 by default)."""
    t0 = today()
    sent, due, overdue = 0, 0, 0
    for t in db.query(CryoStorageTerm).filter(CryoStorageTerm.status.in_(("active", "due", "overdue"))).all():
        days = (t.paid_until - t0).days
        if days < -jsettings.CRYO_GRACE_DAYS:
            t.status = "overdue"
            overdue += 1
        elif days <= min(jsettings.cryo_reminder_days):
            t.status = "due"
            due += 1
        # reminder thresholds: fire once per threshold crossing
        crossed = [d for d in jsettings.cryo_reminder_days if days <= d]
        n_should = len(crossed)
        if n_should > (t.reminders_sent or 0):
            notifications.notify(db, t.patient_id, "cryo.renewal_due",
                                 {"content": t.content_type, "date": str(t.paid_until), "days": max(days, 0)},
                                 cycle_id=t.cycle_id)
            events.emit(db, "cryo.renewal_due", cycle_id=t.cycle_id, patient_id=t.patient_id,
                        payload={"term_id": t.id, "days": days, "paid_until": str(t.paid_until)})
            t.reminders_sent = n_should
            t.last_reminder_at = now()
            sent += 1
    db.commit()
    return {"reminders_sent": sent, "due": due, "overdue": overdue}


def due_list(db: Session, within_days: int = 90) -> list[dict]:
    limit = today() + timedelta(days=within_days)
    out = []
    for t in db.query(CryoStorageTerm).filter(CryoStorageTerm.status.in_(("active", "due", "overdue")),
                                              CryoStorageTerm.paid_until <= limit).order_by(CryoStorageTerm.paid_until).all():
        d = row(t)
        p = db.query(Patient).filter(Patient.id == t.patient_id).first()
        d.update({"hn": p.hn_number if p else None, "patient_en": patient_name(p), "patient_th": patient_name(p, "th"),
                  "days_left": (t.paid_until - today()).days, "phone": p.phone if p else None})
        inv = db.query(Invoice).filter(Invoice.id == t.invoice_id).first() if t.invoice_id else None
        d["invoice"] = {"number": inv.invoice_number, "status": inv.status, "balance_due": float(inv.balance_due or 0)} if inv else None
        out.append(d)
    return out


def inventory_for_patient(db: Session, patient_id: str) -> dict:
    """What the patient (and the lab) sees: embryos / oocytes / sperm in storage with locations and terms."""
    embryos = []
    for e in db.query(Embryo).filter(Embryo.patient_id == str(patient_id)).all():
        cp = e.cryopreservation
        if not cp:
            continue
        last = e.assessments[-1] if e.assessments else None
        embryos.append({"embryo_code": e.embryo_code, "cycle_id": e.cycle_id, "day": last.assessment_day if last else None,
                        "grade": last.overall_grade if last else None, "pgta": e.pgta_result, "disposition": e.disposition.value if e.disposition else None,
                        "freeze_date": str(cp.freeze_date.date()), "device": cp.device, "device_label": cp.device_label,
                        "tank": cp.tank_id, "canister": cp.canister, "goblet": cp.goblet, "position": cp.position,
                        "cryo_id": cp.id, "status": "thawed" if e.warming else "stored"})
    sperm = [row(s) for s in db.query(SpermCryopreservation).filter(SpermCryopreservation.patient_id == str(patient_id)).all()]
    terms = [row(t) for t in db.query(CryoStorageTerm).filter(CryoStorageTerm.patient_id == str(patient_id)).order_by(desc(CryoStorageTerm.paid_until)).all()]
    return {"embryos": embryos, "sperm": sperm, "terms": terms}
