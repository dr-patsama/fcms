"""
FCMS Module 4 — Pharmacy ORM Models / โมเดลฐานข้อมูลเภสัชกรรม
Drug catalogue, stock lots, transactions, prescriptions, dispensing records.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Numeric, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

def gen_uuid():
    return str(uuid.uuid4())

# Import Base from shared core (module1)
from module1.backend.core.database import Base


# ── Drug Catalogue ─────────────────────────────────────────

class Drug(Base):
    """Drug master record with bilingual names and instructions."""
    __tablename__ = "drugs"

    id                    = Column(UUID, primary_key=True, default=gen_uuid)
    generic_name          = Column(String(200), nullable=False, index=True)
    generic_name_th       = Column(String(200))
    brand_name            = Column(String(200))
    brand_name_th         = Column(String(200))
    category              = Column(String(50), index=True)
    # hormonal | ivf_protocol | antibiotic | analgesic | vitamin
    # anesthetic | anticoagulant | antifungal | other
    form                  = Column(String(30), nullable=False)
    # tablet | capsule | injection | cream_gel | suppository
    # liquid_syrup | patch | nasal_spray | vaginal_tablet
    form_th               = Column(String(30))
    strength              = Column(String(50), nullable=False)
    unit                  = Column(String(30), nullable=False)  # tablet, vial, ml, amp...
    unit_th               = Column(String(30))
    manufacturer          = Column(String(200))
    supplier              = Column(String(200))
    reorder_level         = Column(Integer, default=50)
    reorder_quantity      = Column(Integer, default=200)
    pack_size             = Column(Integer)  # units per box/pack — drives Rx quantity round-up / จำนวนต่อกล่อง ใช้ปัดจำนวนจ่ายขึ้นเต็มกล่อง
    unit_cost             = Column(Numeric(10, 2))
    selling_price         = Column(Numeric(10, 2))
    storage_condition     = Column(String(100))
    storage_condition_th  = Column(String(100))
    instructions_en       = Column(Text)
    instructions_th       = Column(Text)
    warnings_en           = Column(Text)
    warnings_th           = Column(Text)
    requires_refrigeration = Column(Boolean, default=False)
    is_controlled         = Column(Boolean, default=False)
    is_active             = Column(Boolean, default=True, index=True)
    current_stock         = Column(Integer, default=0)

    # Label defaults
    label_dose_en         = Column(String(200))  # e.g. "Take 1 tablet twice daily"
    label_dose_th         = Column(String(200))  # e.g. "รับประทานครั้งละ 1 เม็ด วันละ 2 ครั้ง"
    label_route_en        = Column(String(100))  # e.g. "Oral"
    label_route_th        = Column(String(100))  # e.g. "รับประทาน"
    label_frequency_en    = Column(String(100))  # e.g. "Every 12 hours"
    label_frequency_th    = Column(String(100))  # e.g. "ทุก 12 ชั่วโมง"
    label_warnings_en     = Column(Text)          # JSON array
    label_warnings_th     = Column(Text)          # JSON array

    created_by = Column(UUID, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stock_lots   = relationship("DrugStockLot", back_populates="drug", lazy="dynamic")
    transactions = relationship("StockTransaction", back_populates="drug", lazy="dynamic")


# ── Stock Lots (per lot/expiry tracking) ───────────────────

class DrugStockLot(Base):
    """Individual stock lot with expiry tracking for FIFO dispensing."""
    __tablename__ = "drug_stock_lots"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    drug_id          = Column(UUID, ForeignKey("drugs.id"), nullable=False, index=True)
    lot_number       = Column(String(50), nullable=False, index=True)
    expiry_date      = Column(Date, nullable=False, index=True)
    initial_quantity = Column(Integer, nullable=False)
    current_quantity = Column(Integer, nullable=False)
    unit_cost        = Column(Numeric(10, 2))
    supplier         = Column(String(200))
    po_number        = Column(String(50))
    invoice_number   = Column(String(50))
    received_by      = Column(UUID, ForeignKey("users.id"))
    received_at      = Column(DateTime(timezone=True), server_default=func.now())
    notes            = Column(Text)
    is_active        = Column(Boolean, default=True)

    drug = relationship("Drug", back_populates="stock_lots")

    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="ck_lot_qty_non_negative"),
    )


# ── Stock Transactions ─────────────────────────────────────

class StockTransaction(Base):
    """Immutable log of every stock movement."""
    __tablename__ = "stock_transactions"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    drug_id          = Column(UUID, ForeignKey("drugs.id"), nullable=False, index=True)
    lot_id           = Column(UUID, ForeignKey("drug_stock_lots.id"))
    transaction_type = Column(String(20), nullable=False, index=True)
    # receive | dispense | adjust_add | adjust_remove | return | expired_write_off
    quantity         = Column(Integer, nullable=False)  # +ve for in, -ve for out
    balance_after    = Column(Integer)
    reference_type   = Column(String(20))  # prescription | adjustment | po | return
    reference_id     = Column(UUID)
    reason           = Column(Text)
    performed_by     = Column(UUID, ForeignKey("users.id"))
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    drug = relationship("Drug", back_populates="transactions")


# ── Prescriptions ──────────────────────────────────────────

class Prescription(Base):
    """Prescription from EMR, flows through verify → dispense."""
    __tablename__ = "prescriptions"

    id             = Column(UUID, primary_key=True, default=gen_uuid)
    rx_number      = Column(String(20), unique=True, nullable=False)  # RX-2026-00001
    patient_id     = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    visit_id       = Column(UUID)
    prescriber_id  = Column(UUID, ForeignKey("users.id"), nullable=False)
    status         = Column(String(20), default="pending", index=True)
    # pending | verified | dispensed | partially_dispensed | cancelled
    priority       = Column(String(10), default="normal")  # normal | urgent | stat
    diagnosis_en   = Column(Text)  # printed on the prescription document / วินิจฉัยบนใบสั่งยา
    diagnosis_th   = Column(Text)
    notes          = Column(Text)
    notes_th       = Column(Text)
    verified_by    = Column(UUID, ForeignKey("users.id"))
    verified_at    = Column(DateTime(timezone=True))
    dispensed_by   = Column(UUID, ForeignKey("users.id"))
    dispensed_at   = Column(DateTime(timezone=True))
    cancelled_by   = Column(UUID, ForeignKey("users.id"))
    cancelled_at   = Column(DateTime(timezone=True))
    cancel_reason  = Column(Text)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    """Individual medication line in a prescription."""
    __tablename__ = "prescription_items"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    prescription_id  = Column(UUID, ForeignKey("prescriptions.id"), nullable=False)
    drug_id          = Column(UUID, ForeignKey("drugs.id"), nullable=False)
    quantity         = Column(Integer, nullable=False)   # final quantity to dispense (rounded up to full packs)
    quantity_needed  = Column(Integer)                    # exact clinical need = dose × times/day × days
    dose_per_time    = Column(Numeric(6, 2))              # e.g. 2 (tablets per dose)
    times_per_day    = Column(Integer)                    # e.g. 2 (bid)
    sig_en           = Column(Text)                       # full directions, e.g. "Take 2 tablets orally twice daily after meals"
    sig_th           = Column(Text)                       # e.g. "รับประทานครั้งละ 2 เม็ด วันละ 2 ครั้ง หลังอาหาร"
    dosage           = Column(String(100))  # e.g. "200mg"
    frequency        = Column(String(100))  # e.g. "Twice daily"
    frequency_th     = Column(String(100))  # e.g. "วันละ 2 ครั้ง"
    route            = Column(String(50))   # e.g. "Oral"
    route_th         = Column(String(50))   # e.g. "รับประทาน"
    duration_days    = Column(Integer)
    instructions_en  = Column(Text)         # e.g. "Take after meals"
    instructions_th  = Column(Text)         # e.g. "รับประทานหลังอาหาร"
    warnings         = Column(JSON)         # ["Avoid alcohol", "หลีกเลี่ยงแอลกอฮอล์"]

    prescription = relationship("Prescription", back_populates="items")


# ── Dispensing Records ─────────────────────────────────────

class DispensingRecord(Base):
    """Record of actual dispensing event."""
    __tablename__ = "dispensing_records"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    prescription_id  = Column(UUID, ForeignKey("prescriptions.id"), nullable=False)
    patient_id       = Column(UUID, ForeignKey("patients.id"), nullable=False)
    dispensed_by     = Column(UUID, ForeignKey("users.id"), nullable=False)
    counseling_notes = Column(Text)
    counseling_notes_th = Column(Text)
    labels_printed   = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("DispensingItem", back_populates="dispensing_record", cascade="all, delete-orphan")


class DispensingItem(Base):
    """Individual item dispensed with lot tracking."""
    __tablename__ = "dispensing_items"

    id                 = Column(UUID, primary_key=True, default=gen_uuid)
    dispensing_id      = Column(UUID, ForeignKey("dispensing_records.id"), nullable=False)
    drug_id            = Column(UUID, ForeignKey("drugs.id"), nullable=False)
    lot_id             = Column(UUID, ForeignKey("drug_stock_lots.id"))
    quantity_dispensed = Column(Integer, nullable=False)
    instructions_en    = Column(Text)
    instructions_th    = Column(Text)

    dispensing_record = relationship("DispensingRecord", back_populates="items")
