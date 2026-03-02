"""
FCMS Module 2 - Lab Management Schemas (Pydantic)
Request/Response models for all lab endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid


# ─────────────────────────────────────────────────────────────
# GENERAL LAB SCHEMAS
# ─────────────────────────────────────────────────────────────

class LabOrderCreate(BaseModel):
    patient_id: uuid.UUID
    visit_id: Optional[uuid.UUID]
    lab_type: str
    priority: str = "routine"
    clinical_notes: Optional[str]
    diagnosis_code: Optional[str]
    test_panel_ids: List[uuid.UUID]

class LabOrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    patient_id: uuid.UUID
    lab_type: str
    status: str
    priority: str
    ordered_at: datetime
    items: List[dict] = []

    class Config:
        from_attributes = True


class LabResultCreate(BaseModel):
    order_item_id: uuid.UUID
    numeric_value: Optional[Decimal]
    text_value: Optional[str]
    unit: Optional[str]
    flag: Optional[str]
    normal_range: Optional[str]
    method: Optional[str]
    instrument: Optional[str]
    comment: Optional[str]

class LabResultResponse(BaseModel):
    id: uuid.UUID
    order_item_id: uuid.UUID
    numeric_value: Optional[Decimal]
    text_value: Optional[str]
    unit: Optional[str]
    flag: Optional[str]
    normal_range: Optional[str]
    resulted_at: datetime
    verified_at: Optional[datetime]

    class Config:
        from_attributes = True


class SpecimenCreate(BaseModel):
    order_id: uuid.UUID
    specimen_type: str
    container: Optional[str]
    volume_ml: Optional[Decimal]
    storage_location: Optional[str]
    notes: Optional[str]

class SpecimenResponse(BaseModel):
    id: uuid.UUID
    barcode: str
    specimen_type: str
    container: Optional[str]
    collected_at: Optional[datetime]
    is_rejected: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# EMBRYOLOGY SCHEMAS
# ─────────────────────────────────────────────────────────────

class TreatmentCycleCreate(BaseModel):
    patient_id: uuid.UUID
    partner_id: Optional[uuid.UUID]
    cycle_type: str   # IVF | ICSI | IUI | FET
    start_date: date
    physician_id: uuid.UUID
    embryologist_id: uuid.UUID
    notes: Optional[str]

class TreatmentCycleResponse(BaseModel):
    id: uuid.UUID
    cycle_number: str
    patient_id: uuid.UUID
    cycle_type: str
    start_date: date
    outcome: Optional[str]

    class Config:
        from_attributes = True


class OocyteRetrievalCreate(BaseModel):
    patient_id: uuid.UUID
    cycle_id: Optional[uuid.UUID]
    visit_id: Optional[uuid.UUID]
    procedure_date: date
    physician_id: uuid.UUID
    embryologist_id: uuid.UUID
    anesthesia_type: Optional[str]
    total_follicles_aspirated: Optional[int]
    total_oocytes_retrieved: Optional[int]
    mii_count: Optional[int]
    mi_count: Optional[int]
    gv_count: Optional[int]
    degenerated_count: Optional[int]
    follicular_fluid_ml: Optional[Decimal]
    complications: Optional[str]
    notes: Optional[str]

class OocyteRetrievalResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    procedure_date: date
    total_oocytes_retrieved: Optional[int]
    mii_count: Optional[int]
    oocytes: List[dict] = []

    class Config:
        from_attributes = True


class EmbryoAssessmentCreate(BaseModel):
    embryo_id: uuid.UUID
    assessment_day: int
    embryologist_id: uuid.UUID
    # Cleavage
    cell_count: Optional[int]
    fragmentation_pct: Optional[Decimal]
    symmetry: Optional[str]
    multinucleation: Optional[bool]
    # Blastocyst
    expansion: Optional[str]
    icm_grade: Optional[str]
    te_grade: Optional[str]
    # Overall
    overall_grade: Optional[str]
    is_suitable_transfer: Optional[bool]
    is_suitable_freeze: Optional[bool]
    notes: Optional[str]

class EmbryoAssessmentResponse(BaseModel):
    id: uuid.UUID
    embryo_id: uuid.UUID
    assessment_day: int
    overall_grade: Optional[str]
    is_suitable_transfer: Optional[bool]
    is_suitable_freeze: Optional[bool]

    class Config:
        from_attributes = True


class EmbryoCryoCreate(BaseModel):
    embryo_id: uuid.UUID
    method: str    # vitrification | slow-freeze
    device: str
    device_label: str
    tank_id: str
    canister: str
    goblet: str
    position: str
    cryo_medium: Optional[str]
    notes: Optional[str]

class EmbryoWarmingCreate(BaseModel):
    embryo_id: uuid.UUID
    warming_date: datetime
    status: str
    blastomeres_intact_pct: Optional[Decimal]
    post_warm_grade: Optional[str]
    warming_medium: Optional[str]
    notes: Optional[str]

class EmbryoTransferCreate(BaseModel):
    embryo_id: uuid.UUID
    patient_id: uuid.UUID
    cycle_id: Optional[uuid.UUID]
    transfer_date: datetime
    physician_id: uuid.UUID
    embryologist_id: uuid.UUID
    transfer_type: str   # fresh | frozen
    endometrial_thickness: Optional[Decimal]
    catheter_type: Optional[str]
    difficulty: Optional[str]
    ultrasound_guided: bool = True
    embryo_position_mm: Optional[Decimal]
    notes: Optional[str]


# ─────────────────────────────────────────────────────────────
# ANDROLOGY SCHEMAS
# ─────────────────────────────────────────────────────────────

class SemenAnalysisCreate(BaseModel):
    patient_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    collected_at: Optional[datetime]
    abstinence_days: Optional[int]
    collection_method: Optional[str]
    collection_location: Optional[str]
    # Macroscopic
    volume_ml: Optional[Decimal]
    appearance: Optional[str]
    color: Optional[str]
    viscosity: Optional[str]
    liquefaction_time_min: Optional[int]
    ph: Optional[Decimal]
    # Microscopic
    concentration_M_per_ml: Optional[Decimal]
    total_count_M: Optional[Decimal]
    total_motility_pct: Optional[Decimal]
    progressive_motility_pct: Optional[Decimal]
    non_progressive_pct: Optional[Decimal]
    immotile_pct: Optional[Decimal]
    normal_morphology_pct: Optional[Decimal]
    vitality_pct: Optional[Decimal]
    vitality_method: Optional[str]
    wbc_per_ml: Optional[Decimal]
    agglutination: Optional[str]
    dfi_pct: Optional[Decimal]
    dfi_method: Optional[str]
    diagnosis: Optional[str]
    recommendation: Optional[str]
    notes: Optional[str]

class SemenAnalysisResponse(BaseModel):
    id: uuid.UUID
    analysis_number: str
    patient_id: uuid.UUID
    collected_at: Optional[datetime]
    volume_ml: Optional[Decimal]
    concentration_M_per_ml: Optional[Decimal]
    total_motility_pct: Optional[Decimal]
    progressive_motility_pct: Optional[Decimal]
    normal_morphology_pct: Optional[Decimal]
    diagnosis: Optional[str]
    who_reference_met: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# IMPORT SCHEMAS (Excel / CSV)
# ─────────────────────────────────────────────────────────────

class ImportResult(BaseModel):
    total_rows: int
    imported: int
    skipped: int
    errors: List[dict] = []
    warnings: List[str] = []

class InventoryImportRow(BaseModel):
    item_code: str
    name_en: str
    name_th: Optional[str]
    category: str
    unit: str
    quantity: float
    reorder_level: float
    unit_price: Optional[Decimal]
    supplier: Optional[str]
    expiry_date: Optional[str]
    storage_location: Optional[str]

class PatientHistoryImportRow(BaseModel):
    hn_number: Optional[str]
    first_name_en: str
    last_name_en: str
    first_name_th: Optional[str]
    last_name_th: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    id_number: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    blood_type: Optional[str]
    allergies: Optional[str]
    medical_history: Optional[str]
    diagnosis: Optional[str]
    treatment_notes: Optional[str]
