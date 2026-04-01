"""
FCMS Module 5 — Medical Supply ORM Models / โมเดลฐานข้อมูลเวชภัณฑ์
Supply catalogue, suppliers, stock lots, transactions, requisitions, usage logs.
Covers: plasticware, lab media, test kits, cryostorage, consumables, PPE.
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
from ...module1.backend.core.database import Base


# ── Supplier Master ───────────────────────────────────────

class Supplier(Base):
    """Supplier/vendor record with contact details."""
    __tablename__ = "suppliers"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    name              = Column(String(200), nullable=False, index=True)
    name_th           = Column(String(200))
    code              = Column(String(20), unique=True)  # SUP-001
    contact_person    = Column(String(100))
    phone             = Column(String(50))
    email             = Column(String(100))
    address           = Column(Text)
    address_th        = Column(Text)
    tax_id            = Column(String(30))
    payment_terms     = Column(String(50))   # Net 30, COD, etc.
    notes             = Column(Text)
    is_active         = Column(Boolean, default=True, index=True)
    created_by        = Column(UUID, ForeignKey("users.id"))
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), onupdate=func.now())

    supplies = relationship("MedicalSupply", back_populates="default_supplier_rel", lazy="dynamic")


# ── Medical Supply Catalogue ──────────────────────────────

class MedicalSupply(Base):
    """Medical supply item master with bilingual names and specs."""
    __tablename__ = "medical_supplies"

    id                    = Column(UUID, primary_key=True, default=gen_uuid)
    # Names (bilingual)
    name_en               = Column(String(200), nullable=False, index=True)
    name_th               = Column(String(200))
    description_en        = Column(Text)
    description_th        = Column(Text)
    # Classification
    category              = Column(String(30), nullable=False, index=True)
    # plasticware | lab_media | test_kit | cryostorage | consumable
    # ppe | cleaning | general
    subcategory           = Column(String(50))
    # SKU / catalog number
    sku                   = Column(String(50), unique=True)
    catalog_number        = Column(String(50))   # Manufacturer catalog #
    # Physical specs
    unit                  = Column(String(30), nullable=False)  # piece, box, bottle, pack, vial, liter
    unit_th               = Column(String(30))
    pack_size             = Column(Integer, default=1)         # items per unit (e.g. 100 dishes/box)
    # Supply chain
    manufacturer          = Column(String(200))
    default_supplier_id   = Column(UUID, ForeignKey("suppliers.id"))
    reorder_level         = Column(Integer, default=10)
    reorder_quantity      = Column(Integer, default=50)
    unit_cost             = Column(Numeric(10, 2))
    # Storage
    storage_condition     = Column(String(100))
    storage_condition_th  = Column(String(100))
    requires_refrigeration = Column(Boolean, default=False)
    requires_sterile      = Column(Boolean, default=False)
    # Department allocation
    department            = Column(String(30))
    # embryology_lab | andrology_lab | general_lab | clinic | operating_room | all
    # Status
    is_active             = Column(Boolean, default=True, index=True)
    current_stock         = Column(Integer, default=0)
    # Audit
    created_by            = Column(UUID, ForeignKey("users.id"))
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    default_supplier_rel  = relationship("Supplier", back_populates="supplies")
    stock_lots            = relationship("SupplyStockLot", back_populates="supply", lazy="dynamic")
    transactions          = relationship("SupplyTransaction", back_populates="supply", lazy="dynamic")


# ── Stock Lots (per lot/expiry tracking) ──────────────────

class SupplyStockLot(Base):
    """Individual stock lot with expiry tracking for FIFO usage."""
    __tablename__ = "supply_stock_lots"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    supply_id        = Column(UUID, ForeignKey("medical_supplies.id"), nullable=False, index=True)
    lot_number       = Column(String(50), nullable=False, index=True)
    expiry_date      = Column(Date, index=True)   # nullable — some supplies don't expire
    initial_quantity = Column(Integer, nullable=False)
    current_quantity = Column(Integer, nullable=False)
    unit_cost        = Column(Numeric(10, 2))
    supplier_id      = Column(UUID, ForeignKey("suppliers.id"))
    po_number        = Column(String(50))
    invoice_number   = Column(String(50))
    grn_number       = Column(String(50))   # Goods Received Note
    received_by      = Column(UUID, ForeignKey("users.id"))
    received_at      = Column(DateTime(timezone=True), server_default=func.now())
    notes            = Column(Text)
    is_active        = Column(Boolean, default=True)

    supply = relationship("MedicalSupply", back_populates="stock_lots")

    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="ck_supply_lot_qty_non_negative"),
    )


# ── Stock Transactions ────────────────────────────────────

class SupplyTransaction(Base):
    """Immutable log of every supply stock movement."""
    __tablename__ = "supply_transactions"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    supply_id        = Column(UUID, ForeignKey("medical_supplies.id"), nullable=False, index=True)
    lot_id           = Column(UUID, ForeignKey("supply_stock_lots.id"))
    transaction_type = Column(String(20), nullable=False, index=True)
    # receive | issue | adjust_add | adjust_remove | return | expired_write_off
    quantity         = Column(Integer, nullable=False)  # +ve for in, -ve for out
    balance_after    = Column(Integer)
    reference_type   = Column(String(30))  # requisition | adjustment | po | return | procedure
    reference_id     = Column(UUID)
    department       = Column(String(30))  # which department used it
    reason           = Column(Text)
    performed_by     = Column(UUID, ForeignKey("users.id"))
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    supply = relationship("MedicalSupply", back_populates="transactions")


# ── Requisitions (department requests) ────────────────────

class SupplyRequisition(Base):
    """Internal requisition — department requests supplies from store."""
    __tablename__ = "supply_requisitions"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    req_number       = Column(String(20), unique=True, nullable=False)  # REQ-2026-00001
    department       = Column(String(30), nullable=False)
    # embryology_lab | andrology_lab | general_lab | clinic | operating_room
    requested_by     = Column(UUID, ForeignKey("users.id"), nullable=False)
    status           = Column(String(20), default="pending", index=True)
    # pending | approved | partially_issued | issued | rejected | cancelled
    priority         = Column(String(10), default="normal")  # normal | urgent
    notes            = Column(Text)
    notes_th         = Column(Text)
    approved_by      = Column(UUID, ForeignKey("users.id"))
    approved_at      = Column(DateTime(timezone=True))
    issued_by        = Column(UUID, ForeignKey("users.id"))
    issued_at        = Column(DateTime(timezone=True))
    rejected_by      = Column(UUID, ForeignKey("users.id"))
    rejected_at      = Column(DateTime(timezone=True))
    reject_reason    = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    items = relationship("RequisitionItem", back_populates="requisition", cascade="all, delete-orphan")


class RequisitionItem(Base):
    """Individual line item in a requisition."""
    __tablename__ = "requisition_items"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    requisition_id   = Column(UUID, ForeignKey("supply_requisitions.id"), nullable=False)
    supply_id        = Column(UUID, ForeignKey("medical_supplies.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    quantity_issued  = Column(Integer, default=0)
    notes            = Column(Text)

    requisition = relationship("SupplyRequisition", back_populates="items")


# ── Usage Log (procedure-level tracking) ──────────────────

class SupplyUsageLog(Base):
    """Track supply usage per procedure/patient for cost analysis."""
    __tablename__ = "supply_usage_logs"

    id             = Column(UUID, primary_key=True, default=gen_uuid)
    supply_id      = Column(UUID, ForeignKey("medical_supplies.id"), nullable=False, index=True)
    lot_id         = Column(UUID, ForeignKey("supply_stock_lots.id"))
    quantity_used  = Column(Integer, nullable=False)
    department     = Column(String(30), nullable=False)
    procedure_type = Column(String(50))
    # opu | embryo_transfer | iui | icsi | hysteroscopy | prp | lab_test | other
    patient_id     = Column(UUID, ForeignKey("patients.id"))
    visit_id       = Column(UUID)
    used_by        = Column(UUID, ForeignKey("users.id"), nullable=False)
    notes          = Column(Text)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)
