"""
FCMS Module 4 — Pharmacy / เภสัชกรรม
Drug catalogue, stock management, prescription dispensing, label printing, expiry alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from datetime import datetime, timezone, date, timedelta
from typing import Optional
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/pharmacy", tags=["Pharmacy"])


def _audit(db, user, action, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()), user_id=user.id if user else None,
        action=action, module="pharmacy", resource_type="drug",
        resource_id=resource_id, detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


# ── 1. DRUG CATALOGUE ──────────────────────────────────

@router.get("/drugs")
async def list_drugs(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None, category: Optional[str] = None,
    form: Optional[str] = None, low_stock_only: bool = False,
    current_user: User = Depends(require_module_access("pharmacy")),
    db: Session = Depends(get_db),
):
    return {"drugs": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0,
            "filters": {"categories": ["Hormones","Antibiotics","Analgesics","Antiemetics","Supplements","Anesthetics","Anticoagulants","Other"],
                        "forms": ["Tablet","Capsule","Injection","Cream/Gel","Suppository","Liquid/Syrup","Patch","Nasal Spray"]}}

@router.post("/drugs")
async def create_drug(request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    for f in ["generic_name","form","strength","unit"]:
        if not body.get(f): raise HTTPException(400, f"{f} is required")
    drug_id = str(uuid.uuid4())
    _audit(db, current_user, "CREATE", drug_id, f"Drug: {body.get('generic_name')} ({body.get('brand_name','')})", request)
    db.commit()
    return {"id": drug_id, **body, "current_stock": 0, "created_at": datetime.now(timezone.utc).isoformat()}

@router.get("/drugs/{drug_id}")
async def get_drug(drug_id: str, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    return {"drug": None, "stock_lots": [], "recent_dispensing": [], "avg_daily_consumption": 0, "days_of_stock_remaining": 0}

@router.patch("/drugs/{drug_id}")
async def update_drug(drug_id: str, request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    _audit(db, current_user, "UPDATE", drug_id, f"Updated drug", request)
    db.commit()
    return {"message": "Drug updated", "id": drug_id}


# ── 2. STOCK MANAGEMENT ────────────────────────────────

@router.post("/stock/receive")
async def receive_stock(request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    for f in ["drug_id","quantity","lot_number","expiry_date"]:
        if not body.get(f): raise HTTPException(400, f"{f} is required")
    receipt_id = str(uuid.uuid4())
    _audit(db, current_user, "CREATE", receipt_id, f"Stock in: {body['quantity']} units, lot {body['lot_number']}, exp {body['expiry_date']}", request)
    db.commit()
    return {"id": receipt_id, **body, "received_by": current_user.id, "received_at": datetime.now(timezone.utc).isoformat()}

@router.post("/stock/adjust")
async def adjust_stock(request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    adj_id = str(uuid.uuid4())
    _audit(db, current_user, "UPDATE", adj_id, f"Adjustment: {body.get('quantity')} ({body.get('adjustment_type')}): {body.get('reason')}", request)
    db.commit()
    return {"id": adj_id, **body, "adjusted_by": current_user.id, "adjusted_at": datetime.now(timezone.utc).isoformat()}

@router.get("/stock/levels")
async def stock_levels(low_stock_only: bool = False, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    return {"drugs": [], "total_items": 0, "low_stock_count": 0, "out_of_stock_count": 0}

@router.get("/expiry/alerts")
async def expiry_alerts(days_ahead: int = Query(90, ge=1, le=365), current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    return {"expiring_30d": [], "expiring_60d": [], "expiring_90d": [], "already_expired": [], "total_value_at_risk": 0}


# ── 3. PRESCRIPTIONS & DISPENSING ───────────────────────

@router.get("/prescriptions")
async def list_prescriptions(
    status: Optional[str] = None, patient_id: Optional[str] = None,
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db),
):
    return {"prescriptions": [], "total": 0, "page": page, "per_page": per_page,
            "counts": {"pending": 0, "verified": 0, "dispensed": 0, "cancelled": 0}}

@router.post("/prescriptions/{rx_id}/verify")
async def verify_prescription(rx_id: str, request: Request, current_user: User = Depends(require_roles(["pharmacist","admin"])), db: Session = Depends(get_db)):
    body = await request.json()
    _audit(db, current_user, "UPDATE", rx_id, f"Rx verified. Notes: {body.get('notes','')}", request)
    db.commit()
    return {"rx_id": rx_id, "status": "verified", "verified_by": f"{current_user.first_name_en} {current_user.last_name_en}", "verified_at": datetime.now(timezone.utc).isoformat()}

@router.post("/prescriptions/{rx_id}/dispense")
async def dispense_prescription(rx_id: str, request: Request, current_user: User = Depends(require_roles(["pharmacist","pharmacy_staff","admin"])), db: Session = Depends(get_db)):
    body = await request.json()
    dispense_id = str(uuid.uuid4())
    _audit(db, current_user, "CREATE", dispense_id, f"Dispensed Rx {rx_id}: {len(body.get('items',[]))} items", request)
    db.commit()
    return {"dispense_id": dispense_id, "rx_id": rx_id, "status": "dispensed", "dispensed_by": f"{current_user.first_name_en} {current_user.last_name_en}", "dispensed_at": datetime.now(timezone.utc).isoformat(), "items": body.get("items", []), "label_ready": True}


# ── 4. LABEL PRINTING ──────────────────────────────────

@router.post("/labels/generate")
async def generate_label(request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    return {"id": str(uuid.uuid4()), "clinic_name_en": "Life by Dr. Pat", "clinic_name_th": "คลินิก ไลฟ์ บาย ดร.แพท", "clinic_phone": "02-XXX-XXXX", **body,
            "dispensed_date": datetime.now(timezone.utc).strftime("%d/%m/%Y"), "barcode_data": f"RX-{body.get('patient_hn','')}-{datetime.now().strftime('%Y%m%d%H%M')}"}

@router.post("/labels/batch")
async def generate_batch_labels(request: Request, current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    body = await request.json()
    return {"rx_id": body.get("rx_id"), "labels": [], "total_labels": 0}


# ── 5. DASHBOARD ────────────────────────────────────────

@router.get("/dashboard")
async def pharmacy_dashboard(current_user: User = Depends(require_module_access("pharmacy")), db: Session = Depends(get_db)):
    return {"pending_prescriptions": 0, "dispensed_today": 0, "low_stock_items": 0, "expiring_30d": 0, "total_drugs": 0, "total_stock_value": 0, "today": date.today().isoformat()}

@router.get("/reports/consumption")
async def consumption_report(drug_id: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None,
    current_user: User = Depends(require_roles(["pharmacist","admin","it_admin"])), db: Session = Depends(get_db)):
    return {"period": {"from": date_from, "to": date_to}, "items": [], "total_cost": 0, "total_items_dispensed": 0}
