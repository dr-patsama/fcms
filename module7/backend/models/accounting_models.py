"""
FCMS Module 7 — Accounting ORM Models / โมเดลฐานข้อมูลบัญชี
Service catalog (price list), invoices, payments/receipts, expenses, daily cash closings.

Thai tax notes:
- Medical services at licensed clinics are VAT-exempt → default vat_rate = 0.
  Retail items (supplements, cosmetics, products) may carry 7% VAT per item.
- Tax invoice (ใบกำกับภาษี) issued on request for VATable items.
- Expenses support withholding tax (ภาษีหัก ณ ที่จ่าย) for services/rent (1–5%).
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

def gen_uuid():
    return str(uuid.uuid4())

from ...module1.backend.core.database import Base


# ── Service Catalog / รายการค่าบริการ ─────────────────────

class ServiceCatalog(Base):
    """Clinic price list: consultations, labs, procedures, packages, retail items."""
    __tablename__ = "service_catalog"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    service_code  = Column(String(20), unique=True, nullable=False)   # SVC-0001
    name_en       = Column(String(200), nullable=False)
    name_th       = Column(String(200))
    category      = Column(String(30), nullable=False, index=True)
    # consultation | laboratory | ultrasound | procedure | ivf_package
    # medication | retail | other
    unit          = Column(String(30), default="service")             # service|test|cycle|item
    unit_price    = Column(Numeric(12, 2), nullable=False, default=0)
    vat_rate      = Column(Numeric(5, 2), default=0)                  # 0 = medical exempt, 7 = retail
    is_package    = Column(Boolean, default=False)
    package_includes = Column(JSON)        # [{"name_en": "...", "name_th": "...", "qty": 1}]
    description   = Column(Text)
    description_th= Column(Text)
    active        = Column(Boolean, default=True, index=True)
    created_by    = Column(UUID, ForeignKey("users.id"))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True))


# ── Invoices / ใบแจ้งหนี้ ─────────────────────────────────

class Invoice(Base):
    """Patient invoice with line items; supports deposits, discounts, tax invoice issue."""
    __tablename__ = "invoices"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    invoice_number    = Column(String(20), unique=True, nullable=False)   # INV-2026-00001
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    invoice_date      = Column(Date, nullable=False, index=True)
    due_date          = Column(Date)
    status            = Column(String(20), default="issued", index=True)
    # draft | issued | partially_paid | paid | void
    # Amounts
    subtotal          = Column(Numeric(12, 2), default=0)
    discount_amount   = Column(Numeric(12, 2), default=0)
    discount_reason   = Column(String(200))
    vat_amount        = Column(Numeric(12, 2), default=0)
    total_amount      = Column(Numeric(12, 2), default=0)
    paid_amount       = Column(Numeric(12, 2), default=0)
    balance_due       = Column(Numeric(12, 2), default=0)
    # Thai tax invoice
    is_tax_invoice    = Column(Boolean, default=False)
    tax_invoice_number= Column(String(30))
    tax_id            = Column(String(20))       # patient / company tax ID for ใบกำกับภาษี
    billing_name      = Column(String(200))      # name on tax invoice if different
    billing_address   = Column(Text)
    # Meta
    notes             = Column(Text)
    notes_th          = Column(Text)
    void_reason       = Column(Text)
    voided_by         = Column(UUID, ForeignKey("users.id"))
    voided_at         = Column(DateTime(timezone=True))
    created_by        = Column(UUID, ForeignKey("users.id"))
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True))

    items    = relationship("InvoiceItem", back_populates="invoice",
                            cascade="all, delete-orphan", order_by="InvoiceItem.sort_order")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceItem(Base):
    """Single line on an invoice."""
    __tablename__ = "invoice_items"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    invoice_id    = Column(UUID, ForeignKey("invoices.id"), nullable=False, index=True)
    service_id    = Column(UUID, ForeignKey("service_catalog.id"))
    description   = Column(String(300), nullable=False)
    description_th= Column(String(300))
    category      = Column(String(30))            # denormalised for reporting
    quantity      = Column(Numeric(10, 2), default=1)
    unit_price    = Column(Numeric(12, 2), nullable=False, default=0)
    vat_rate      = Column(Numeric(5, 2), default=0)
    line_total    = Column(Numeric(12, 2), default=0)   # qty * price (ex-VAT)
    sort_order    = Column(Integer, default=0)

    invoice = relationship("Invoice", back_populates="items")


# ── Payments / การรับชำระเงิน ─────────────────────────────

class Payment(Base):
    """Payment receipt against an invoice. Partial payments supported."""
    __tablename__ = "payments"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    receipt_number  = Column(String(20), unique=True, nullable=False)   # RC-2026-00001
    invoice_id      = Column(UUID, ForeignKey("invoices.id"), nullable=False, index=True)
    patient_id      = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    payment_date    = Column(Date, nullable=False, index=True)
    amount          = Column(Numeric(12, 2), nullable=False)
    method          = Column(String(20), nullable=False, index=True)
    # cash | credit_card | debit_card | bank_transfer | promptpay | insurance | other
    reference_number= Column(String(100))     # slip / approval / policy number
    card_last4      = Column(String(4))
    bank_name       = Column(String(100))
    notes           = Column(Text)
    is_void         = Column(Boolean, default=False)
    void_reason     = Column(Text)
    voided_by       = Column(UUID, ForeignKey("users.id"))
    voided_at       = Column(DateTime(timezone=True))
    received_by     = Column(UUID, ForeignKey("users.id"))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="payments")


# ── Expenses / ค่าใช้จ่าย ─────────────────────────────────

class Expense(Base):
    """Clinic operating expense with Thai withholding tax support."""
    __tablename__ = "expenses"

    id                    = Column(UUID, primary_key=True, default=gen_uuid)
    expense_number        = Column(String(20), unique=True, nullable=False)   # EXP-2026-00001
    expense_date          = Column(Date, nullable=False, index=True)
    category              = Column(String(30), nullable=False, index=True)
    # salaries | rent | utilities | medical_supplies | lab_reagents | medications
    # equipment | maintenance | marketing | insurance | professional_fees
    # bank_fees | taxes | other
    vendor_name           = Column(String(200))
    vendor_tax_id         = Column(String(20))
    description           = Column(Text, nullable=False)
    description_th        = Column(Text)
    amount                = Column(Numeric(12, 2), nullable=False)            # base amount ex-VAT
    vat_amount            = Column(Numeric(12, 2), default=0)                 # input VAT paid
    withholding_tax_rate  = Column(Numeric(5, 2), default=0)                  # 1 / 2 / 3 / 5 %
    withholding_tax_amount= Column(Numeric(12, 2), default=0)
    net_paid              = Column(Numeric(12, 2), default=0)                 # amount + VAT − WHT
    payment_method        = Column(String(20), default="bank_transfer")
    reference_number      = Column(String(100))
    receipt_attached      = Column(Boolean, default=False)
    status                = Column(String(20), default="recorded", index=True)
    # recorded | approved | void
    approved_by           = Column(UUID, ForeignKey("users.id"))
    created_by            = Column(UUID, ForeignKey("users.id"))
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True))


# ── Daily Closing / ปิดยอดประจำวัน ────────────────────────

class DailyClosing(Base):
    """End-of-day cash reconciliation and revenue summary."""
    __tablename__ = "daily_closings"

    id             = Column(UUID, primary_key=True, default=gen_uuid)
    closing_date   = Column(Date, unique=True, nullable=False, index=True)
    cash_expected  = Column(Numeric(12, 2), default=0)   # sum of non-void cash payments
    cash_counted   = Column(Numeric(12, 2), default=0)   # physically counted
    cash_variance  = Column(Numeric(12, 2), default=0)
    card_total     = Column(Numeric(12, 2), default=0)
    transfer_total = Column(Numeric(12, 2), default=0)
    promptpay_total= Column(Numeric(12, 2), default=0)
    insurance_total= Column(Numeric(12, 2), default=0)
    other_total    = Column(Numeric(12, 2), default=0)
    total_revenue  = Column(Numeric(12, 2), default=0)
    invoice_count  = Column(Integer, default=0)
    payment_count  = Column(Integer, default=0)
    notes          = Column(Text)
    closed_by      = Column(UUID, ForeignKey("users.id"))
    closed_at      = Column(DateTime(timezone=True), server_default=func.now())
