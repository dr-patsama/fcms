"""
FCMS Module 5 — Medical Supply API Routes / เส้นทาง API เวชภัณฑ์
Full CRUD: suppliers, supply catalogue, stock management (FIFO), requisitions,
usage logging, expiry/low-stock alerts, dashboard & reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_
from datetime import datetime, timezone, date, timedelta
from typing import Optional
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/supplies", tags=["Medical Supply / เวชภัณฑ์"])

# ── Helpers ───────────────────────────────────────────────

_req_counter = 0

def _next_req_number(db: Session) -> str:
    global _req_counter
    year = datetime.now().year
    _req_counter += 1
    return f"REQ-{year}-{_req_counter:05d}"


_grn_counter = 0

def _next_grn_number() -> str:
    global _grn_counter
    year = datetime.now().year
    _grn_counter += 1
    return f"GRN-{year}-{_grn_counter:05d}"


def _audit(db, user, action, resource_type, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()), user_id=user.id if user else None,
        action=action, module="medical_supply", resource_type=resource_type,
        resource_id=resource_id, detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


# ══════════════════════════════════════════════════════════
# 1. SUPPLIER MANAGEMENT / จัดการผู้จำหน่าย
# ══════════════════════════════════════════════════════════

@router.get("/suppliers")
async def list_suppliers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """List suppliers with search & pagination. / แสดงรายการผู้จำหน่าย"""
    from ..models.supply_models import Supplier

    q = db.query(Supplier)
    if active_only:
        q = q.filter(Supplier.is_active == True)
    if search:
        s = f"%{search}%"
        q = q.filter(or_(
            Supplier.name.ilike(s),
            Supplier.name_th.ilike(s),
            Supplier.code.ilike(s),
            Supplier.contact_person.ilike(s),
        ))

    total = q.count()
    suppliers = q.order_by(Supplier.name).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "suppliers": [{
            "id": s.id, "name": s.name, "name_th": s.name_th,
            "code": s.code, "contact_person": s.contact_person,
            "phone": s.phone, "email": s.email,
            "payment_terms": s.payment_terms, "is_active": s.is_active,
        } for s in suppliers],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/suppliers")
async def create_supplier(
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "lab_supervisor", "pharmacist"])),
    db: Session = Depends(get_db),
):
    """Create a new supplier. / เพิ่มผู้จำหน่ายใหม่"""
    from ..models.supply_models import Supplier
    body = await request.json()

    if not body.get("name"):
        raise HTTPException(400, "Supplier name is required / จำเป็นต้องกรอกชื่อผู้จำหน่าย")

    supplier = Supplier(
        id=str(uuid.uuid4()),
        name=body["name"],
        name_th=body.get("name_th"),
        code=body.get("code"),
        contact_person=body.get("contact_person"),
        phone=body.get("phone"),
        email=body.get("email"),
        address=body.get("address"),
        address_th=body.get("address_th"),
        tax_id=body.get("tax_id"),
        payment_terms=body.get("payment_terms"),
        notes=body.get("notes"),
        created_by=current_user.id,
    )
    db.add(supplier)
    _audit(db, current_user, "CREATE", "supplier", supplier.id,
           f"Supplier created: {supplier.name}", request)
    db.commit()
    db.refresh(supplier)

    return {"id": supplier.id, "name": supplier.name, "message": "Supplier created / เพิ่มผู้จำหน่ายสำเร็จ"}


@router.get("/suppliers/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Get supplier detail. / รายละเอียดผู้จำหน่าย"""
    from ..models.supply_models import Supplier
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(404, "Supplier not found / ไม่พบผู้จำหน่าย")

    return {
        "id": supplier.id, "name": supplier.name, "name_th": supplier.name_th,
        "code": supplier.code, "contact_person": supplier.contact_person,
        "phone": supplier.phone, "email": supplier.email,
        "address": supplier.address, "address_th": supplier.address_th,
        "tax_id": supplier.tax_id, "payment_terms": supplier.payment_terms,
        "notes": supplier.notes, "is_active": supplier.is_active,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
    }


@router.patch("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "lab_supervisor"])),
    db: Session = Depends(get_db),
):
    """Update supplier. / แก้ไขผู้จำหน่าย"""
    from ..models.supply_models import Supplier
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(404, "Supplier not found / ไม่พบผู้จำหน่าย")

    body = await request.json()
    updatable = [
        "name", "name_th", "code", "contact_person", "phone", "email",
        "address", "address_th", "tax_id", "payment_terms", "notes", "is_active"
    ]
    changes = []
    for field in updatable:
        if field in body:
            old = getattr(supplier, field)
            setattr(supplier, field, body[field])
            changes.append(f"{field}: {old} → {body[field]}")

    _audit(db, current_user, "UPDATE", "supplier", supplier.id,
           "; ".join(changes[:5]), request)
    db.commit()
    return {"id": supplier.id, "message": "Supplier updated / แก้ไขผู้จำหน่ายสำเร็จ"}


# ══════════════════════════════════════════════════════════
# 2. SUPPLY CATALOGUE / รายการเวชภัณฑ์
# ══════════════════════════════════════════════════════════

@router.get("/items")
async def list_supplies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    department: Optional[str] = None,
    low_stock_only: bool = False,
    active_only: bool = True,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """List supplies with search, filter, pagination. / แสดงรายการเวชภัณฑ์"""
    from ..models.supply_models import MedicalSupply

    q = db.query(MedicalSupply)
    if active_only:
        q = q.filter(MedicalSupply.is_active == True)
    if search:
        s = f"%{search}%"
        q = q.filter(or_(
            MedicalSupply.name_en.ilike(s),
            MedicalSupply.name_th.ilike(s),
            MedicalSupply.sku.ilike(s),
            MedicalSupply.catalog_number.ilike(s),
        ))
    if category:
        q = q.filter(MedicalSupply.category == category)
    if department:
        q = q.filter(or_(MedicalSupply.department == department, MedicalSupply.department == "all"))
    if low_stock_only:
        q = q.filter(MedicalSupply.current_stock <= MedicalSupply.reorder_level)

    total = q.count()
    items = q.order_by(MedicalSupply.name_en).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [{
            "id": i.id, "name_en": i.name_en, "name_th": i.name_th,
            "category": i.category, "subcategory": i.subcategory,
            "sku": i.sku, "catalog_number": i.catalog_number,
            "unit": i.unit, "unit_th": i.unit_th,
            "pack_size": i.pack_size, "manufacturer": i.manufacturer,
            "unit_cost": float(i.unit_cost) if i.unit_cost else None,
            "current_stock": i.current_stock or 0,
            "reorder_level": i.reorder_level,
            "department": i.department,
            "requires_refrigeration": i.requires_refrigeration,
            "requires_sterile": i.requires_sterile,
            "is_active": i.is_active,
            "stock_status": "out_of_stock" if (i.current_stock or 0) == 0
                           else "low" if (i.current_stock or 0) <= (i.reorder_level or 0)
                           else "ok",
        } for i in items],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/items")
async def create_supply(
    request: Request,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor", "embryologist", "pharmacist"
    ])),
    db: Session = Depends(get_db),
):
    """Create a new supply item. / เพิ่มเวชภัณฑ์ใหม่"""
    from ..models.supply_models import MedicalSupply
    body = await request.json()

    for f in ["name_en", "category", "unit"]:
        if not body.get(f):
            raise HTTPException(400, f"{f} is required / จำเป็นต้องกรอก {f}")

    supply = MedicalSupply(
        id=str(uuid.uuid4()),
        name_en=body["name_en"],
        name_th=body.get("name_th"),
        description_en=body.get("description_en"),
        description_th=body.get("description_th"),
        category=body["category"],
        subcategory=body.get("subcategory"),
        sku=body.get("sku"),
        catalog_number=body.get("catalog_number"),
        unit=body["unit"],
        unit_th=body.get("unit_th"),
        pack_size=body.get("pack_size", 1),
        manufacturer=body.get("manufacturer"),
        default_supplier_id=body.get("default_supplier_id"),
        reorder_level=body.get("reorder_level", 10),
        reorder_quantity=body.get("reorder_quantity", 50),
        unit_cost=body.get("unit_cost"),
        storage_condition=body.get("storage_condition"),
        storage_condition_th=body.get("storage_condition_th"),
        requires_refrigeration=body.get("requires_refrigeration", False),
        requires_sterile=body.get("requires_sterile", False),
        department=body.get("department", "all"),
        current_stock=0,
        created_by=current_user.id,
    )
    db.add(supply)
    _audit(db, current_user, "CREATE", "medical_supply", supply.id,
           f"Supply created: {supply.name_en} ({supply.category})", request)
    db.commit()
    db.refresh(supply)

    return {"id": supply.id, "name_en": supply.name_en,
            "message": "Supply created / เพิ่มเวชภัณฑ์สำเร็จ"}


@router.get("/items/{supply_id}")
async def get_supply(
    supply_id: str,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Get supply detail with stock lots. / รายละเอียดเวชภัณฑ์พร้อมสต็อก"""
    from ..models.supply_models import MedicalSupply, SupplyStockLot, SupplyTransaction

    supply = db.query(MedicalSupply).filter(MedicalSupply.id == supply_id).first()
    if not supply:
        raise HTTPException(404, "Supply not found / ไม่พบเวชภัณฑ์")

    lots = db.query(SupplyStockLot).filter(
        SupplyStockLot.supply_id == supply_id,
        SupplyStockLot.is_active == True,
        SupplyStockLot.current_quantity > 0,
    ).order_by(SupplyStockLot.expiry_date.asc().nullslast()).all()

    recent_txs = db.query(SupplyTransaction).filter(
        SupplyTransaction.supply_id == supply_id
    ).order_by(desc(SupplyTransaction.created_at)).limit(20).all()

    return {
        "id": supply.id, "name_en": supply.name_en, "name_th": supply.name_th,
        "description_en": supply.description_en, "description_th": supply.description_th,
        "category": supply.category, "subcategory": supply.subcategory,
        "sku": supply.sku, "catalog_number": supply.catalog_number,
        "unit": supply.unit, "unit_th": supply.unit_th, "pack_size": supply.pack_size,
        "manufacturer": supply.manufacturer,
        "default_supplier_id": supply.default_supplier_id,
        "reorder_level": supply.reorder_level, "reorder_quantity": supply.reorder_quantity,
        "unit_cost": float(supply.unit_cost) if supply.unit_cost else None,
        "storage_condition": supply.storage_condition,
        "storage_condition_th": supply.storage_condition_th,
        "requires_refrigeration": supply.requires_refrigeration,
        "requires_sterile": supply.requires_sterile,
        "department": supply.department,
        "current_stock": supply.current_stock or 0,
        "is_active": supply.is_active,
        "stock_lots": [{
            "id": l.id, "lot_number": l.lot_number,
            "expiry_date": l.expiry_date.isoformat() if l.expiry_date else None,
            "current_quantity": l.current_quantity,
            "initial_quantity": l.initial_quantity,
            "unit_cost": float(l.unit_cost) if l.unit_cost else None,
            "grn_number": l.grn_number,
            "received_at": l.received_at.isoformat() if l.received_at else None,
        } for l in lots],
        "recent_transactions": [{
            "id": t.id, "type": t.transaction_type,
            "quantity": t.quantity, "balance_after": t.balance_after,
            "department": t.department, "reason": t.reason,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in recent_txs],
    }


@router.patch("/items/{supply_id}")
async def update_supply(
    supply_id: str,
    request: Request,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor", "embryologist"
    ])),
    db: Session = Depends(get_db),
):
    """Update supply item. / แก้ไขเวชภัณฑ์"""
    from ..models.supply_models import MedicalSupply
    supply = db.query(MedicalSupply).filter(MedicalSupply.id == supply_id).first()
    if not supply:
        raise HTTPException(404, "Supply not found / ไม่พบเวชภัณฑ์")

    body = await request.json()
    updatable = [
        "name_en", "name_th", "description_en", "description_th",
        "category", "subcategory", "sku", "catalog_number",
        "unit", "unit_th", "pack_size", "manufacturer", "default_supplier_id",
        "reorder_level", "reorder_quantity", "unit_cost",
        "storage_condition", "storage_condition_th",
        "requires_refrigeration", "requires_sterile",
        "department", "is_active",
    ]
    changes = []
    for field in updatable:
        if field in body:
            old = getattr(supply, field)
            setattr(supply, field, body[field])
            changes.append(f"{field}: {old} → {body[field]}")

    _audit(db, current_user, "UPDATE", "medical_supply", supply.id,
           "; ".join(changes[:5]), request)
    db.commit()
    return {"id": supply.id, "message": "Supply updated / แก้ไขเวชภัณฑ์สำเร็จ"}


# ══════════════════════════════════════════════════════════
# 3. STOCK MANAGEMENT / จัดการสต็อก
# ══════════════════════════════════════════════════════════

@router.post("/stock/receive")
async def receive_stock(
    request: Request,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor", "embryologist",
        "lab_technician", "pharmacist"
    ])),
    db: Session = Depends(get_db),
):
    """Receive supply stock with lot/expiry tracking. / รับสต็อกเวชภัณฑ์เข้า"""
    from ..models.supply_models import MedicalSupply, SupplyStockLot, SupplyTransaction
    body = await request.json()

    supply = db.query(MedicalSupply).filter(MedicalSupply.id == body.get("supply_id")).first()
    if not supply:
        raise HTTPException(404, "Supply not found / ไม่พบเวชภัณฑ์")

    qty = body.get("quantity", 0)
    if qty <= 0:
        raise HTTPException(400, "Quantity must be > 0 / จำนวนต้องมากกว่า 0")

    lot = SupplyStockLot(
        id=str(uuid.uuid4()),
        supply_id=supply.id,
        lot_number=body.get("lot_number", "N/A"),
        expiry_date=body.get("expiry_date"),
        initial_quantity=qty,
        current_quantity=qty,
        unit_cost=body.get("unit_cost") or supply.unit_cost,
        supplier_id=body.get("supplier_id") or supply.default_supplier_id,
        po_number=body.get("po_number"),
        invoice_number=body.get("invoice_number"),
        grn_number=body.get("grn_number") or _next_grn_number(),
        received_by=current_user.id,
        notes=body.get("notes"),
    )
    db.add(lot)

    supply.current_stock = (supply.current_stock or 0) + qty

    tx = SupplyTransaction(
        id=str(uuid.uuid4()),
        supply_id=supply.id,
        lot_id=lot.id,
        transaction_type="receive",
        quantity=qty,
        balance_after=supply.current_stock,
        reference_type="po",
        reason=f"GRN: {lot.grn_number}",
        performed_by=current_user.id,
    )
    db.add(tx)

    _audit(db, current_user, "CREATE", "supply_stock_receive", lot.id,
           f"Received {qty} × {supply.name_en} (Lot: {lot.lot_number})", request)
    db.commit()

    return {
        "lot_id": lot.id, "grn_number": lot.grn_number,
        "supply": supply.name_en, "quantity": qty,
        "new_stock": supply.current_stock,
        "message": "Stock received / รับสต็อกสำเร็จ",
    }


@router.post("/stock/adjust")
async def adjust_stock(
    request: Request,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor"
    ])),
    db: Session = Depends(get_db),
):
    """Manual stock adjustment with mandatory reason. / ปรับสต็อกด้วยตนเอง"""
    from ..models.supply_models import MedicalSupply, SupplyStockLot, SupplyTransaction
    body = await request.json()

    supply = db.query(MedicalSupply).filter(MedicalSupply.id == body.get("supply_id")).first()
    if not supply:
        raise HTTPException(404, "Supply not found / ไม่พบเวชภัณฑ์")

    adj_type = body.get("adjustment_type")
    qty = body.get("quantity", 0)
    reason = body.get("reason", "").strip()
    if qty <= 0:
        raise HTTPException(400, "Quantity must be > 0 / จำนวนต้องมากกว่า 0")
    if not reason:
        raise HTTPException(400, "Reason is required / จำเป็นต้องระบุเหตุผล")

    lot_id = body.get("lot_id")
    if adj_type in ("remove", "expired_write_off") and lot_id:
        lot = db.query(SupplyStockLot).filter(SupplyStockLot.id == lot_id).first()
        if lot and lot.current_quantity >= qty:
            lot.current_quantity -= qty
        elif lot:
            raise HTTPException(400, f"Insufficient lot qty ({lot.current_quantity}) / จำนวนในล็อตไม่พอ")

    if adj_type == "add":
        supply.current_stock = (supply.current_stock or 0) + qty
        tx_type = "adjust_add"
    elif adj_type in ("remove", "expired_write_off"):
        if (supply.current_stock or 0) < qty:
            raise HTTPException(400, "Insufficient stock / สต็อกไม่เพียงพอ")
        supply.current_stock -= qty
        tx_type = adj_type if adj_type == "expired_write_off" else "adjust_remove"
    else:
        raise HTTPException(400, "Invalid adjustment type / ประเภทการปรับไม่ถูกต้อง")

    tx = SupplyTransaction(
        id=str(uuid.uuid4()),
        supply_id=supply.id,
        lot_id=lot_id,
        transaction_type=tx_type,
        quantity=qty if adj_type == "add" else -qty,
        balance_after=supply.current_stock,
        reference_type="adjustment",
        reason=reason,
        performed_by=current_user.id,
    )
    db.add(tx)

    _audit(db, current_user, "UPDATE", "supply_stock_adjust", supply.id,
           f"Adjust {adj_type}: {qty} × {supply.name_en} — {reason}", request)
    db.commit()

    return {
        "supply_id": supply.id, "adjustment": adj_type,
        "quantity": qty, "new_stock": supply.current_stock,
        "message": "Stock adjusted / ปรับสต็อกสำเร็จ",
    }


@router.get("/stock/levels")
async def stock_levels(
    category: Optional[str] = None,
    department: Optional[str] = None,
    low_stock_only: bool = False,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Current stock levels with status indicators. / ระดับสต็อกปัจจุบัน"""
    from ..models.supply_models import MedicalSupply

    q = db.query(MedicalSupply).filter(MedicalSupply.is_active == True)
    if category:
        q = q.filter(MedicalSupply.category == category)
    if department:
        q = q.filter(or_(MedicalSupply.department == department, MedicalSupply.department == "all"))
    if low_stock_only:
        q = q.filter(MedicalSupply.current_stock <= MedicalSupply.reorder_level)

    items = q.order_by(MedicalSupply.category, MedicalSupply.name_en).all()

    return {
        "items": [{
            "id": i.id, "name_en": i.name_en, "name_th": i.name_th,
            "category": i.category, "unit": i.unit,
            "current_stock": i.current_stock or 0,
            "reorder_level": i.reorder_level,
            "reorder_quantity": i.reorder_quantity,
            "department": i.department,
            "status": "out_of_stock" if (i.current_stock or 0) == 0
                      else "low" if (i.current_stock or 0) <= (i.reorder_level or 0)
                      else "ok",
            "suggested_order": max(0, (i.reorder_quantity or 50) - (i.current_stock or 0))
                               if (i.current_stock or 0) <= (i.reorder_level or 0) else 0,
        } for i in items],
        "total": len(items),
    }


# ══════════════════════════════════════════════════════════
# 4. REQUISITIONS / ใบเบิกเวชภัณฑ์
# ══════════════════════════════════════════════════════════

@router.get("/requisitions")
async def list_requisitions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """List requisitions. / แสดงรายการใบเบิก"""
    from ..models.supply_models import SupplyRequisition

    q = db.query(SupplyRequisition)
    if status:
        q = q.filter(SupplyRequisition.status == status)
    if department:
        q = q.filter(SupplyRequisition.department == department)

    total = q.count()
    reqs = q.order_by(desc(SupplyRequisition.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "requisitions": [{
            "id": r.id, "req_number": r.req_number,
            "department": r.department, "status": r.status,
            "priority": r.priority, "notes": r.notes,
            "item_count": len(r.items) if r.items else 0,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reqs],
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/requisitions")
async def create_requisition(
    request: Request,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Create a new supply requisition. / สร้างใบเบิกเวชภัณฑ์"""
    from ..models.supply_models import SupplyRequisition, RequisitionItem
    body = await request.json()

    if not body.get("department"):
        raise HTTPException(400, "Department is required / จำเป็นต้องระบุแผนก")
    if not body.get("items") or len(body["items"]) == 0:
        raise HTTPException(400, "At least one item required / ต้องมีอย่างน้อย 1 รายการ")

    req = SupplyRequisition(
        id=str(uuid.uuid4()),
        req_number=_next_req_number(db),
        department=body["department"],
        requested_by=current_user.id,
        priority=body.get("priority", "normal"),
        notes=body.get("notes"),
        notes_th=body.get("notes_th"),
    )
    db.add(req)

    for item_data in body["items"]:
        item = RequisitionItem(
            id=str(uuid.uuid4()),
            requisition_id=req.id,
            supply_id=item_data["supply_id"],
            quantity_requested=item_data["quantity_requested"],
            notes=item_data.get("notes"),
        )
        db.add(item)

    _audit(db, current_user, "CREATE", "requisition", req.id,
           f"Requisition {req.req_number} — {body['department']} — {len(body['items'])} items", request)
    db.commit()

    return {
        "id": req.id, "req_number": req.req_number,
        "message": "Requisition created / สร้างใบเบิกสำเร็จ",
    }


@router.get("/requisitions/{req_id}")
async def get_requisition(
    req_id: str,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Get requisition detail with items. / รายละเอียดใบเบิก"""
    from ..models.supply_models import SupplyRequisition, MedicalSupply

    req = db.query(SupplyRequisition).filter(SupplyRequisition.id == req_id).first()
    if not req:
        raise HTTPException(404, "Requisition not found / ไม่พบใบเบิก")

    items_out = []
    for item in req.items:
        supply = db.query(MedicalSupply).filter(MedicalSupply.id == item.supply_id).first()
        items_out.append({
            "id": item.id, "supply_id": item.supply_id,
            "supply_name_en": supply.name_en if supply else "Unknown",
            "supply_name_th": supply.name_th if supply else None,
            "unit": supply.unit if supply else "",
            "quantity_requested": item.quantity_requested,
            "quantity_issued": item.quantity_issued or 0,
            "notes": item.notes,
        })

    return {
        "id": req.id, "req_number": req.req_number,
        "department": req.department, "status": req.status,
        "priority": req.priority,
        "notes": req.notes, "notes_th": req.notes_th,
        "items": items_out,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "approved_at": req.approved_at.isoformat() if req.approved_at else None,
        "issued_at": req.issued_at.isoformat() if req.issued_at else None,
    }


@router.post("/requisitions/{req_id}/approve")
async def approve_requisition(
    req_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "lab_supervisor"])),
    db: Session = Depends(get_db),
):
    """Approve a requisition. / อนุมัติใบเบิก"""
    from ..models.supply_models import SupplyRequisition

    req = db.query(SupplyRequisition).filter(SupplyRequisition.id == req_id).first()
    if not req:
        raise HTTPException(404, "Requisition not found / ไม่พบใบเบิก")
    if req.status != "pending":
        raise HTTPException(400, f"Cannot approve — status is {req.status} / ไม่สามารถอนุมัติ — สถานะ {req.status}")

    req.status = "approved"
    req.approved_by = current_user.id
    req.approved_at = datetime.now(timezone.utc)

    _audit(db, current_user, "UPDATE", "requisition", req.id,
           f"Approved {req.req_number}", request)
    db.commit()
    return {"id": req.id, "status": "approved", "message": "Requisition approved / อนุมัติใบเบิกสำเร็จ"}


@router.post("/requisitions/{req_id}/reject")
async def reject_requisition(
    req_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin", "lab_supervisor"])),
    db: Session = Depends(get_db),
):
    """Reject a requisition. / ปฏิเสธใบเบิก"""
    from ..models.supply_models import SupplyRequisition
    body = await request.json()

    req = db.query(SupplyRequisition).filter(SupplyRequisition.id == req_id).first()
    if not req:
        raise HTTPException(404, "Requisition not found / ไม่พบใบเบิก")
    if req.status != "pending":
        raise HTTPException(400, f"Cannot reject — status is {req.status}")

    req.status = "rejected"
    req.rejected_by = current_user.id
    req.rejected_at = datetime.now(timezone.utc)
    req.reject_reason = body.get("reason", "")

    _audit(db, current_user, "UPDATE", "requisition", req.id,
           f"Rejected {req.req_number}: {req.reject_reason}", request)
    db.commit()
    return {"id": req.id, "status": "rejected", "message": "Requisition rejected / ปฏิเสธใบเบิกสำเร็จ"}


@router.post("/requisitions/{req_id}/issue")
async def issue_requisition(
    req_id: str,
    request: Request,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor", "lab_technician"
    ])),
    db: Session = Depends(get_db),
):
    """Issue (dispense) supplies against an approved requisition using FIFO. / จ่ายเวชภัณฑ์ตามใบเบิก"""
    from ..models.supply_models import (
        SupplyRequisition, RequisitionItem, MedicalSupply,
        SupplyStockLot, SupplyTransaction
    )
    body = await request.json()

    req = db.query(SupplyRequisition).filter(SupplyRequisition.id == req_id).first()
    if not req:
        raise HTTPException(404, "Requisition not found / ไม่พบใบเบิก")
    if req.status not in ("approved", "partially_issued"):
        raise HTTPException(400, f"Cannot issue — status is {req.status}")

    issued_items = []
    for issue in body.get("items", []):
        item = db.query(RequisitionItem).filter(RequisitionItem.id == issue["item_id"]).first()
        if not item:
            continue

        qty_to_issue = issue.get("quantity_issued", 0)
        if qty_to_issue <= 0:
            continue

        supply = db.query(MedicalSupply).filter(MedicalSupply.id == item.supply_id).first()
        if not supply or (supply.current_stock or 0) < qty_to_issue:
            raise HTTPException(400,
                f"Insufficient stock for {supply.name_en if supply else 'unknown'} / สต็อกไม่เพียงพอ")

        # FIFO: deduct from oldest lots first
        remaining = qty_to_issue
        lots = db.query(SupplyStockLot).filter(
            SupplyStockLot.supply_id == item.supply_id,
            SupplyStockLot.is_active == True,
            SupplyStockLot.current_quantity > 0,
        ).order_by(SupplyStockLot.expiry_date.asc().nullslast()).all()

        for lot in lots:
            if remaining <= 0:
                break
            deduct = min(remaining, lot.current_quantity)
            lot.current_quantity -= deduct
            remaining -= deduct

            tx = SupplyTransaction(
                id=str(uuid.uuid4()),
                supply_id=supply.id,
                lot_id=lot.id,
                transaction_type="issue",
                quantity=-deduct,
                balance_after=(supply.current_stock or 0) - qty_to_issue + remaining,
                reference_type="requisition",
                reference_id=req.id,
                department=req.department,
                reason=f"REQ: {req.req_number}",
                performed_by=current_user.id,
            )
            db.add(tx)

        supply.current_stock = (supply.current_stock or 0) - qty_to_issue
        item.quantity_issued = (item.quantity_issued or 0) + qty_to_issue
        issued_items.append({"supply": supply.name_en, "qty": qty_to_issue})

    # Determine final status
    all_complete = all(
        (it.quantity_issued or 0) >= it.quantity_requested for it in req.items
    )
    any_issued = any((it.quantity_issued or 0) > 0 for it in req.items)

    if all_complete:
        req.status = "issued"
        req.issued_at = datetime.now(timezone.utc)
    elif any_issued:
        req.status = "partially_issued"

    req.issued_by = current_user.id

    _audit(db, current_user, "UPDATE", "requisition_issue", req.id,
           f"Issued {req.req_number}: {len(issued_items)} items", request)
    db.commit()

    return {
        "id": req.id, "req_number": req.req_number,
        "status": req.status, "issued_items": issued_items,
        "message": "Supplies issued / จ่ายเวชภัณฑ์สำเร็จ",
    }


# ══════════════════════════════════════════════════════════
# 5. USAGE LOG / บันทึกการใช้งาน
# ══════════════════════════════════════════════════════════

@router.post("/usage")
async def log_usage(
    request: Request,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Log supply usage per procedure/patient. / บันทึกการใช้เวชภัณฑ์"""
    from ..models.supply_models import (
        MedicalSupply, SupplyStockLot, SupplyTransaction, SupplyUsageLog
    )
    body = await request.json()

    supply = db.query(MedicalSupply).filter(MedicalSupply.id == body.get("supply_id")).first()
    if not supply:
        raise HTTPException(404, "Supply not found / ไม่พบเวชภัณฑ์")

    qty = body.get("quantity_used", 0)
    if qty <= 0:
        raise HTTPException(400, "Quantity must be > 0 / จำนวนต้องมากกว่า 0")
    if (supply.current_stock or 0) < qty:
        raise HTTPException(400, "Insufficient stock / สต็อกไม่เพียงพอ")

    # FIFO deduction
    remaining = qty
    lots = db.query(SupplyStockLot).filter(
        SupplyStockLot.supply_id == supply.id,
        SupplyStockLot.is_active == True,
        SupplyStockLot.current_quantity > 0,
    ).order_by(SupplyStockLot.expiry_date.asc().nullslast()).all()

    used_lot_id = None
    for lot in lots:
        if remaining <= 0:
            break
        deduct = min(remaining, lot.current_quantity)
        lot.current_quantity -= deduct
        remaining -= deduct
        if used_lot_id is None:
            used_lot_id = lot.id

    supply.current_stock -= qty

    # Transaction log
    tx = SupplyTransaction(
        id=str(uuid.uuid4()),
        supply_id=supply.id,
        lot_id=used_lot_id,
        transaction_type="issue",
        quantity=-qty,
        balance_after=supply.current_stock,
        reference_type="procedure",
        department=body.get("department", ""),
        reason=body.get("procedure_type", "usage"),
        performed_by=current_user.id,
    )
    db.add(tx)

    # Usage log entry
    usage = SupplyUsageLog(
        id=str(uuid.uuid4()),
        supply_id=supply.id,
        lot_id=used_lot_id,
        quantity_used=qty,
        department=body.get("department", ""),
        procedure_type=body.get("procedure_type"),
        patient_id=body.get("patient_id"),
        visit_id=body.get("visit_id"),
        used_by=current_user.id,
        notes=body.get("notes"),
    )
    db.add(usage)

    _audit(db, current_user, "CREATE", "supply_usage", usage.id,
           f"Used {qty} × {supply.name_en} ({body.get('procedure_type', '-')})", request)
    db.commit()

    return {
        "usage_id": usage.id, "supply": supply.name_en,
        "quantity_used": qty, "remaining_stock": supply.current_stock,
        "message": "Usage recorded / บันทึกการใช้สำเร็จ",
    }


@router.get("/usage")
async def list_usage(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    supply_id: Optional[str] = None,
    department: Optional[str] = None,
    procedure_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """List usage logs with filters. / แสดงบันทึกการใช้งาน"""
    from ..models.supply_models import SupplyUsageLog, MedicalSupply

    q = db.query(SupplyUsageLog)
    if supply_id:
        q = q.filter(SupplyUsageLog.supply_id == supply_id)
    if department:
        q = q.filter(SupplyUsageLog.department == department)
    if procedure_type:
        q = q.filter(SupplyUsageLog.procedure_type == procedure_type)
    if date_from:
        q = q.filter(SupplyUsageLog.created_at >= date_from)
    if date_to:
        q = q.filter(SupplyUsageLog.created_at <= date_to)

    total = q.count()
    logs = q.order_by(desc(SupplyUsageLog.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for log in logs:
        supply = db.query(MedicalSupply).filter(MedicalSupply.id == log.supply_id).first()
        result.append({
            "id": log.id,
            "supply_name_en": supply.name_en if supply else "Unknown",
            "supply_name_th": supply.name_th if supply else None,
            "quantity_used": log.quantity_used,
            "department": log.department,
            "procedure_type": log.procedure_type,
            "patient_id": log.patient_id,
            "notes": log.notes,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "usage_logs": result,
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ══════════════════════════════════════════════════════════
# 6. ALERTS / แจ้งเตือน
# ══════════════════════════════════════════════════════════

@router.get("/alerts/expiry")
async def expiry_alerts(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Expiring supply lots within N days. / เวชภัณฑ์ใกล้หมดอายุ"""
    from ..models.supply_models import SupplyStockLot, MedicalSupply

    today = date.today()
    cutoff = today + timedelta(days=days)

    lots = db.query(SupplyStockLot).filter(
        SupplyStockLot.is_active == True,
        SupplyStockLot.current_quantity > 0,
        SupplyStockLot.expiry_date != None,
        SupplyStockLot.expiry_date <= cutoff,
    ).order_by(SupplyStockLot.expiry_date.asc()).all()

    result = []
    for lot in lots:
        supply = db.query(MedicalSupply).filter(MedicalSupply.id == lot.supply_id).first()
        days_left = (lot.expiry_date - today).days if lot.expiry_date else None
        value = float(lot.unit_cost or 0) * lot.current_quantity

        result.append({
            "lot_id": lot.id,
            "supply_id": lot.supply_id,
            "supply_name_en": supply.name_en if supply else "Unknown",
            "supply_name_th": supply.name_th if supply else None,
            "lot_number": lot.lot_number,
            "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
            "days_left": days_left,
            "current_quantity": lot.current_quantity,
            "unit": supply.unit if supply else "",
            "value_at_risk": round(value, 2),
            "severity": "expired" if days_left is not None and days_left <= 0
                       else "critical" if days_left is not None and days_left <= 7
                       else "warning" if days_left is not None and days_left <= 30
                       else "info",
        })

    return {
        "alerts": result,
        "total": len(result),
        "cutoff_days": days,
        "total_value_at_risk": round(sum(r["value_at_risk"] for r in result), 2),
    }


@router.get("/alerts/low-stock")
async def low_stock_alerts(
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Supplies below reorder level. / เวชภัณฑ์ต่ำกว่าระดับสั่งซื้อ"""
    from ..models.supply_models import MedicalSupply

    items = db.query(MedicalSupply).filter(
        MedicalSupply.is_active == True,
        MedicalSupply.current_stock <= MedicalSupply.reorder_level,
    ).order_by(MedicalSupply.current_stock.asc()).all()

    return {
        "alerts": [{
            "id": i.id, "name_en": i.name_en, "name_th": i.name_th,
            "category": i.category, "unit": i.unit,
            "current_stock": i.current_stock or 0,
            "reorder_level": i.reorder_level,
            "reorder_quantity": i.reorder_quantity,
            "suggested_order": max(0, (i.reorder_quantity or 50) - (i.current_stock or 0)),
            "severity": "critical" if (i.current_stock or 0) == 0 else "warning",
        } for i in items],
        "total": len(items),
        "out_of_stock": sum(1 for i in items if (i.current_stock or 0) == 0),
    }


# ══════════════════════════════════════════════════════════
# 7. DASHBOARD & REPORTS / แดชบอร์ดและรายงาน
# ══════════════════════════════════════════════════════════

@router.get("/dashboard")
async def supply_dashboard(
    current_user: User = Depends(require_module_access("medical_supply")),
    db: Session = Depends(get_db),
):
    """Dashboard stats. / สถิติแดชบอร์ดเวชภัณฑ์"""
    from ..models.supply_models import (
        MedicalSupply, Supplier, SupplyRequisition, SupplyStockLot
    )

    today = date.today()
    total_items = db.query(MedicalSupply).filter(MedicalSupply.is_active == True).count()
    total_suppliers = db.query(Supplier).filter(Supplier.is_active == True).count()
    total_stock_value = db.query(
        func.sum(MedicalSupply.current_stock * MedicalSupply.unit_cost)
    ).filter(MedicalSupply.is_active == True).scalar() or 0
    low_stock = db.query(MedicalSupply).filter(
        MedicalSupply.is_active == True,
        MedicalSupply.current_stock <= MedicalSupply.reorder_level,
        MedicalSupply.current_stock > 0,
    ).count()
    out_of_stock = db.query(MedicalSupply).filter(
        MedicalSupply.is_active == True,
        MedicalSupply.current_stock == 0,
    ).count()
    expiring_30d = db.query(SupplyStockLot).filter(
        SupplyStockLot.is_active == True,
        SupplyStockLot.current_quantity > 0,
        SupplyStockLot.expiry_date != None,
        SupplyStockLot.expiry_date <= today + timedelta(30),
        SupplyStockLot.expiry_date > today,
    ).count()
    pending_reqs = db.query(SupplyRequisition).filter(
        SupplyRequisition.status == "pending"
    ).count()
    approved_reqs = db.query(SupplyRequisition).filter(
        SupplyRequisition.status == "approved"
    ).count()

    # Category breakdown
    categories = db.query(
        MedicalSupply.category,
        func.count(MedicalSupply.id),
        func.sum(MedicalSupply.current_stock * MedicalSupply.unit_cost),
    ).filter(
        MedicalSupply.is_active == True
    ).group_by(MedicalSupply.category).all()

    return {
        "total_items": total_items,
        "total_suppliers": total_suppliers,
        "total_stock_value": float(total_stock_value),
        "low_stock_items": low_stock,
        "out_of_stock_items": out_of_stock,
        "expiring_30d": expiring_30d,
        "pending_requisitions": pending_reqs,
        "approved_requisitions": approved_reqs,
        "categories": [{
            "category": c[0],
            "item_count": c[1],
            "value": float(c[2] or 0),
        } for c in categories],
        "today": today.isoformat(),
    }


@router.get("/reports/consumption")
async def consumption_report(
    supply_id: Optional[str] = None,
    category: Optional[str] = None,
    department: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(require_roles([
        "admin", "it_admin", "lab_supervisor"
    ])),
    db: Session = Depends(get_db),
):
    """Consumption report by supply/category/department. / รายงานการใช้เวชภัณฑ์"""
    from ..models.supply_models import SupplyUsageLog, MedicalSupply

    q = db.query(SupplyUsageLog)
    if supply_id:
        q = q.filter(SupplyUsageLog.supply_id == supply_id)
    if department:
        q = q.filter(SupplyUsageLog.department == department)
    if date_from:
        q = q.filter(SupplyUsageLog.created_at >= date_from)
    if date_to:
        q = q.filter(SupplyUsageLog.created_at <= date_to)

    logs = q.all()

    by_supply = {}
    for log in logs:
        sid = log.supply_id
        if sid not in by_supply:
            supply = db.query(MedicalSupply).filter(MedicalSupply.id == sid).first()
            if category and supply and supply.category != category:
                continue
            by_supply[sid] = {
                "supply_id": sid,
                "supply_name_en": supply.name_en if supply else "Unknown",
                "supply_name_th": supply.name_th if supply else None,
                "category": supply.category if supply else "",
                "unit": supply.unit if supply else "",
                "total_used": 0,
                "by_department": {},
                "by_procedure": {},
            }
        by_supply[sid]["total_used"] += log.quantity_used
        dept = log.department or "unknown"
        by_supply[sid]["by_department"][dept] = by_supply[sid]["by_department"].get(dept, 0) + log.quantity_used
        proc = log.procedure_type or "other"
        by_supply[sid]["by_procedure"][proc] = by_supply[sid]["by_procedure"].get(proc, 0) + log.quantity_used

    return {
        "period": {"from": date_from, "to": date_to},
        "items": list(by_supply.values()),
        "total_items_consumed": sum(d["total_used"] for d in by_supply.values()),
    }


# ── Translation endpoint for frontend i18n ────────────────
@router.get("/translations")
async def get_supply_translations():
    """Return supply UI translations. / คืนค่าคำแปล"""
    from ..schemas.supply_schemas import (
        CATEGORY_OPTIONS, SUBCATEGORY_OPTIONS, DEPARTMENT_OPTIONS,
        UNIT_OPTIONS, PROCEDURE_TYPES, STORAGE_OPTIONS
    )
    return {
        "categories": CATEGORY_OPTIONS,
        "subcategories": SUBCATEGORY_OPTIONS,
        "departments": DEPARTMENT_OPTIONS,
        "units": UNIT_OPTIONS,
        "procedure_types": PROCEDURE_TYPES,
        "storage_options": STORAGE_OPTIONS,
    }
