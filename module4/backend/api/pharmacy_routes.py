"""
FCMS Module 4 — Pharmacy API Routes / เส้นทาง API เภสัชกรรม
Full CRUD: drug catalogue, stock management (FIFO), prescription workflow,
dispensing, bilingual label generation, expiry/low-stock alerts, dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_, case
from datetime import datetime, timezone, date, timedelta
from typing import Optional
import uuid
import json

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/pharmacy", tags=["Pharmacy / เภสัชกรรม"])

# ── Next RX number generator ─────────────────────────────
_rx_counter = 0

def _next_rx_number(db: Session) -> str:
    global _rx_counter
    year = datetime.now().year
    _rx_counter += 1
    return f"RX-{year}-{_rx_counter:05d}"


def _audit(db, user, action, resource_type, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()), user_id=user.id if user else None,
        action=action, module="pharmacy", resource_type=resource_type,
        resource_id=resource_id, detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


# ══════════════════════════════════════════════════════════
# 1. DRUG CATALOGUE / รายการยา
# ══════════════════════════════════════════════════════════

@router.get("/drugs")
async def list_drugs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    form: Optional[str] = None,
    low_stock_only: bool = False,
    active_only: bool = True,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """List drugs with search, filter, pagination. / แสดงรายการยาพร้อมค้นหาและตัวกรอง"""
    from ..models.pharmacy_models import Drug

    q = db.query(Drug)
    if active_only:
        q = q.filter(Drug.is_active == True)
    if search:
        s = f"%{search}%"
        q = q.filter(or_(
            Drug.generic_name.ilike(s),
            Drug.generic_name_th.ilike(s),
            Drug.brand_name.ilike(s),
            Drug.brand_name_th.ilike(s),
        ))
    if category:
        q = q.filter(Drug.category == category)
    if form:
        q = q.filter(Drug.form == form)
    if low_stock_only:
        q = q.filter(Drug.current_stock <= Drug.reorder_level)

    total = q.count()
    drugs = q.order_by(Drug.generic_name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "drugs": [{
            "id": d.id, "generic_name": d.generic_name, "generic_name_th": d.generic_name_th,
            "brand_name": d.brand_name, "brand_name_th": d.brand_name_th,
            "category": d.category, "form": d.form, "form_th": d.form_th,
            "strength": d.strength, "unit": d.unit, "unit_th": d.unit_th,
            "manufacturer": d.manufacturer, "supplier": d.supplier,
            "unit_cost": float(d.unit_cost) if d.unit_cost else None,
            "selling_price": float(d.selling_price) if d.selling_price else None,
            "current_stock": d.current_stock or 0, "reorder_level": d.reorder_level,
            "requires_refrigeration": d.requires_refrigeration,
            "is_controlled": d.is_controlled, "is_active": d.is_active,
            "stock_status": "out_of_stock" if (d.current_stock or 0) == 0
                           else "low" if (d.current_stock or 0) <= (d.reorder_level or 0)
                           else "ok",
        } for d in drugs],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "filters": {
            "categories": [
                {"en": "Hormonal", "th": "ฮอร์โมน"},
                {"en": "IVF Protocol", "th": "โปรโตคอล IVF"},
                {"en": "Antibiotic", "th": "ยาปฏิชีวนะ"},
                {"en": "Analgesic", "th": "ยาแก้ปวด"},
                {"en": "Vitamin", "th": "วิตามิน"},
                {"en": "Anesthetic", "th": "ยาชา"},
                {"en": "Anticoagulant", "th": "ยาต้านการแข็งตัวของเลือด"},
                {"en": "Supplement", "th": "อาหารเสริม"},
                {"en": "Other", "th": "อื่นๆ"},
            ],
            "forms": [
                {"en": "Tablet", "th": "เม็ด"}, {"en": "Capsule", "th": "แคปซูล"},
                {"en": "Injection", "th": "ยาฉีด"}, {"en": "Cream/Gel", "th": "ครีม/เจล"},
                {"en": "Suppository", "th": "ยาเหน็บ"}, {"en": "Liquid/Syrup", "th": "ยาน้ำ"},
                {"en": "Patch", "th": "แผ่นแปะ"}, {"en": "Nasal Spray", "th": "สเปรย์พ่นจมูก"},
                {"en": "Vaginal Tablet", "th": "ยาเหน็บช่องคลอด"},
            ],
        },
    }


@router.post("/drugs")
async def create_drug(
    request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Create a new drug entry. / เพิ่มยาใหม่"""
    from ..models.pharmacy_models import Drug
    body = await request.json()

    for f in ["generic_name", "form", "strength", "unit"]:
        if not body.get(f):
            raise HTTPException(400, f"{f} is required / จำเป็นต้องกรอก {f}")

    drug = Drug(
        id=str(uuid.uuid4()),
        generic_name=body["generic_name"],
        generic_name_th=body.get("generic_name_th"),
        brand_name=body.get("brand_name"),
        brand_name_th=body.get("brand_name_th"),
        category=body.get("category", "other"),
        form=body["form"],
        form_th=body.get("form_th"),
        strength=body["strength"],
        unit=body["unit"],
        unit_th=body.get("unit_th"),
        manufacturer=body.get("manufacturer"),
        supplier=body.get("supplier"),
        reorder_level=body.get("reorder_level", 50),
        reorder_quantity=body.get("reorder_quantity", 200),
        unit_cost=body.get("unit_cost"),
        selling_price=body.get("selling_price"),
        storage_condition=body.get("storage_condition"),
        storage_condition_th=body.get("storage_condition_th"),
        instructions_en=body.get("instructions_en"),
        instructions_th=body.get("instructions_th"),
        warnings_en=body.get("warnings_en"),
        warnings_th=body.get("warnings_th"),
        requires_refrigeration=body.get("requires_refrigeration", False),
        is_controlled=body.get("is_controlled", False),
        label_dose_en=body.get("label_dose_en"),
        label_dose_th=body.get("label_dose_th"),
        label_route_en=body.get("label_route_en"),
        label_route_th=body.get("label_route_th"),
        label_frequency_en=body.get("label_frequency_en"),
        label_frequency_th=body.get("label_frequency_th"),
        label_warnings_en=body.get("label_warnings_en"),
        label_warnings_th=body.get("label_warnings_th"),
        current_stock=0,
        created_by=current_user.id,
    )
    db.add(drug)
    _audit(db, current_user, "CREATE", "drug", drug.id,
           f"Drug created: {drug.generic_name} ({drug.brand_name or '-'})", request)
    db.commit()
    db.refresh(drug)

    return {"id": drug.id, "generic_name": drug.generic_name, "message": "Drug created / เพิ่มยาสำเร็จ"}


@router.get("/drugs/{drug_id}")
async def get_drug(
    drug_id: str,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Get drug detail with stock lots and recent dispensing. / รายละเอียดยาพร้อมสต็อก"""
    from ..models.pharmacy_models import Drug, DrugStockLot, StockTransaction

    drug = db.query(Drug).filter(Drug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Drug not found / ไม่พบข้อมูลยา")

    lots = db.query(DrugStockLot).filter(
        DrugStockLot.drug_id == drug_id,
        DrugStockLot.is_active == True,
        DrugStockLot.current_quantity > 0
    ).order_by(DrugStockLot.expiry_date).all()

    recent_tx = db.query(StockTransaction).filter(
        StockTransaction.drug_id == drug_id
    ).order_by(desc(StockTransaction.created_at)).limit(20).all()

    return {
        "drug": {
            "id": drug.id, "generic_name": drug.generic_name,
            "generic_name_th": drug.generic_name_th,
            "brand_name": drug.brand_name, "brand_name_th": drug.brand_name_th,
            "category": drug.category, "form": drug.form, "form_th": drug.form_th,
            "strength": drug.strength, "unit": drug.unit, "unit_th": drug.unit_th,
            "manufacturer": drug.manufacturer, "supplier": drug.supplier,
            "unit_cost": float(drug.unit_cost) if drug.unit_cost else None,
            "selling_price": float(drug.selling_price) if drug.selling_price else None,
            "current_stock": drug.current_stock or 0,
            "reorder_level": drug.reorder_level, "reorder_quantity": drug.reorder_quantity,
            "storage_condition": drug.storage_condition,
            "storage_condition_th": drug.storage_condition_th,
            "instructions_en": drug.instructions_en, "instructions_th": drug.instructions_th,
            "warnings_en": drug.warnings_en, "warnings_th": drug.warnings_th,
            "requires_refrigeration": drug.requires_refrigeration,
            "is_controlled": drug.is_controlled, "is_active": drug.is_active,
            "label_dose_en": drug.label_dose_en, "label_dose_th": drug.label_dose_th,
            "label_route_en": drug.label_route_en, "label_route_th": drug.label_route_th,
            "label_frequency_en": drug.label_frequency_en,
            "label_frequency_th": drug.label_frequency_th,
        },
        "stock_lots": [{
            "id": lot.id, "lot_number": lot.lot_number,
            "expiry_date": lot.expiry_date.isoformat(),
            "initial_quantity": lot.initial_quantity,
            "current_quantity": lot.current_quantity,
            "unit_cost": float(lot.unit_cost) if lot.unit_cost else None,
            "supplier": lot.supplier,
            "days_to_expiry": (lot.expiry_date - date.today()).days,
        } for lot in lots],
        "recent_transactions": [{
            "id": tx.id, "type": tx.transaction_type,
            "quantity": tx.quantity, "balance_after": tx.balance_after,
            "reason": tx.reason,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        } for tx in recent_tx],
    }


@router.patch("/drugs/{drug_id}")
async def update_drug(
    drug_id: str, request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Update drug details. / แก้ไขรายละเอียดยา"""
    from ..models.pharmacy_models import Drug
    body = await request.json()
    drug = db.query(Drug).filter(Drug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Drug not found / ไม่พบข้อมูลยา")

    updatable = [
        "generic_name", "generic_name_th", "brand_name", "brand_name_th",
        "category", "form", "form_th", "strength", "unit", "unit_th",
        "manufacturer", "supplier", "reorder_level", "reorder_quantity",
        "unit_cost", "selling_price", "storage_condition", "storage_condition_th",
        "instructions_en", "instructions_th", "warnings_en", "warnings_th",
        "requires_refrigeration", "is_controlled", "is_active",
        "label_dose_en", "label_dose_th", "label_route_en", "label_route_th",
        "label_frequency_en", "label_frequency_th",
        "label_warnings_en", "label_warnings_th",
    ]
    changes = []
    for field in updatable:
        if field in body:
            old_val = getattr(drug, field)
            setattr(drug, field, body[field])
            changes.append(f"{field}: {old_val} → {body[field]}")

    _audit(db, current_user, "UPDATE", "drug", drug_id,
           f"Updated: {'; '.join(changes[:5])}", request)
    db.commit()
    return {"message": "Drug updated / แก้ไขยาสำเร็จ", "id": drug_id}


# ══════════════════════════════════════════════════════════
# 2. STOCK MANAGEMENT / จัดการสต็อก
# ══════════════════════════════════════════════════════════

@router.post("/stock/receive")
async def receive_stock(
    request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "pharmacy_staff", "admin"])),
    db: Session = Depends(get_db),
):
    """Receive stock with lot/expiry tracking. / รับสต็อกเข้าพร้อมเลขล็อตและวันหมดอายุ"""
    from ..models.pharmacy_models import Drug, DrugStockLot, StockTransaction
    body = await request.json()

    for f in ["drug_id", "quantity", "lot_number", "expiry_date"]:
        if not body.get(f):
            raise HTTPException(400, f"{f} is required / จำเป็นต้องกรอก {f}")

    drug = db.query(Drug).filter(Drug.id == body["drug_id"]).first()
    if not drug:
        raise HTTPException(404, "Drug not found / ไม่พบข้อมูลยา")

    qty = int(body["quantity"])
    if qty <= 0:
        raise HTTPException(400, "Quantity must be positive / จำนวนต้องมากกว่า 0")

    lot = DrugStockLot(
        id=str(uuid.uuid4()),
        drug_id=body["drug_id"],
        lot_number=body["lot_number"],
        expiry_date=body["expiry_date"],
        initial_quantity=qty,
        current_quantity=qty,
        unit_cost=body.get("unit_cost"),
        supplier=body.get("supplier"),
        po_number=body.get("po_number"),
        invoice_number=body.get("invoice_number"),
        received_by=current_user.id,
        notes=body.get("notes"),
    )
    db.add(lot)

    drug.current_stock = (drug.current_stock or 0) + qty

    tx = StockTransaction(
        id=str(uuid.uuid4()),
        drug_id=body["drug_id"], lot_id=lot.id,
        transaction_type="receive", quantity=qty,
        balance_after=drug.current_stock,
        reference_type="po",
        reason=f"GRN: Lot {body['lot_number']}, Exp {body['expiry_date']}",
        performed_by=current_user.id,
    )
    db.add(tx)

    _audit(db, current_user, "CREATE", "stock_receipt", lot.id,
           f"Received {qty} {drug.unit} of {drug.generic_name}, lot {body['lot_number']}", request)
    db.commit()

    return {
        "id": lot.id, "drug_id": body["drug_id"],
        "lot_number": body["lot_number"], "quantity": qty,
        "new_total_stock": drug.current_stock,
        "message": f"Stock received / รับสต็อกเข้า {qty} {drug.unit}",
    }


@router.post("/stock/adjust")
async def adjust_stock(
    request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "admin"])),
    db: Session = Depends(get_db),
):
    """Manual stock adjustment with mandatory reason. / ปรับสต็อกด้วยตนเองพร้อมเหตุผล"""
    from ..models.pharmacy_models import Drug, DrugStockLot, StockTransaction
    body = await request.json()

    for f in ["drug_id", "adjustment_type", "quantity", "reason"]:
        if not body.get(f):
            raise HTTPException(400, f"{f} is required / จำเป็นต้องกรอก {f}")

    drug = db.query(Drug).filter(Drug.id == body["drug_id"]).first()
    if not drug:
        raise HTTPException(404, "Drug not found / ไม่พบข้อมูลยา")

    qty = int(body["quantity"])
    adj_type = body["adjustment_type"]

    if adj_type in ("remove", "expired_write_off"):
        if qty > (drug.current_stock or 0):
            raise HTTPException(400, "Insufficient stock / สต็อกไม่เพียงพอ")
        drug.current_stock = (drug.current_stock or 0) - qty
        tx_qty = -qty
    else:
        drug.current_stock = (drug.current_stock or 0) + qty
        tx_qty = qty

    lot_id = body.get("lot_id")
    if lot_id:
        lot = db.query(DrugStockLot).filter(DrugStockLot.id == lot_id).first()
        if lot:
            if adj_type in ("remove", "expired_write_off"):
                lot.current_quantity = max(0, lot.current_quantity - qty)
            else:
                lot.current_quantity += qty

    tx = StockTransaction(
        id=str(uuid.uuid4()),
        drug_id=body["drug_id"], lot_id=lot_id,
        transaction_type=f"adjust_{adj_type}",
        quantity=tx_qty, balance_after=drug.current_stock,
        reference_type="adjustment",
        reason=body["reason"],
        performed_by=current_user.id,
    )
    db.add(tx)

    _audit(db, current_user, "UPDATE", "stock_adjustment", tx.id,
           f"Adjusted {drug.generic_name}: {adj_type} {qty}. Reason: {body['reason']}", request)
    db.commit()

    return {
        "id": tx.id, "drug_id": body["drug_id"],
        "adjustment_type": adj_type, "quantity": qty,
        "new_total_stock": drug.current_stock,
        "message": "Stock adjusted / ปรับสต็อกสำเร็จ",
    }


@router.get("/stock/levels")
async def stock_levels(
    low_stock_only: bool = False,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Current stock levels. / ระดับสต็อกปัจจุบัน"""
    from ..models.pharmacy_models import Drug

    q = db.query(Drug).filter(Drug.is_active == True)
    if low_stock_only:
        q = q.filter(Drug.current_stock <= Drug.reorder_level)

    drugs = q.order_by(Drug.generic_name).all()
    total = len(drugs)
    low = sum(1 for d in drugs if 0 < (d.current_stock or 0) <= (d.reorder_level or 0))
    out = sum(1 for d in drugs if (d.current_stock or 0) == 0)

    return {
        "drugs": [{
            "id": d.id, "generic_name": d.generic_name, "generic_name_th": d.generic_name_th,
            "brand_name": d.brand_name, "current_stock": d.current_stock or 0,
            "reorder_level": d.reorder_level, "unit": d.unit,
            "stock_status": "out_of_stock" if (d.current_stock or 0) == 0
                           else "low" if (d.current_stock or 0) <= (d.reorder_level or 0)
                           else "ok",
            "suggested_reorder": d.reorder_quantity if (d.current_stock or 0) <= (d.reorder_level or 0) else 0,
        } for d in drugs],
        "total_items": total, "low_stock_count": low, "out_of_stock_count": out,
    }


@router.get("/expiry/alerts")
async def expiry_alerts(
    days_ahead: int = Query(90, ge=1, le=365),
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Expiry alerts. / แจ้งเตือนยาใกล้หมดอายุ"""
    from ..models.pharmacy_models import DrugStockLot, Drug

    today = date.today()
    lots = db.query(DrugStockLot, Drug).join(Drug).filter(
        DrugStockLot.is_active == True,
        DrugStockLot.current_quantity > 0,
        DrugStockLot.expiry_date <= today + timedelta(days=days_ahead),
    ).order_by(DrugStockLot.expiry_date).all()

    def lot_info(lot, drug):
        days_left = (lot.expiry_date - today).days
        return {
            "lot_id": lot.id, "drug_id": drug.id,
            "drug_name": drug.generic_name, "drug_name_th": drug.generic_name_th,
            "brand_name": drug.brand_name, "lot_number": lot.lot_number,
            "expiry_date": lot.expiry_date.isoformat(),
            "current_quantity": lot.current_quantity, "unit": drug.unit,
            "days_to_expiry": days_left,
            "value_at_risk": float(lot.unit_cost * lot.current_quantity) if lot.unit_cost else 0,
        }

    expired = [lot_info(l, d) for l, d in lots if l.expiry_date <= today]
    exp_30 = [lot_info(l, d) for l, d in lots if today < l.expiry_date <= today + timedelta(30)]
    exp_60 = [lot_info(l, d) for l, d in lots if today + timedelta(30) < l.expiry_date <= today + timedelta(60)]
    exp_90 = [lot_info(l, d) for l, d in lots if today + timedelta(60) < l.expiry_date <= today + timedelta(days_ahead)]

    total_risk = sum(i.get("value_at_risk", 0) for i in expired + exp_30 + exp_60 + exp_90)

    return {
        "already_expired": expired, "expiring_30d": exp_30,
        "expiring_60d": exp_60, "expiring_90d": exp_90,
        "total_value_at_risk": total_risk,
    }


# ══════════════════════════════════════════════════════════
# 3. PRESCRIPTIONS & DISPENSING / ใบสั่งยาและการจ่ายยา
# ══════════════════════════════════════════════════════════

@router.get("/prescriptions")
async def list_prescriptions(
    status: Optional[str] = None,
    patient_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """List prescriptions. / แสดงใบสั่งยา"""
    from ..models.pharmacy_models import Prescription

    q = db.query(Prescription)
    if status:
        q = q.filter(Prescription.status == status)
    if patient_id:
        q = q.filter(Prescription.patient_id == patient_id)

    total = q.count()
    rxs = q.order_by(desc(Prescription.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    counts = {}
    for s in ["pending", "verified", "dispensed", "cancelled"]:
        counts[s] = db.query(Prescription).filter(Prescription.status == s).count()

    return {
        "prescriptions": [{
            "id": rx.id, "rx_number": rx.rx_number,
            "patient_id": rx.patient_id, "prescriber_id": rx.prescriber_id,
            "status": rx.status, "priority": rx.priority,
            "notes": rx.notes, "item_count": len(rx.items) if rx.items else 0,
            "created_at": rx.created_at.isoformat() if rx.created_at else None,
            "verified_at": rx.verified_at.isoformat() if rx.verified_at else None,
            "dispensed_at": rx.dispensed_at.isoformat() if rx.dispensed_at else None,
        } for rx in rxs],
        "total": total, "page": page, "per_page": per_page,
        "counts": counts,
    }


@router.post("/prescriptions")
async def create_prescription(
    request: Request,
    current_user: User = Depends(require_roles(["physician", "admin"])),
    db: Session = Depends(get_db),
):
    """Create prescription from EMR. / สร้างใบสั่งยา"""
    from ..models.pharmacy_models import Prescription, PrescriptionItem
    body = await request.json()

    if not body.get("patient_id"):
        raise HTTPException(400, "patient_id is required / จำเป็นต้องระบุผู้ป่วย")
    if not body.get("items") or len(body["items"]) == 0:
        raise HTTPException(400, "At least one medication required / ต้องระบุยาอย่างน้อย 1 รายการ")

    rx = Prescription(
        id=str(uuid.uuid4()),
        rx_number=_next_rx_number(db),
        patient_id=body["patient_id"],
        visit_id=body.get("visit_id"),
        prescriber_id=current_user.id,
        priority=body.get("priority", "normal"),
        notes=body.get("notes"),
        notes_th=body.get("notes_th"),
        status="pending",
    )
    db.add(rx)

    for item_data in body["items"]:
        item = PrescriptionItem(
            id=str(uuid.uuid4()),
            prescription_id=rx.id,
            drug_id=item_data["drug_id"],
            quantity=item_data["quantity"],
            dosage=item_data.get("dosage"),
            frequency=item_data.get("frequency"),
            frequency_th=item_data.get("frequency_th"),
            route=item_data.get("route"),
            route_th=item_data.get("route_th"),
            duration_days=item_data.get("duration_days"),
            instructions_en=item_data.get("instructions_en"),
            instructions_th=item_data.get("instructions_th"),
            warnings=item_data.get("warnings"),
        )
        db.add(item)

    _audit(db, current_user, "CREATE", "prescription", rx.id,
           f"Rx {rx.rx_number}: {len(body['items'])} items", request)
    db.commit()

    return {
        "id": rx.id, "rx_number": rx.rx_number,
        "status": "pending", "item_count": len(body["items"]),
        "message": f"Prescription created / สร้างใบสั่งยา {rx.rx_number} สำเร็จ",
    }


@router.post("/prescriptions/{rx_id}/verify")
async def verify_prescription(
    rx_id: str, request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "admin"])),
    db: Session = Depends(get_db),
):
    """Pharmacist verifies. / เภสัชกรตรวจสอบใบสั่งยา"""
    from ..models.pharmacy_models import Prescription
    body = await request.json()

    rx = db.query(Prescription).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(404, "Prescription not found / ไม่พบใบสั่งยา")
    if rx.status != "pending":
        raise HTTPException(400, f"Cannot verify — status is {rx.status}")

    rx.status = "verified"
    rx.verified_by = current_user.id
    rx.verified_at = datetime.now(timezone.utc)

    _audit(db, current_user, "UPDATE", "prescription", rx_id,
           f"Rx {rx.rx_number} verified", request)
    db.commit()

    return {
        "rx_id": rx_id, "rx_number": rx.rx_number, "status": "verified",
        "verified_by": f"{current_user.first_name_en} {current_user.last_name_en}",
        "verified_at": rx.verified_at.isoformat(),
        "message": "Prescription verified / ตรวจสอบใบสั่งยาสำเร็จ",
    }


@router.post("/prescriptions/{rx_id}/dispense")
async def dispense_prescription(
    rx_id: str, request: Request,
    current_user: User = Depends(require_roles(["pharmacist", "pharmacy_staff", "admin"])),
    db: Session = Depends(get_db),
):
    """Dispense with FIFO. / จ่ายยาตามระบบ FIFO"""
    from ..models.pharmacy_models import (
        Prescription, Drug, DrugStockLot,
        StockTransaction, DispensingRecord, DispensingItem
    )
    body = await request.json()

    rx = db.query(Prescription).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(404, "Prescription not found / ไม่พบใบสั่งยา")
    if rx.status not in ("verified", "partially_dispensed"):
        raise HTTPException(400, f"Must be verified first / ต้องตรวจสอบก่อน (status: {rx.status})")

    disp = DispensingRecord(
        id=str(uuid.uuid4()),
        prescription_id=rx_id,
        patient_id=rx.patient_id,
        dispensed_by=current_user.id,
        counseling_notes=body.get("counseling_notes"),
        counseling_notes_th=body.get("counseling_notes_th"),
    )
    db.add(disp)

    dispensed_items = []
    for item_data in body.get("items", []):
        drug = db.query(Drug).filter(Drug.id == item_data["drug_id"]).first()
        if not drug:
            raise HTTPException(404, f"Drug {item_data['drug_id']} not found")

        qty_needed = int(item_data["quantity"])

        # FIFO: earliest expiry first, skip expired lots
        lots = db.query(DrugStockLot).filter(
            DrugStockLot.drug_id == drug.id,
            DrugStockLot.is_active == True,
            DrugStockLot.current_quantity > 0,
            DrugStockLot.expiry_date > date.today(),
        ).order_by(DrugStockLot.expiry_date).all()

        total_available = sum(l.current_quantity for l in lots)
        if total_available < qty_needed:
            raise HTTPException(400,
                f"Insufficient stock for {drug.generic_name}: need {qty_needed}, have {total_available} / "
                f"สต็อกไม่เพียงพอ: {drug.generic_name_th or drug.generic_name}")

        remaining = qty_needed
        used_lot = None
        for lot in lots:
            if remaining <= 0:
                break
            take = min(remaining, lot.current_quantity)
            lot.current_quantity -= take
            remaining -= take
            used_lot = lot

            tx = StockTransaction(
                id=str(uuid.uuid4()),
                drug_id=drug.id, lot_id=lot.id,
                transaction_type="dispense", quantity=-take,
                balance_after=(drug.current_stock or 0) - (qty_needed - remaining),
                reference_type="prescription", reference_id=rx_id,
                performed_by=current_user.id,
            )
            db.add(tx)

        drug.current_stock = (drug.current_stock or 0) - qty_needed

        disp_item = DispensingItem(
            id=str(uuid.uuid4()),
            dispensing_id=disp.id, drug_id=drug.id,
            lot_id=used_lot.id if used_lot else None,
            quantity_dispensed=qty_needed,
            instructions_en=item_data.get("instructions_en"),
            instructions_th=item_data.get("instructions_th"),
        )
        db.add(disp_item)
        dispensed_items.append({
            "drug_name": drug.generic_name, "drug_name_th": drug.generic_name_th,
            "quantity": qty_needed, "unit": drug.unit,
        })

    rx.status = "dispensed"
    rx.dispensed_by = current_user.id
    rx.dispensed_at = datetime.now(timezone.utc)

    _audit(db, current_user, "CREATE", "dispensing", disp.id,
           f"Dispensed Rx {rx.rx_number}: {len(dispensed_items)} items", request)
    db.commit()

    return {
        "dispense_id": disp.id, "rx_id": rx_id, "rx_number": rx.rx_number,
        "status": "dispensed",
        "dispensed_by": f"{current_user.first_name_en} {current_user.last_name_en}",
        "dispensed_at": rx.dispensed_at.isoformat(),
        "items": dispensed_items,
        "label_ready": True,
        "message": f"Dispensed / จ่ายยาสำเร็จ — {len(dispensed_items)} รายการ",
    }


# ══════════════════════════════════════════════════════════
# 4. LABEL GENERATION / พิมพ์ฉลากยา (ไทย/อังกฤษ)
# ══════════════════════════════════════════════════════════

@router.post("/labels/generate")
async def generate_label(
    request: Request,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Generate bilingual label data. / สร้างข้อมูลฉลากยาสองภาษา (70×35mm)"""
    body = await request.json()
    now = datetime.now()

    label = {
        "id": str(uuid.uuid4()),
        "label_format": "70x35mm",
        "clinic_name_en": "Life by Dr. Pat",
        "clinic_name_th": "คลินิก ไลฟ์ บาย ดร.แพท",
        "clinic_phone": body.get("clinic_phone", "02-XXX-XXXX"),
        "patient_hn": body.get("patient_hn", ""),
        "patient_name_en": body.get("patient_name_en", ""),
        "patient_name_th": body.get("patient_name_th", ""),
        "drug_name_en": body.get("drug_name_en", ""),
        "drug_name_th": body.get("drug_name_th", ""),
        "strength": body.get("strength", ""),
        "form_en": body.get("form_en", ""),
        "form_th": body.get("form_th", ""),
        "quantity": body.get("quantity", 0),
        "unit_en": body.get("unit_en", ""),
        "unit_th": body.get("unit_th", ""),
        "dosage_en": body.get("dosage_en", ""),
        "dosage_th": body.get("dosage_th", ""),
        "frequency_en": body.get("frequency_en", ""),
        "frequency_th": body.get("frequency_th", ""),
        "route_en": body.get("route_en", ""),
        "route_th": body.get("route_th", ""),
        "instructions_en": body.get("instructions_en", ""),
        "instructions_th": body.get("instructions_th", ""),
        "warnings_en": body.get("warnings_en", []),
        "warnings_th": body.get("warnings_th", []),
        "prescriber_name": body.get("prescriber_name", ""),
        "dispensed_date": body.get("dispense_date", now.strftime("%d/%m/%Y")),
        "dispensed_date_th": now.strftime("%d/%m/") + str(now.year + 543),
        "barcode_data": f"RX-{body.get('patient_hn', '')}-{now.strftime('%Y%m%d%H%M')}",
        "generated_at": now.isoformat(),
        "generated_by": f"{current_user.first_name_en} {current_user.last_name_en}",
    }

    _audit(db, current_user, "CREATE", "label", label["id"],
           f"Label: {body.get('patient_hn')} — {body.get('drug_name_en')}", request)
    db.commit()
    return label


@router.post("/labels/batch")
async def generate_batch_labels(
    request: Request,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Generate all labels for a prescription. / สร้างฉลากทั้งหมดของใบสั่งยา"""
    body = await request.json()
    now = datetime.now()
    labels = []

    for idx, item in enumerate(body.get("items", [])):
        labels.append({
            "id": str(uuid.uuid4()),
            "clinic_name_en": "Life by Dr. Pat",
            "clinic_name_th": "คลินิก ไลฟ์ บาย ดร.แพท",
            "patient_hn": body.get("patient_hn"),
            "patient_name_en": body.get("patient_name_en"),
            "patient_name_th": body.get("patient_name_th"),
            "drug_name_en": item.get("drug_name_en", ""),
            "drug_name_th": item.get("drug_name_th", ""),
            "strength": item.get("strength", ""),
            "form_en": item.get("form_en", ""),
            "form_th": item.get("form_th", ""),
            "quantity": item.get("quantity", 0),
            "unit_en": item.get("unit_en", ""),
            "unit_th": item.get("unit_th", ""),
            "dosage_en": item.get("dosage_en", ""),
            "dosage_th": item.get("dosage_th", ""),
            "frequency_en": item.get("frequency_en", ""),
            "frequency_th": item.get("frequency_th", ""),
            "route_en": item.get("route_en", ""),
            "route_th": item.get("route_th", ""),
            "instructions_en": item.get("instructions_en", ""),
            "instructions_th": item.get("instructions_th", ""),
            "warnings_en": item.get("warnings_en", []),
            "warnings_th": item.get("warnings_th", []),
            "dispensed_date": now.strftime("%d/%m/%Y"),
            "dispensed_date_th": now.strftime("%d/%m/") + str(now.year + 543),
            "barcode_data": f"RX-{body.get('patient_hn','')}-{now.strftime('%Y%m%d%H%M')}-{idx+1}",
        })

    return {"rx_id": body.get("rx_id"), "labels": labels, "total_labels": len(labels)}


# ══════════════════════════════════════════════════════════
# 5. DASHBOARD & REPORTS / แดชบอร์ดและรายงาน
# ══════════════════════════════════════════════════════════

@router.get("/dashboard")
async def pharmacy_dashboard(
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    """Dashboard stats. / สถิติแดชบอร์ดเภสัชกรรม"""
    from ..models.pharmacy_models import Drug, Prescription, DrugStockLot

    today = date.today()
    total_drugs = db.query(Drug).filter(Drug.is_active == True).count()
    total_stock_value = db.query(func.sum(Drug.current_stock * Drug.unit_cost)).filter(Drug.is_active == True).scalar() or 0
    low_stock = db.query(Drug).filter(Drug.is_active == True, Drug.current_stock <= Drug.reorder_level, Drug.current_stock > 0).count()
    out_of_stock = db.query(Drug).filter(Drug.is_active == True, Drug.current_stock == 0).count()
    expiring_30d = db.query(DrugStockLot).filter(
        DrugStockLot.is_active == True, DrugStockLot.current_quantity > 0,
        DrugStockLot.expiry_date <= today + timedelta(30), DrugStockLot.expiry_date > today,
    ).count()
    pending_rx = db.query(Prescription).filter(Prescription.status == "pending").count()
    verified_rx = db.query(Prescription).filter(Prescription.status == "verified").count()
    dispensed_today = db.query(Prescription).filter(
        Prescription.status == "dispensed", func.date(Prescription.dispensed_at) == today,
    ).count()

    return {
        "total_drugs": total_drugs, "total_stock_value": float(total_stock_value),
        "low_stock_items": low_stock, "out_of_stock_items": out_of_stock,
        "expiring_30d": expiring_30d, "pending_prescriptions": pending_rx,
        "verified_prescriptions": verified_rx, "dispensed_today": dispensed_today,
        "today": today.isoformat(),
    }


@router.get("/reports/consumption")
async def consumption_report(
    drug_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(require_roles(["pharmacist", "admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Consumption report. / รายงานการใช้ยา"""
    from ..models.pharmacy_models import StockTransaction, Drug

    q = db.query(StockTransaction).filter(StockTransaction.transaction_type == "dispense")
    if drug_id:
        q = q.filter(StockTransaction.drug_id == drug_id)
    if date_from:
        q = q.filter(StockTransaction.created_at >= date_from)
    if date_to:
        q = q.filter(StockTransaction.created_at <= date_to)

    txs = q.order_by(desc(StockTransaction.created_at)).all()

    by_drug = {}
    for tx in txs:
        did = tx.drug_id
        if did not in by_drug:
            drug = db.query(Drug).filter(Drug.id == did).first()
            by_drug[did] = {
                "drug_id": did,
                "drug_name": drug.generic_name if drug else "Unknown",
                "drug_name_th": drug.generic_name_th if drug else None,
                "total_dispensed": 0, "unit": drug.unit if drug else "",
            }
        by_drug[did]["total_dispensed"] += abs(tx.quantity)

    return {
        "period": {"from": date_from, "to": date_to},
        "items": list(by_drug.values()),
        "total_items_dispensed": sum(d["total_dispensed"] for d in by_drug.values()),
    }


# ── Translation endpoint for frontend i18n ────────────────
@router.get("/translations")
async def get_pharmacy_translations():
    """Return pharmacy UI translations. / คืนค่าคำแปล"""
    from ..schemas.pharmacy_schemas import (
        FREQUENCY_OPTIONS, ROUTE_OPTIONS, FORM_OPTIONS,
        CATEGORY_OPTIONS, WARNING_PRESETS
    )
    return {
        "frequencies": FREQUENCY_OPTIONS,
        "routes": ROUTE_OPTIONS,
        "forms": FORM_OPTIONS,
        "categories": CATEGORY_OPTIONS,
        "warning_presets": WARNING_PRESETS,
    }
