"""
FCMS Module 2 - Lab Management API Routes
All endpoints for General Lab, Embryology, Andrology + Imports
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from io import BytesIO
import uuid
import pandas as pd

from ..schemas.lab_schemas import (
    LabOrderCreate, LabOrderResponse,
    LabResultCreate, LabResultResponse,
    SpecimenCreate, SpecimenResponse,
    TreatmentCycleCreate, TreatmentCycleResponse,
    OocyteRetrievalCreate, OocyteRetrievalResponse,
    EmbryoAssessmentCreate, EmbryoAssessmentResponse,
    EmbryoCryoCreate, EmbryoWarmingCreate, EmbryoTransferCreate,
    SemenAnalysisCreate, SemenAnalysisResponse,
    ImportResult
)
from ..services.lab_service import LabService
from ..services.import_service import ImportService
# These come from Module 1 core
from ..core.database import get_db
from ..core.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/v1/lab", tags=["Lab Management"])


# ═══════════════════════════════════════════════════════════
# GENERAL LAB
# ═══════════════════════════════════════════════════════════

@router.post("/orders", response_model=LabOrderResponse, status_code=201)
async def create_lab_order(
    order: LabOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "nurse", "lab_technician"]))
):
    return await LabService(db).create_order(order, current_user.id)


@router.get("/orders", response_model=List[LabOrderResponse])
async def list_lab_orders(
    patient_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    lab_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "nurse", "lab_technician", "embryologist"]))
):
    return await LabService(db).list_orders(patient_id, status, lab_type)


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
async def get_lab_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    order = await LabService(db).get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: uuid.UUID,
    new_status: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["lab_technician", "embryologist"]))
):
    return await LabService(db).update_order_status(order_id, new_status, current_user.id)


@router.post("/specimens", response_model=SpecimenResponse, status_code=201)
async def register_specimen(
    specimen: SpecimenCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["lab_technician", "nurse"]))
):
    return await LabService(db).register_specimen(specimen, current_user.id)


@router.post("/results", response_model=LabResultResponse, status_code=201)
async def enter_result(
    result: LabResultCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["lab_technician"]))
):
    return await LabService(db).enter_result(result, current_user.id)


@router.patch("/results/{result_id}/verify")
async def verify_result(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "lab_supervisor"]))
):
    return await LabService(db).verify_result(result_id, current_user.id)


@router.get("/patients/{patient_id}/results")
async def get_patient_lab_history(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await LabService(db).get_patient_results(patient_id)


# ═══════════════════════════════════════════════════════════
# EMBRYOLOGY
# ═══════════════════════════════════════════════════════════

@router.post("/cycles", response_model=TreatmentCycleResponse, status_code=201)
async def create_cycle(
    cycle: TreatmentCycleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "embryologist"]))
):
    return await LabService(db).create_cycle(cycle)


@router.get("/cycles/{cycle_id}")
async def get_cycle(
    cycle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cycle = await LabService(db).get_cycle(cycle_id)
    if not cycle:
        raise HTTPException(404, "Cycle not found")
    return cycle


@router.get("/patients/{patient_id}/cycles")
async def get_patient_cycles(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from ..models.lab_models import TreatmentCycle
    from sqlalchemy import desc
    return db.query(TreatmentCycle).filter(
        TreatmentCycle.patient_id == str(patient_id)
    ).order_by(desc(TreatmentCycle.start_date)).all()


@router.post("/retrievals", response_model=OocyteRetrievalResponse, status_code=201)
async def create_retrieval(
    data: OocyteRetrievalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).create_retrieval(data)


@router.get("/retrievals/{retrieval_id}")
async def get_retrieval(
    retrieval_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    r = await LabService(db).get_retrieval(retrieval_id)
    if not r:
        raise HTTPException(404, "Retrieval not found")
    return r


@router.post("/fertilization")
async def record_fertilization(
    oocyte_id: uuid.UUID,
    patient_id: uuid.UUID,
    fert_status: str = Query(..., alias="status"),
    pronuclei_count: Optional[int] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).record_fertilization(
        str(oocyte_id), str(patient_id), fert_status,
        current_user.id, pronuclei_count, notes
    )


@router.post("/embryos/{embryo_id}/assessments", response_model=EmbryoAssessmentResponse, status_code=201)
async def add_assessment(
    embryo_id: uuid.UUID,
    data: EmbryoAssessmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).add_assessment(embryo_id, data, current_user.id)


@router.get("/embryos/{embryo_id}/assessments")
async def get_assessments(
    embryo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await LabService(db).get_assessments(embryo_id)


@router.post("/embryos/{embryo_id}/freeze", status_code=201)
async def freeze_embryo(
    embryo_id: uuid.UUID,
    data: EmbryoCryoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).freeze_embryo(embryo_id, data, current_user.id)


@router.post("/embryos/{embryo_id}/warm", status_code=201)
async def warm_embryo(
    embryo_id: uuid.UUID,
    data: EmbryoWarmingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).warm_embryo(embryo_id, data, current_user.id)


@router.post("/embryos/{embryo_id}/transfer", status_code=201)
async def transfer_embryo(
    embryo_id: uuid.UUID,
    data: EmbryoTransferCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist", "physician"]))
):
    return await LabService(db).record_transfer(embryo_id, data)


@router.get("/patients/{patient_id}/embryos")
async def get_patient_embryos(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await LabService(db).get_patient_embryos(patient_id)


# ═══════════════════════════════════════════════════════════
# ANDROLOGY
# ═══════════════════════════════════════════════════════════

@router.post("/semen/analyses", response_model=SemenAnalysisResponse, status_code=201)
async def create_semen_analysis(
    data: SemenAnalysisCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["lab_technician", "embryologist"]))
):
    return await LabService(db).create_semen_analysis(data, current_user.id)


@router.get("/semen/patients/{patient_id}")
async def get_semen_analyses(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await LabService(db).get_semen_analyses(patient_id)


@router.post("/sperm/preparation", status_code=201)
async def create_sperm_prep(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["embryologist"]))
):
    return await LabService(db).create_sperm_prep(data, current_user.id)


# ═══════════════════════════════════════════════════════════
# IMPORT — Excel / CSV
# ═══════════════════════════════════════════════════════════

@router.post("/import/inventory", response_model=ImportResult)
async def import_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "pharmacy_staff", "supply_manager"]))
):
    """Import inventory from Excel (.xlsx) or CSV (.csv)"""
    contents = await file.read()
    return await ImportService(db).import_inventory(contents, file.filename, current_user.id)


@router.post("/import/patients", response_model=ImportResult)
async def import_patient_history(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "physician", "nurse"]))
):
    """Import patient/client history from Excel (.xlsx) or CSV (.csv)"""
    contents = await file.read()
    return await ImportService(db).import_patient_history(contents, file.filename, current_user.id)


@router.get("/import/template/{template_type}")
async def download_import_template(
    template_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Download blank import template (inventory or patient)"""
    svc = ImportService(db)

    if template_type == "inventory":
        df = svc.generate_inventory_template()
        filename = "FCMS_Inventory_Import_Template.xlsx"
    elif template_type == "patient":
        df = svc.generate_patient_template()
        filename = "FCMS_Patient_Import_Template.xlsx"
    else:
        raise HTTPException(400, "template_type must be 'inventory' or 'patient'")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ═══════════════════════════════════════════════════════════
# LAB TUBE LABELS — 40×20mm / ฉลากหลอดเลือด 40×20 มม.
# ═══════════════════════════════════════════════════════════

@router.post("/labels/tube")
async def generate_tube_label(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("lab"))
):
    """
    Generate lab tube label data (40×20mm). / สร้างข้อมูลฉลากหลอดตัวอย่าง (40×20 มม.)
    Compact format for blood/urine collection tubes.
    """
    body = await request.json()
    from datetime import datetime
    now = datetime.now()

    label = {
        "id": str(uuid.uuid4()),
        "label_format": "40x20mm",
        "patient_hn": body.get("patient_hn", ""),
        "patient_name_en": body.get("patient_name_en", ""),
        "patient_name_th": body.get("patient_name_th", ""),
        "sample_barcode": body.get("barcode", ""),
        "test_code": body.get("test_code", ""),
        "test_name_en": body.get("test_name_en", ""),
        "test_name_th": body.get("test_name_th", ""),
        "container": body.get("container", ""),  # EDTA, Plain, SST, etc.
        "collected_date": body.get("collected_date", now.strftime("%d/%m/%Y")),
        "collected_time": body.get("collected_time", now.strftime("%H:%M")),
        "collected_date_th": now.strftime("%d/%m/") + str(now.year + 543),
    }
    return label


@router.post("/labels/tube/batch")
async def generate_tube_labels_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("lab"))
):
    """
    Generate all tube labels for a lab order. / สร้างฉลากหลอดทั้งหมดของใบสั่ง lab
    One label per tube/container.
    """
    body = await request.json()
    from datetime import datetime
    now = datetime.now()
    labels = []

    for idx, tube in enumerate(body.get("tubes", [])):
        labels.append({
            "id": str(uuid.uuid4()),
            "label_format": "40x20mm",
            "patient_hn": body.get("patient_hn", ""),
            "patient_name_en": body.get("patient_name_en", ""),
            "patient_name_th": body.get("patient_name_th", ""),
            "sample_barcode": tube.get("barcode", ""),
            "test_code": tube.get("test_code", ""),
            "test_name_en": tube.get("test_name_en", ""),
            "test_name_th": tube.get("test_name_th", ""),
            "container": tube.get("container", ""),
            "collected_date": now.strftime("%d/%m/%Y"),
            "collected_time": now.strftime("%H:%M"),
            "collected_date_th": now.strftime("%d/%m/") + str(now.year + 543),
        })

    return {"order_id": body.get("order_id"), "labels": labels, "total_labels": len(labels)}

