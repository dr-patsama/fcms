"""
FCMS Module 4 — Pharmacy Pydantic Schemas / สคีมาเภสัชกรรม
Request/response validation for drug catalogue, stock, prescriptions, dispensing, labels.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ── Drug Catalogue ────────────────────────────────────────

class DrugCreate(BaseModel):
    generic_name: str = Field(..., min_length=1, max_length=200)
    generic_name_th: Optional[str] = None
    brand_name: Optional[str] = None
    brand_name_th: Optional[str] = None
    category: str = "other"
    form: str = Field(..., min_length=1)
    form_th: Optional[str] = None
    strength: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    unit_th: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    reorder_level: int = 50
    reorder_quantity: int = 200
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    storage_condition: Optional[str] = None
    storage_condition_th: Optional[str] = None
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None
    warnings_en: Optional[str] = None
    warnings_th: Optional[str] = None
    requires_refrigeration: bool = False
    is_controlled: bool = False
    # Label defaults
    label_dose_en: Optional[str] = None
    label_dose_th: Optional[str] = None
    label_route_en: Optional[str] = None
    label_route_th: Optional[str] = None
    label_frequency_en: Optional[str] = None
    label_frequency_th: Optional[str] = None
    label_warnings_en: Optional[str] = None
    label_warnings_th: Optional[str] = None


class DrugUpdate(BaseModel):
    generic_name: Optional[str] = None
    generic_name_th: Optional[str] = None
    brand_name: Optional[str] = None
    brand_name_th: Optional[str] = None
    category: Optional[str] = None
    form: Optional[str] = None
    form_th: Optional[str] = None
    strength: Optional[str] = None
    unit: Optional[str] = None
    unit_th: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    reorder_level: Optional[int] = None
    reorder_quantity: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    storage_condition: Optional[str] = None
    storage_condition_th: Optional[str] = None
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None
    warnings_en: Optional[str] = None
    warnings_th: Optional[str] = None
    requires_refrigeration: Optional[bool] = None
    is_controlled: Optional[bool] = None
    is_active: Optional[bool] = None
    label_dose_en: Optional[str] = None
    label_dose_th: Optional[str] = None
    label_route_en: Optional[str] = None
    label_route_th: Optional[str] = None
    label_frequency_en: Optional[str] = None
    label_frequency_th: Optional[str] = None
    label_warnings_en: Optional[str] = None
    label_warnings_th: Optional[str] = None


class DrugOut(BaseModel):
    id: str
    generic_name: str
    generic_name_th: Optional[str] = None
    brand_name: Optional[str] = None
    brand_name_th: Optional[str] = None
    category: Optional[str] = None
    form: str
    form_th: Optional[str] = None
    strength: str
    unit: str
    unit_th: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    reorder_level: int = 50
    reorder_quantity: int = 200
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    storage_condition: Optional[str] = None
    storage_condition_th: Optional[str] = None
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None
    requires_refrigeration: bool = False
    is_controlled: bool = False
    is_active: bool = True
    current_stock: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Stock ─────────────────────────────────────────────────

class StockReceiveRequest(BaseModel):
    drug_id: str
    quantity: int = Field(..., gt=0)
    lot_number: str = Field(..., min_length=1)
    expiry_date: date
    unit_cost: Optional[Decimal] = None
    supplier: Optional[str] = None
    po_number: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None


class StockAdjustRequest(BaseModel):
    drug_id: str
    lot_id: Optional[str] = None
    adjustment_type: str  # add | remove | expired_write_off
    quantity: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1)


class StockLotOut(BaseModel):
    id: str
    drug_id: str
    lot_number: str
    expiry_date: date
    initial_quantity: int
    current_quantity: int
    unit_cost: Optional[Decimal] = None
    supplier: Optional[str] = None
    received_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ── Prescriptions ─────────────────────────────────────────

class PrescriptionItemCreate(BaseModel):
    drug_id: str
    quantity: int = Field(..., gt=0)
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    frequency_th: Optional[str] = None
    route: Optional[str] = None
    route_th: Optional[str] = None
    duration_days: Optional[int] = None
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None
    warnings: Optional[list] = None


class PrescriptionCreate(BaseModel):
    patient_id: str
    visit_id: Optional[str] = None
    priority: str = "normal"
    notes: Optional[str] = None
    notes_th: Optional[str] = None
    items: List[PrescriptionItemCreate]


class PrescriptionVerifyRequest(BaseModel):
    notes: Optional[str] = None
    items_approved: Optional[List[str]] = None  # specific item IDs, or all


# ── Prescription Generator / เครื่องมือสร้างใบสั่งยา ─────────

class RxGenItem(BaseModel):
    """Structured medication line — quantity is computed server-side
    (dose × times/day × days, rounded UP to the drug's pack_size)."""
    drug_id: str
    dose_per_time: float = Field(..., gt=0)      # e.g. 2 tablets per dose
    times_per_day: int = Field(..., gt=0)        # e.g. 2 (bid)
    duration_days: int = Field(..., gt=0)        # e.g. 14
    route: Optional[str] = None                  # oral | vaginal | sublingual | subcutaneous | intramuscular | topical
    instruction_en: Optional[str] = None         # e.g. "after meals"
    instruction_th: Optional[str] = None         # e.g. "หลังอาหาร"
    sig_en_override: Optional[str] = None        # free-text override of the auto sig
    sig_th_override: Optional[str] = None
    quantity_override: Optional[int] = Field(None, gt=0)  # manual final quantity


class RxGenerateRequest(BaseModel):
    patient_id: str
    visit_id: Optional[str] = None
    diagnosis_en: Optional[str] = None
    diagnosis_th: Optional[str] = None
    notes: Optional[str] = None                  # printed note, e.g. continue until 12 weeks
    notes_th: Optional[str] = None
    priority: str = "normal"
    items: List[RxGenItem]


class DispenseItemRequest(BaseModel):
    drug_id: str
    lot_id: Optional[str] = None  # auto-FIFO if not specified
    quantity: int = Field(..., gt=0)
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None


class DispenseRequest(BaseModel):
    items: List[DispenseItemRequest]
    counseling_notes: Optional[str] = None
    counseling_notes_th: Optional[str] = None
    print_labels: bool = True


# ── Label Generation ──────────────────────────────────────

class LabelRequest(BaseModel):
    patient_hn: str
    patient_name_en: str
    patient_name_th: Optional[str] = None
    drug_name_en: str
    drug_name_th: Optional[str] = None
    strength: str
    form_en: str
    form_th: Optional[str] = None
    quantity: int
    unit_en: str
    unit_th: Optional[str] = None
    dosage_en: str
    dosage_th: Optional[str] = None
    frequency_en: str
    frequency_th: Optional[str] = None
    route_en: Optional[str] = None
    route_th: Optional[str] = None
    instructions_en: Optional[str] = None
    instructions_th: Optional[str] = None
    warnings_en: Optional[List[str]] = None
    warnings_th: Optional[List[str]] = None
    prescriber_name: Optional[str] = None
    dispense_date: Optional[str] = None


class BatchLabelRequest(BaseModel):
    rx_id: str
    patient_hn: str
    patient_name_en: str
    patient_name_th: Optional[str] = None
    items: List[LabelRequest]


# ── Common Frequency/Route Thai translations ──────────────
# Used as defaults in frontend dropdowns

FREQUENCY_OPTIONS = [
    {"en": "Once daily",            "th": "วันละ 1 ครั้ง"},
    {"en": "Twice daily",           "th": "วันละ 2 ครั้ง"},
    {"en": "Three times daily",     "th": "วันละ 3 ครั้ง"},
    {"en": "Four times daily",      "th": "วันละ 4 ครั้ง"},
    {"en": "Every 4 hours",         "th": "ทุก 4 ชั่วโมง"},
    {"en": "Every 6 hours",         "th": "ทุก 6 ชั่วโมง"},
    {"en": "Every 8 hours",         "th": "ทุก 8 ชั่วโมง"},
    {"en": "Every 12 hours",        "th": "ทุก 12 ชั่วโมง"},
    {"en": "Every other day",       "th": "วันเว้นวัน"},
    {"en": "Once weekly",           "th": "สัปดาห์ละ 1 ครั้ง"},
    {"en": "Before meals",          "th": "ก่อนอาหาร"},
    {"en": "After meals",           "th": "หลังอาหาร"},
    {"en": "Before bedtime",        "th": "ก่อนนอน"},
    {"en": "As needed (PRN)",       "th": "เมื่อจำเป็น"},
    {"en": "As directed",           "th": "ตามแพทย์สั่ง"},
]

ROUTE_OPTIONS = [
    {"en": "Oral",                  "th": "รับประทาน"},
    {"en": "Sublingual",            "th": "อมใต้ลิ้น"},
    {"en": "Subcutaneous injection","th": "ฉีดใต้ผิวหนัง"},
    {"en": "Intramuscular injection","th": "ฉีดเข้ากล้ามเนื้อ"},
    {"en": "Intravenous",           "th": "ฉีดเข้าหลอดเลือดดำ"},
    {"en": "Vaginal",               "th": "สอดช่องคลอด"},
    {"en": "Rectal",                "th": "สอดทวารหนัก"},
    {"en": "Topical",               "th": "ทาภายนอก"},
    {"en": "Nasal",                 "th": "พ่นจมูก"},
    {"en": "Transdermal (patch)",   "th": "แปะผิวหนัง"},
    {"en": "Ophthalmic (eye)",      "th": "หยอดตา"},
]

FORM_OPTIONS = [
    {"en": "Tablet",       "th": "เม็ด"},
    {"en": "Capsule",      "th": "แคปซูล"},
    {"en": "Injection",    "th": "ยาฉีด"},
    {"en": "Cream/Gel",    "th": "ครีม/เจล"},
    {"en": "Suppository",  "th": "ยาเหน็บ"},
    {"en": "Liquid/Syrup", "th": "ยาน้ำ/ไซรัป"},
    {"en": "Patch",        "th": "แผ่นแปะ"},
    {"en": "Nasal Spray",  "th": "สเปรย์พ่นจมูก"},
    {"en": "Vaginal Tablet","th": "ยาเหน็บช่องคลอด"},
    {"en": "Eye Drops",    "th": "ยาหยอดตา"},
    {"en": "Powder",       "th": "ยาผง"},
]

CATEGORY_OPTIONS = [
    {"en": "Hormonal",       "th": "ฮอร์โมน"},
    {"en": "IVF Protocol",   "th": "โปรโตคอล IVF"},
    {"en": "Antibiotic",     "th": "ยาปฏิชีวนะ"},
    {"en": "Analgesic",      "th": "ยาแก้ปวด"},
    {"en": "Vitamin",        "th": "วิตามิน"},
    {"en": "Anesthetic",     "th": "ยาชา"},
    {"en": "Anticoagulant",  "th": "ยาต้านการแข็งตัวของเลือด"},
    {"en": "Antiemetic",     "th": "ยาแก้อาเจียน"},
    {"en": "Antifungal",     "th": "ยาต้านเชื้อรา"},
    {"en": "Supplement",     "th": "อาหารเสริม"},
    {"en": "Other",          "th": "อื่นๆ"},
]

WARNING_PRESETS = [
    {"en": "Avoid alcohol",                      "th": "หลีกเลี่ยงแอลกอฮอล์"},
    {"en": "Take with food",                     "th": "รับประทานพร้อมอาหาร"},
    {"en": "May cause drowsiness",               "th": "อาจทำให้ง่วง"},
    {"en": "Do not drive after taking",           "th": "ห้ามขับรถหลังรับประทาน"},
    {"en": "Store in refrigerator (2-8°C)",      "th": "เก็บในตู้เย็น (2-8°C)"},
    {"en": "Keep away from children",            "th": "เก็บให้พ้นมือเด็ก"},
    {"en": "For external use only",              "th": "ใช้ภายนอกเท่านั้น"},
    {"en": "Complete the full course",           "th": "รับประทานให้ครบจำนวน"},
    {"en": "Shake well before use",              "th": "เขย่าขวดก่อนใช้"},
    {"en": "Take on empty stomach",             "th": "รับประทานขณะท้องว่าง"},
    {"en": "Avoid sunlight exposure",            "th": "หลีกเลี่ยงแสงแดด"},
    {"en": "Possible injection site reaction",   "th": "อาจมีอาการบวมแดงบริเวณที่ฉีด"},
]
