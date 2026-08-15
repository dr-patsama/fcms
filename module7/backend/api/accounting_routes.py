"""
FCMS Module 7 — Accounting API Routes / เส้นทาง API บัญชี
Service catalog, invoices, payments/receipts, expenses, daily closings, financial reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_, extract
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional
import uuid
import csv
import io

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog
from ..models.accounting_models import (
    ServiceCatalog, Invoice, InvoiceItem, Payment, Expense, DailyClosing
)
from ..schemas.accounting_schemas import (
    ServiceCreate, ServiceUpdate, ServiceOut,
    InvoiceCreate, InvoiceVoid, InvoiceOut, InvoiceDetailOut,
    PaymentCreate, PaymentVoid, PaymentOut,
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    ClosingCreate, ClosingOut,
)

router = APIRouter(prefix="/api/v1/accounting", tags=["Accounting / ระบบบัญชี"])

PAYMENT_METHODS = {"cash", "credit_card", "debit_card", "bank_transfer",
                   "promptpay", "insurance", "other"}


# ── Helpers ───────────────────────────────────────────────

def _audit(db, user, action, resource_type, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()), user_id=user.id if user else None,
        action=action, module="accounting", resource_type=resource_type,
        resource_id=resource_id, detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


def _next_number(db: Session, model, column, prefix: str) -> str:
    """Sequential document number: PREFIX-YYYY-NNNNN, safe against restarts."""
    year = datetime.now().year
    pattern = f"{prefix}-{year}-%"
    last = (db.query(column)
              .filter(column.like(pattern))
              .order_by(desc(column))
              .first())
    seq = int(last[0].rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}-{year}-{seq:05d}"


def _q2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _recalc_invoice_payment_state(inv: Invoice, db: Session):
    paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.invoice_id == inv.id, Payment.is_void.is_(False)
    ).scalar()
    inv.paid_amount = _q2(paid)
    inv.balance_due = _q2(Decimal(str(inv.total_amount)) - inv.paid_amount)
    if inv.status != "void":
        if inv.paid_amount <= 0:
            inv.status = "issued" if inv.status != "draft" else "draft"
        elif inv.balance_due <= 0:
            inv.status = "paid"
        else:
            inv.status = "partially_paid"
    inv.updated_at = datetime.now(timezone.utc)


# ══ SERVICE CATALOG / รายการค่าบริการ ═════════════════════

@router.get("/services")
def list_services(
    search: Optional[str] = None,
    category: Optional[str] = None,
    active: Optional[bool] = None,
    skip: int = 0, limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    q = db.query(ServiceCatalog)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(ServiceCatalog.name_en.ilike(like),
                         ServiceCatalog.name_th.ilike(like),
                         ServiceCatalog.service_code.ilike(like)))
    if category:
        q = q.filter(ServiceCatalog.category == category)
    if active is not None:
        q = q.filter(ServiceCatalog.active == active)
    total = q.count()
    rows = q.order_by(ServiceCatalog.category, ServiceCatalog.name_en)\
            .offset(skip).limit(limit).all()
    return {"total": total, "items": [ServiceOut.model_validate(r) for r in rows]}


@router.post("/services", status_code=201)
def create_service(
    payload: ServiceCreate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    code = payload.service_code or _next_number(
        db, ServiceCatalog, ServiceCatalog.service_code, "SVC").replace(f"-{datetime.now().year}", "")
    if db.query(ServiceCatalog).filter(ServiceCatalog.service_code == code).first():
        raise HTTPException(409, f"Service code {code} already exists")
    svc = ServiceCatalog(id=str(uuid.uuid4()),
                         **payload.model_dump(exclude={"service_code"}),
                         service_code=code, created_by=user.id)
    db.add(svc)
    _audit(db, user, "create", "service", svc.id, code, request)
    db.commit(); db.refresh(svc)
    return ServiceOut.model_validate(svc)


@router.patch("/services/{service_id}")
def update_service(
    service_id: str, payload: ServiceUpdate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    svc = db.get(ServiceCatalog, service_id)
    if not svc:
        raise HTTPException(404, "Service not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(svc, k, v)
    svc.updated_at = datetime.now(timezone.utc)
    _audit(db, user, "update", "service", svc.id, svc.service_code, request)
    db.commit(); db.refresh(svc)
    return ServiceOut.model_validate(svc)


@router.post("/services/import-csv")
async def import_services_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    """
    Flexible CSV import for the price list. EN/TH headers accepted:
    code|รหัส, name_en|ชื่อ(EN), name_th|ชื่อ(TH), category|หมวด,
    price|ราคา, vat|ภาษี, unit|หน่วย
    """
    header_map = {
        "code": "service_code", "service_code": "service_code", "รหัส": "service_code",
        "name_en": "name_en", "name": "name_en", "ชื่อ(en)": "name_en",
        "name_th": "name_th", "ชื่อ(th)": "name_th", "ชื่อไทย": "name_th",
        "category": "category", "หมวด": "category", "หมวดหมู่": "category",
        "price": "unit_price", "unit_price": "unit_price", "ราคา": "unit_price",
        "vat": "vat_rate", "vat_rate": "vat_rate", "ภาษี": "vat_rate",
        "unit": "unit", "หน่วย": "unit",
    }
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    created, updated, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        mapped = {}
        for k, v in row.items():
            key = header_map.get((k or "").strip().lower())
            if key and v not in (None, ""):
                mapped[key] = v.strip()
        if not mapped.get("name_en"):
            errors.append(f"Row {i}: missing name"); continue
        try:
            price = _q2(mapped.get("unit_price", 0))
            vat = _q2(mapped.get("vat_rate", 0))
        except Exception:
            errors.append(f"Row {i}: bad number"); continue
        code = mapped.get("service_code")
        svc = (db.query(ServiceCatalog)
                 .filter(ServiceCatalog.service_code == code).first()) if code else None
        if svc:
            svc.name_en = mapped["name_en"]
            svc.name_th = mapped.get("name_th", svc.name_th)
            svc.category = mapped.get("category", svc.category)
            svc.unit_price = price
            svc.vat_rate = vat
            svc.updated_at = datetime.now(timezone.utc)
            updated += 1
        else:
            db.add(ServiceCatalog(
                id=str(uuid.uuid4()),
                service_code=code or f"SVC-{uuid.uuid4().hex[:6].upper()}",
                name_en=mapped["name_en"], name_th=mapped.get("name_th"),
                category=mapped.get("category", "other"),
                unit=mapped.get("unit", "service"),
                unit_price=price, vat_rate=vat, created_by=user.id,
            ))
            created += 1
    _audit(db, user, "import_csv", "service", None,
           f"created={created} updated={updated}", request)
    db.commit()
    return {"created": created, "updated": updated, "errors": errors}


# ══ INVOICES / ใบแจ้งหนี้ ═════════════════════════════════

@router.get("/invoices")
def list_invoices(
    search: Optional[str] = None,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    q = db.query(Invoice)
    if search:
        q = q.filter(Invoice.invoice_number.ilike(f"%{search}%"))
    if patient_id:
        q = q.filter(Invoice.patient_id == patient_id)
    if status:
        q = q.filter(Invoice.status == status)
    if date_from:
        q = q.filter(Invoice.invoice_date >= date_from)
    if date_to:
        q = q.filter(Invoice.invoice_date <= date_to)
    total = q.count()
    rows = q.order_by(desc(Invoice.invoice_date), desc(Invoice.invoice_number))\
            .offset(skip).limit(limit).all()
    return {"total": total, "items": [InvoiceOut.model_validate(r) for r in rows]}


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    inv = (db.query(Invoice).options(joinedload(Invoice.items))
             .filter(Invoice.id == invoice_id).first())
    if not inv:
        raise HTTPException(404, "Invoice not found")
    detail = InvoiceDetailOut.model_validate(inv).model_dump()
    detail["payments"] = [
        PaymentOut.model_validate(p).model_dump()
        for p in sorted(inv.payments, key=lambda p: p.created_at or datetime.min.replace(tzinfo=timezone.utc))
    ]
    return detail


@router.post("/invoices", status_code=201)
def create_invoice(
    payload: InvoiceCreate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "cashier", "manager", "front_desk")),
):
    if payload.status not in ("draft", "issued"):
        raise HTTPException(400, "status must be draft or issued")
    inv_date = payload.invoice_date or date.today()
    number = _next_number(db, Invoice, Invoice.invoice_number, "INV")

    subtotal = Decimal("0"); vat_total = Decimal("0")
    items = []
    for idx, it in enumerate(payload.items):
        line = _q2(Decimal(str(it.quantity)) * Decimal(str(it.unit_price)))
        vat = _q2(line * Decimal(str(it.vat_rate)) / Decimal("100"))
        subtotal += line; vat_total += vat
        category = it.category
        if it.service_id and not category:
            svc = db.get(ServiceCatalog, it.service_id)
            category = svc.category if svc else None
        items.append(InvoiceItem(
            id=str(uuid.uuid4()), service_id=it.service_id,
            description=it.description, description_th=it.description_th,
            category=category, quantity=it.quantity, unit_price=it.unit_price,
            vat_rate=it.vat_rate, line_total=line, sort_order=idx,
        ))

    discount = _q2(payload.discount_amount)
    if discount > subtotal:
        raise HTTPException(400, "Discount exceeds subtotal")
    total = _q2(subtotal - discount + vat_total)

    inv = Invoice(
        id=str(uuid.uuid4()), invoice_number=number,
        patient_id=payload.patient_id, invoice_date=inv_date,
        due_date=payload.due_date, status=payload.status,
        subtotal=_q2(subtotal), discount_amount=discount,
        discount_reason=payload.discount_reason,
        vat_amount=_q2(vat_total), total_amount=total,
        paid_amount=Decimal("0"), balance_due=total,
        is_tax_invoice=payload.is_tax_invoice,
        tax_invoice_number=(number.replace("INV", "TIV") if payload.is_tax_invoice else None),
        tax_id=payload.tax_id, billing_name=payload.billing_name,
        billing_address=payload.billing_address,
        notes=payload.notes, notes_th=payload.notes_th,
        created_by=user.id, items=items,
    )
    db.add(inv)
    _audit(db, user, "create", "invoice", inv.id, number, request)
    db.commit(); db.refresh(inv)
    return InvoiceDetailOut.model_validate(inv)


@router.post("/invoices/{invoice_id}/issue")
def issue_invoice(
    invoice_id: str, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "cashier", "manager", "front_desk")),
):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status != "draft":
        raise HTTPException(400, "Only draft invoices can be issued")
    inv.status = "issued"
    inv.updated_at = datetime.now(timezone.utc)
    _audit(db, user, "issue", "invoice", inv.id, inv.invoice_number, request)
    db.commit()
    return {"ok": True, "status": inv.status}


@router.post("/invoices/{invoice_id}/void")
def void_invoice(
    invoice_id: str, payload: InvoiceVoid, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if _q2(inv.paid_amount) > 0:
        raise HTTPException(400, "Void payments first / ต้องยกเลิกใบเสร็จก่อน")
    inv.status = "void"
    inv.void_reason = payload.void_reason
    inv.voided_by = user.id
    inv.voided_at = datetime.now(timezone.utc)
    _audit(db, user, "void", "invoice", inv.id, inv.invoice_number, request)
    db.commit()
    return {"ok": True, "status": "void"}


# ══ PAYMENTS / การรับชำระเงิน ═════════════════════════════

@router.get("/payments")
def list_payments(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    method: Optional[str] = None,
    patient_id: Optional[str] = None,
    include_void: bool = False,
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    q = db.query(Payment)
    if not include_void:
        q = q.filter(Payment.is_void.is_(False))
    if date_from:
        q = q.filter(Payment.payment_date >= date_from)
    if date_to:
        q = q.filter(Payment.payment_date <= date_to)
    if method:
        q = q.filter(Payment.method == method)
    if patient_id:
        q = q.filter(Payment.patient_id == patient_id)
    total = q.count()
    rows = q.order_by(desc(Payment.payment_date), desc(Payment.receipt_number))\
            .offset(skip).limit(limit).all()
    return {"total": total, "items": [PaymentOut.model_validate(r) for r in rows]}


@router.post("/payments", status_code=201)
def create_payment(
    payload: PaymentCreate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "cashier", "manager", "front_desk")),
):
    if payload.method not in PAYMENT_METHODS:
        raise HTTPException(400, f"method must be one of {sorted(PAYMENT_METHODS)}")
    inv = db.get(Invoice, payload.invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status in ("void", "draft"):
        raise HTTPException(400, f"Cannot pay a {inv.status} invoice")
    amount = _q2(payload.amount)
    if amount > _q2(inv.balance_due):
        raise HTTPException(400, "Amount exceeds balance due / เกินยอดคงเหลือ")

    pay = Payment(
        id=str(uuid.uuid4()),
        receipt_number=_next_number(db, Payment, Payment.receipt_number, "RC"),
        invoice_id=inv.id, patient_id=inv.patient_id,
        payment_date=payload.payment_date or date.today(),
        amount=amount, method=payload.method,
        reference_number=payload.reference_number,
        card_last4=payload.card_last4, bank_name=payload.bank_name,
        notes=payload.notes, received_by=user.id,
    )
    db.add(pay)
    db.flush()
    _recalc_invoice_payment_state(inv, db)
    _audit(db, user, "create", "payment", pay.id, pay.receipt_number, request)
    db.commit(); db.refresh(pay)
    return PaymentOut.model_validate(pay)


@router.post("/payments/{payment_id}/void")
def void_payment(
    payment_id: str, payload: PaymentVoid, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    pay = db.get(Payment, payment_id)
    if not pay:
        raise HTTPException(404, "Payment not found")
    if pay.is_void:
        raise HTTPException(400, "Already void")
    closing = db.query(DailyClosing).filter(
        DailyClosing.closing_date == pay.payment_date).first()
    if closing:
        raise HTTPException(400, "Day already closed / วันนี้ปิดยอดแล้ว")
    pay.is_void = True
    pay.void_reason = payload.void_reason
    pay.voided_by = user.id
    pay.voided_at = datetime.now(timezone.utc)
    inv = db.get(Invoice, pay.invoice_id)
    if inv:
        _recalc_invoice_payment_state(inv, db)
    _audit(db, user, "void", "payment", pay.id, pay.receipt_number, request)
    db.commit()
    return {"ok": True}


# ══ EXPENSES / ค่าใช้จ่าย ═════════════════════════════════

@router.get("/expenses")
def list_expenses(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0, limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    q = db.query(Expense)
    if date_from:
        q = q.filter(Expense.expense_date >= date_from)
    if date_to:
        q = q.filter(Expense.expense_date <= date_to)
    if category:
        q = q.filter(Expense.category == category)
    if status:
        q = q.filter(Expense.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Expense.vendor_name.ilike(like),
                         Expense.description.ilike(like),
                         Expense.expense_number.ilike(like)))
    total = q.count()
    rows = q.order_by(desc(Expense.expense_date)).offset(skip).limit(limit).all()
    return {"total": total, "items": [ExpenseOut.model_validate(r) for r in rows]}


@router.post("/expenses", status_code=201)
def create_expense(
    payload: ExpenseCreate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    amount = _q2(payload.amount)
    vat = _q2(payload.vat_amount)
    wht_rate = _q2(payload.withholding_tax_rate)
    wht = _q2(amount * wht_rate / Decimal("100"))
    exp = Expense(
        id=str(uuid.uuid4()),
        expense_number=_next_number(db, Expense, Expense.expense_number, "EXP"),
        expense_date=payload.expense_date or date.today(),
        category=payload.category,
        vendor_name=payload.vendor_name, vendor_tax_id=payload.vendor_tax_id,
        description=payload.description, description_th=payload.description_th,
        amount=amount, vat_amount=vat,
        withholding_tax_rate=wht_rate, withholding_tax_amount=wht,
        net_paid=_q2(amount + vat - wht),
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        receipt_attached=payload.receipt_attached,
        created_by=user.id,
    )
    db.add(exp)
    _audit(db, user, "create", "expense", exp.id, exp.expense_number, request)
    db.commit(); db.refresh(exp)
    return ExpenseOut.model_validate(exp)


@router.patch("/expenses/{expense_id}")
def update_expense(
    expense_id: str, payload: ExpenseUpdate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    exp = db.get(Expense, expense_id)
    if not exp:
        raise HTTPException(404, "Expense not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "approved":
        exp.approved_by = user.id
    for k, v in data.items():
        setattr(exp, k, v)
    # Recompute derived amounts
    amount = _q2(exp.amount); vat = _q2(exp.vat_amount)
    wht = _q2(amount * _q2(exp.withholding_tax_rate) / Decimal("100"))
    exp.withholding_tax_amount = wht
    exp.net_paid = _q2(amount + vat - wht)
    exp.updated_at = datetime.now(timezone.utc)
    _audit(db, user, "update", "expense", exp.id, exp.expense_number, request)
    db.commit(); db.refresh(exp)
    return ExpenseOut.model_validate(exp)


# ══ DAILY CLOSING / ปิดยอดประจำวัน ════════════════════════

def _day_totals(db: Session, day: date) -> dict:
    rows = (db.query(Payment.method, func.coalesce(func.sum(Payment.amount), 0),
                     func.count(Payment.id))
              .filter(Payment.payment_date == day, Payment.is_void.is_(False))
              .group_by(Payment.method).all())
    by_method = {m: _q2(s) for m, s, _ in rows}
    payment_count = sum(c for _, _, c in rows)
    invoice_count = db.query(func.count(Invoice.id)).filter(
        Invoice.invoice_date == day, Invoice.status != "void").scalar()
    card = _q2(by_method.get("credit_card", 0)) + _q2(by_method.get("debit_card", 0))
    return {
        "cash": _q2(by_method.get("cash", 0)),
        "card": card,
        "transfer": _q2(by_method.get("bank_transfer", 0)),
        "promptpay": _q2(by_method.get("promptpay", 0)),
        "insurance": _q2(by_method.get("insurance", 0)),
        "other": _q2(by_method.get("other", 0)),
        "total": _q2(sum(by_method.values())),
        "payment_count": payment_count,
        "invoice_count": invoice_count or 0,
    }


@router.get("/closings")
def list_closings(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0, limit: int = Query(31, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    q = db.query(DailyClosing)
    if date_from:
        q = q.filter(DailyClosing.closing_date >= date_from)
    if date_to:
        q = q.filter(DailyClosing.closing_date <= date_to)
    rows = q.order_by(desc(DailyClosing.closing_date)).offset(skip).limit(limit).all()
    return {"items": [ClosingOut.model_validate(r) for r in rows]}


@router.post("/closings", status_code=201)
def close_day(
    payload: ClosingCreate, request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    day = payload.closing_date or date.today()
    if db.query(DailyClosing).filter(DailyClosing.closing_date == day).first():
        raise HTTPException(409, "Day already closed / วันนี้ปิดยอดแล้ว")
    t = _day_totals(db, day)
    counted = _q2(payload.cash_counted)
    closing = DailyClosing(
        id=str(uuid.uuid4()), closing_date=day,
        cash_expected=t["cash"], cash_counted=counted,
        cash_variance=_q2(counted - t["cash"]),
        card_total=t["card"], transfer_total=t["transfer"],
        promptpay_total=t["promptpay"], insurance_total=t["insurance"],
        other_total=t["other"], total_revenue=t["total"],
        invoice_count=t["invoice_count"], payment_count=t["payment_count"],
        notes=payload.notes, closed_by=user.id,
    )
    db.add(closing)
    _audit(db, user, "close_day", "daily_closing", closing.id, str(day), request)
    db.commit(); db.refresh(closing)
    return ClosingOut.model_validate(closing)


# ══ REPORTS / รายงานการเงิน ═══════════════════════════════

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    today = date.today()
    month_start = today.replace(day=1)
    t = _day_totals(db, today)
    month_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.payment_date >= month_start, Payment.payment_date <= today,
        Payment.is_void.is_(False)).scalar()
    month_expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.expense_date >= month_start, Expense.expense_date <= today,
        Expense.status != "void").scalar()
    outstanding = db.query(func.coalesce(func.sum(Invoice.balance_due), 0)).filter(
        Invoice.status.in_(["issued", "partially_paid"])).scalar()
    outstanding_count = db.query(func.count(Invoice.id)).filter(
        Invoice.status.in_(["issued", "partially_paid"])).scalar()
    recent = (db.query(Payment).filter(Payment.is_void.is_(False))
                .order_by(desc(Payment.created_at)).limit(10).all())
    return {
        "today": {"date": str(today), **{k: str(v) for k, v in t.items()}},
        "month_revenue": str(_q2(month_revenue)),
        "month_expenses": str(_q2(month_expenses)),
        "month_net": str(_q2(Decimal(str(month_revenue)) - Decimal(str(month_expenses)))),
        "outstanding_total": str(_q2(outstanding)),
        "outstanding_count": outstanding_count or 0,
        "recent_payments": [PaymentOut.model_validate(p).model_dump() for p in recent],
    }


@router.get("/reports/daily")
def report_daily(
    day: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    t = _day_totals(db, day)
    payments = (db.query(Payment)
                  .filter(Payment.payment_date == day, Payment.is_void.is_(False))
                  .order_by(Payment.receipt_number).all())
    return {"date": str(day),
            "totals": {k: str(v) for k, v in t.items()},
            "payments": [PaymentOut.model_validate(p).model_dump() for p in payments]}


@router.get("/reports/monthly-pl")
def report_monthly_pl(
    year: int, month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    """Profit & loss: revenue by service category (from paid amounts allocated by
    invoice items) vs expenses by category."""
    start = date(year, month, 1)
    end = (start.replace(year=year + 1, month=1) if month == 12
           else start.replace(month=month + 1)) - timedelta(days=1)

    # Revenue = payments received in period (cash basis)
    revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.payment_date.between(start, end), Payment.is_void.is_(False)).scalar()

    # Billed by category (accrual view for insight)
    billed_rows = (db.query(InvoiceItem.category,
                            func.coalesce(func.sum(InvoiceItem.line_total), 0))
                     .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                     .filter(Invoice.invoice_date.between(start, end),
                             Invoice.status != "void")
                     .group_by(InvoiceItem.category).all())

    expense_rows = (db.query(Expense.category,
                             func.coalesce(func.sum(Expense.amount), 0))
                      .filter(Expense.expense_date.between(start, end),
                              Expense.status != "void")
                      .group_by(Expense.category).all())
    total_expenses = sum((Decimal(str(v)) for _, v in expense_rows), Decimal("0"))

    return {
        "period": f"{year}-{month:02d}",
        "revenue_received": str(_q2(revenue)),
        "billed_by_category": {(c or "other"): str(_q2(v)) for c, v in billed_rows},
        "expenses_by_category": {c: str(_q2(v)) for c, v in expense_rows},
        "total_expenses": str(_q2(total_expenses)),
        "net": str(_q2(Decimal(str(revenue)) - total_expenses)),
    }


@router.get("/reports/outstanding")
def report_outstanding(
    db: Session = Depends(get_db),
    user: User = Depends(require_module_access("accounting")),
):
    """AR aging: 0–30 / 31–60 / 61–90 / 90+ days."""
    today = date.today()
    rows = (db.query(Invoice)
              .filter(Invoice.status.in_(["issued", "partially_paid"]),
                      Invoice.balance_due > 0)
              .order_by(Invoice.invoice_date).all())
    buckets = {"0_30": Decimal("0"), "31_60": Decimal("0"),
               "61_90": Decimal("0"), "over_90": Decimal("0")}
    items = []
    for inv in rows:
        age = (today - inv.invoice_date).days
        key = ("0_30" if age <= 30 else "31_60" if age <= 60
               else "61_90" if age <= 90 else "over_90")
        buckets[key] += _q2(inv.balance_due)
        items.append({**InvoiceOut.model_validate(inv).model_dump(),
                      "age_days": age, "bucket": key})
    return {"as_of": str(today),
            "buckets": {k: str(v) for k, v in buckets.items()},
            "total": str(sum(buckets.values())),
            "invoices": items}


@router.get("/reports/revenue-by-category")
def report_revenue_by_category(
    date_from: date, date_to: date,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    rows = (db.query(InvoiceItem.category,
                     func.coalesce(func.sum(InvoiceItem.line_total), 0),
                     func.count(InvoiceItem.id))
              .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
              .filter(Invoice.invoice_date.between(date_from, date_to),
                      Invoice.status != "void")
              .group_by(InvoiceItem.category)
              .order_by(desc(func.sum(InvoiceItem.line_total))).all())
    return {"from": str(date_from), "to": str(date_to),
            "categories": [{"category": c or "other", "billed": str(_q2(v)),
                            "line_count": n} for c, v, n in rows]}
