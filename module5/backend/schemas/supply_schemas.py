"""
FCMS Module 5 — Medical Supply Pydantic Schemas / สคีมาเวชภัณฑ์
Request/response validation for supply catalogue, stock, requisitions, usage.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ── Supplier ──────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    name_th: Optional[str] = None
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    address_th: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    name_th: Optional[str] = None
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    address_th: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierOut(BaseModel):
    id: str
    name: str
    name_th: Optional[str] = None
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Medical Supply ────────────────────────────────────────

class SupplyCreate(BaseModel):
    name_en: str = Field(..., min_length=1, max_length=200)
    name_th: Optional[str] = None
    description_en: Optional[str] = None
    description_th: Optional[str] = None
    category: str = Field(..., min_length=1)
    subcategory: Optional[str] = None
    sku: Optional[str] = None
    catalog_number: Optional[str] = None
    unit: str = Field(..., min_length=1)
    unit_th: Optional[str] = None
    pack_size: int = 1
    manufacturer: Optional[str] = None
    default_supplier_id: Optional[str] = None
    reorder_level: int = 10
    reorder_quantity: int = 50
    unit_cost: Optional[Decimal] = None
    storage_condition: Optional[str] = None
    storage_condition_th: Optional[str] = None
    requires_refrigeration: bool = False
    requires_sterile: bool = False
    department: Optional[str] = None


class SupplyUpdate(BaseModel):
    name_en: Optional[str] = None
    name_th: Optional[str] = None
    description_en: Optional[str] = None
    description_th: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sku: Optional[str] = None
    catalog_number: Optional[str] = None
    unit: Optional[str] = None
    unit_th: Optional[str] = None
    pack_size: Optional[int] = None
    manufacturer: Optional[str] = None
    default_supplier_id: Optional[str] = None
    reorder_level: Optional[int] = None
    reorder_quantity: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    storage_condition: Optional[str] = None
    storage_condition_th: Optional[str] = None
    requires_refrigeration: Optional[bool] = None
    requires_sterile: Optional[bool] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class SupplyOut(BaseModel):
    id: str
    name_en: str
    name_th: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    sku: Optional[str] = None
    unit: str
    unit_th: Optional[str] = None
    manufacturer: Optional[str] = None
    reorder_level: int = 10
    unit_cost: Optional[Decimal] = None
    requires_refrigeration: bool = False
    requires_sterile: bool = False
    department: Optional[str] = None
    is_active: bool = True
    current_stock: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Stock ─────────────────────────────────────────────────

class StockReceiveRequest(BaseModel):
    supply_id: str
    quantity: int = Field(..., gt=0)
    lot_number: str = Field(..., min_length=1)
    expiry_date: Optional[date] = None
    unit_cost: Optional[Decimal] = None
    supplier_id: Optional[str] = None
    po_number: Optional[str] = None
    invoice_number: Optional[str] = None
    grn_number: Optional[str] = None
    notes: Optional[str] = None


class StockAdjustRequest(BaseModel):
    supply_id: str
    lot_id: Optional[str] = None
    adjustment_type: str  # add | remove | expired_write_off
    quantity: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1)


class StockLotOut(BaseModel):
    id: str
    supply_id: str
    lot_number: str
    expiry_date: Optional[date] = None
    initial_quantity: int
    current_quantity: int
    unit_cost: Optional[Decimal] = None
    supplier_id: Optional[str] = None
    grn_number: Optional[str] = None
    received_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ── Requisitions ──────────────────────────────────────────

class RequisitionItemCreate(BaseModel):
    supply_id: str
    quantity_requested: int = Field(..., gt=0)
    notes: Optional[str] = None


class RequisitionCreate(BaseModel):
    department: str
    priority: str = "normal"
    notes: Optional[str] = None
    notes_th: Optional[str] = None
    items: List[RequisitionItemCreate]


class RequisitionIssueItem(BaseModel):
    item_id: str
    quantity_issued: int = Field(..., ge=0)
    lot_id: Optional[str] = None  # auto-FIFO if not specified


class RequisitionIssueRequest(BaseModel):
    items: List[RequisitionIssueItem]
    notes: Optional[str] = None


# ── Usage Log ─────────────────────────────────────────────

class UsageLogCreate(BaseModel):
    supply_id: str
    lot_id: Optional[str] = None
    quantity_used: int = Field(..., gt=0)
    department: str
    procedure_type: Optional[str] = None
    patient_id: Optional[str] = None
    visit_id: Optional[str] = None
    notes: Optional[str] = None


# ── Bilingual Presets (fertility clinic specific) ─────────

CATEGORY_OPTIONS = [
    {"value": "plasticware",   "en": "Plasticware",            "th": "พลาสติกแวร์"},
    {"value": "lab_media",     "en": "Lab Media",              "th": "มีเดียแล็บ"},
    {"value": "test_kit",      "en": "Test Kit",               "th": "ชุดตรวจ"},
    {"value": "cryostorage",   "en": "Cryostorage",            "th": "วัสดุแช่แข็ง"},
    {"value": "consumable",    "en": "Consumable",             "th": "วัสดุสิ้นเปลือง"},
    {"value": "ppe",           "en": "PPE",                    "th": "อุปกรณ์ป้องกัน"},
    {"value": "cleaning",      "en": "Cleaning/Sterilization", "th": "ทำความสะอาด/ฆ่าเชื้อ"},
    {"value": "general",       "en": "General",                "th": "ทั่วไป"},
]

SUBCATEGORY_OPTIONS = {
    "plasticware": [
        {"value": "culture_dish",    "en": "Culture Dish",       "th": "จานเพาะเลี้ยง"},
        {"value": "petri_dish",      "en": "Petri Dish",         "th": "จานเพาะเชื้อ"},
        {"value": "icsi_dish",       "en": "ICSI Dish",          "th": "จาน ICSI"},
        {"value": "pipette",         "en": "Pipette",            "th": "ปิเปต"},
        {"value": "pipette_tip",     "en": "Pipette Tip",        "th": "ทิปปิเปต"},
        {"value": "test_tube",       "en": "Test Tube",          "th": "หลอดทดลอง"},
        {"value": "centrifuge_tube", "en": "Centrifuge Tube",    "th": "หลอดปั่นเหวี่ยง"},
        {"value": "cryovial",        "en": "Cryovial",           "th": "หลอดแช่แข็ง"},
        {"value": "slide",           "en": "Slide",              "th": "สไลด์"},
        {"value": "cover_slip",      "en": "Cover Slip",         "th": "แผ่นปิดสไลด์"},
        {"value": "specimen_cup",    "en": "Specimen Cup",       "th": "ถ้วยเก็บตัวอย่าง"},
        {"value": "other",           "en": "Other",              "th": "อื่นๆ"},
    ],
    "lab_media": [
        {"value": "culture_media",   "en": "Culture Media",      "th": "มีเดียเพาะเลี้ยง"},
        {"value": "wash_media",      "en": "Wash Media",         "th": "มีเดียล้าง"},
        {"value": "oil_overlay",     "en": "Oil Overlay",        "th": "น้ำมันปิดหยด"},
        {"value": "pvp",             "en": "PVP Solution",       "th": "สารละลาย PVP"},
        {"value": "hyaluronidase",   "en": "Hyaluronidase",      "th": "ไฮยาลูโรนิเดส"},
        {"value": "cryoprotectant",  "en": "Cryoprotectant",     "th": "สารป้องกันการแข็งตัว"},
        {"value": "vitrification",   "en": "Vitrification Media", "th": "มีเดียแช่แข็ง"},
        {"value": "warming_media",   "en": "Warming Media",      "th": "มีเดียละลาย"},
        {"value": "sperm_media",     "en": "Sperm Prep Media",   "th": "มีเดียเตรียมสเปิร์ม"},
        {"value": "other",           "en": "Other",              "th": "อื่นๆ"},
    ],
    "test_kit": [
        {"value": "pregnancy_test",  "en": "Pregnancy Test",     "th": "ชุดตรวจตั้งครรภ์"},
        {"value": "hormone_assay",   "en": "Hormone Assay Kit",  "th": "ชุดตรวจฮอร์โมน"},
        {"value": "blood_test",      "en": "Blood Test Kit",     "th": "ชุดตรวจเลือด"},
        {"value": "urine_test",      "en": "Urine Test Kit",     "th": "ชุดตรวจปัสสาวะ"},
        {"value": "genetic_test",    "en": "Genetic Test Kit",   "th": "ชุดตรวจพันธุกรรม"},
        {"value": "semen_analysis",  "en": "Semen Analysis Kit", "th": "ชุดวิเคราะห์น้ำอสุจิ"},
        {"value": "other",           "en": "Other",              "th": "อื่นๆ"},
    ],
    "cryostorage": [
        {"value": "cryo_straw",      "en": "Cryo Straw",        "th": "หลอดแช่แข็ง"},
        {"value": "goblet",          "en": "Goblet",             "th": "ถ้วยแช่แข็ง"},
        {"value": "cane",            "en": "Cane",               "th": "ก้านแช่แข็ง"},
        {"value": "cryo_sleeve",     "en": "Cryo Sleeve",       "th": "ปลอกแช่แข็ง"},
        {"value": "ln2",             "en": "Liquid Nitrogen",    "th": "ไนโตรเจนเหลว"},
        {"value": "cryo_label",      "en": "Cryo Label",        "th": "ฉลากแช่แข็ง"},
        {"value": "other",           "en": "Other",              "th": "อื่นๆ"},
    ],
    "consumable": [
        {"value": "syringe",         "en": "Syringe",           "th": "กระบอกฉีดยา"},
        {"value": "needle",          "en": "Needle",            "th": "เข็มฉีดยา"},
        {"value": "opu_needle",      "en": "OPU Needle",        "th": "เข็มเจาะไข่"},
        {"value": "catheter",        "en": "Catheter",          "th": "สายสวน"},
        {"value": "et_catheter",     "en": "ET Catheter",       "th": "สายย้ายตัวอ่อน"},
        {"value": "iui_catheter",    "en": "IUI Catheter",      "th": "สายฉีดอสุจิ"},
        {"value": "speculum",        "en": "Speculum",          "th": "คีมถ่างช่องคลอด"},
        {"value": "gloves",          "en": "Gloves",            "th": "ถุงมือ"},
        {"value": "gauze",           "en": "Gauze",             "th": "ผ้าก๊อซ"},
        {"value": "swab",            "en": "Swab",              "th": "สำลี"},
        {"value": "drape",           "en": "Drape",             "th": "ผ้าปูสเตอไรล์"},
        {"value": "other",           "en": "Other",             "th": "อื่นๆ"},
    ],
    "ppe": [
        {"value": "mask",            "en": "Face Mask",         "th": "หน้ากากอนามัย"},
        {"value": "gown",            "en": "Gown",              "th": "ชุดคลุม"},
        {"value": "cap",             "en": "Cap",               "th": "หมวกคลุมผม"},
        {"value": "shoe_cover",      "en": "Shoe Cover",        "th": "ถุงครอบรองเท้า"},
        {"value": "face_shield",     "en": "Face Shield",       "th": "หน้ากากป้องกัน"},
        {"value": "goggles",         "en": "Goggles",           "th": "แว่นป้องกัน"},
        {"value": "other",           "en": "Other",             "th": "อื่นๆ"},
    ],
    "cleaning": [
        {"value": "disinfectant",    "en": "Disinfectant",      "th": "น้ำยาฆ่าเชื้อ"},
        {"value": "alcohol",         "en": "Alcohol",           "th": "แอลกอฮอล์"},
        {"value": "sterilization_pouch", "en": "Sterilization Pouch", "th": "ซองสเตอไรล์"},
        {"value": "indicator_tape",  "en": "Indicator Tape",    "th": "เทปบ่งชี้"},
        {"value": "other",           "en": "Other",             "th": "อื่นๆ"},
    ],
    "general": [
        {"value": "label",           "en": "Label",             "th": "ฉลาก"},
        {"value": "printer_ribbon",  "en": "Printer Ribbon",    "th": "ริบบอนเครื่องพิมพ์"},
        {"value": "paper",           "en": "Paper",             "th": "กระดาษ"},
        {"value": "other",           "en": "Other",             "th": "อื่นๆ"},
    ],
}

DEPARTMENT_OPTIONS = [
    {"value": "embryology_lab",  "en": "Embryology Lab",   "th": "ห้องปฏิบัติการตัวอ่อน"},
    {"value": "andrology_lab",   "en": "Andrology Lab",    "th": "ห้องปฏิบัติการอสุจิ"},
    {"value": "general_lab",     "en": "General Lab",      "th": "ห้องปฏิบัติการทั่วไป"},
    {"value": "clinic",          "en": "Clinic Room",      "th": "ห้องตรวจ"},
    {"value": "operating_room",  "en": "Operating Room",   "th": "ห้องผ่าตัด"},
    {"value": "all",             "en": "All Departments",  "th": "ทุกแผนก"},
]

UNIT_OPTIONS = [
    {"value": "piece",   "en": "Piece",   "th": "ชิ้น"},
    {"value": "box",     "en": "Box",     "th": "กล่อง"},
    {"value": "pack",    "en": "Pack",    "th": "แพ็ค"},
    {"value": "bottle",  "en": "Bottle",  "th": "ขวด"},
    {"value": "vial",    "en": "Vial",    "th": "ไวอัล"},
    {"value": "tube",    "en": "Tube",    "th": "หลอด"},
    {"value": "liter",   "en": "Liter",   "th": "ลิตร"},
    {"value": "ml",      "en": "mL",      "th": "มล."},
    {"value": "roll",    "en": "Roll",    "th": "ม้วน"},
    {"value": "pair",    "en": "Pair",    "th": "คู่"},
    {"value": "set",     "en": "Set",     "th": "ชุด"},
    {"value": "bag",     "en": "Bag",     "th": "ถุง"},
    {"value": "each",    "en": "Each",    "th": "อัน"},
]

PROCEDURE_TYPES = [
    {"value": "opu",              "en": "Oocyte Pick Up (OPU)",  "th": "เจาะไข่"},
    {"value": "embryo_transfer",  "en": "Embryo Transfer (ET)",  "th": "ย้ายตัวอ่อน"},
    {"value": "iui",              "en": "IUI",                   "th": "ฉีดอสุจิเข้าโพรงมดลูก"},
    {"value": "icsi",             "en": "ICSI",                  "th": "ICSI"},
    {"value": "ivf",              "en": "Conventional IVF",      "th": "IVF แบบดั้งเดิม"},
    {"value": "hysteroscopy",     "en": "Hysteroscopy",          "th": "ส่องกล้องโพรงมดลูก"},
    {"value": "ovarian_prp",      "en": "Ovarian PRP",           "th": "PRP รังไข่"},
    {"value": "endometrial_prp",  "en": "Endometrial PRP",       "th": "PRP เยื่อบุมดลูก"},
    {"value": "vitrification",    "en": "Vitrification",         "th": "แช่แข็ง"},
    {"value": "warming",          "en": "Warming/Thawing",       "th": "ละลาย"},
    {"value": "semen_analysis",   "en": "Semen Analysis",        "th": "ตรวจวิเคราะห์น้ำอสุจิ"},
    {"value": "sperm_prep",       "en": "Sperm Preparation",     "th": "เตรียมสเปิร์ม"},
    {"value": "lab_test",         "en": "Lab Test",              "th": "ตรวจแล็บ"},
    {"value": "other",            "en": "Other",                 "th": "อื่นๆ"},
]

STORAGE_OPTIONS = [
    {"en": "Room temperature (15-25°C)",       "th": "อุณหภูมิห้อง (15-25°C)"},
    {"en": "Refrigerated (2-8°C)",             "th": "แช่เย็น (2-8°C)"},
    {"en": "Frozen (-20°C)",                   "th": "แช่แข็ง (-20°C)"},
    {"en": "Ultra-low (-80°C)",                "th": "แช่แข็งพิเศษ (-80°C)"},
    {"en": "Liquid nitrogen (-196°C)",         "th": "ไนโตรเจนเหลว (-196°C)"},
    {"en": "Cool dry place, away from light",  "th": "ที่แห้ง เย็น พ้นแสง"},
]
