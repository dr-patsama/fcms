"""
FCMS Module 7 — Accounting Pydantic Schemas / สคีมาบัญชี
Request/response validation for service catalog, invoices, payments, expenses, closings.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal


# ── Service Catalog ───────────────────────────────────────

class ServiceCreate(BaseModel):
    service_code: Optional[str] = None          # auto-generated if omitted
    name_en: str = Field(..., min_length=1)
    name_th: Optional[str] = None
    category: str = Field(..., min_length=1)
    unit: str = "service"
    unit_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0")
    is_package: bool = False
    package_includes: Optional[List[dict]] = None
    description: Optional[str] = None
    description_th: Optional[str] = None
    active: bool = True


class ServiceUpdate(BaseModel):
    name_en: Optional[str] = None
    name_th: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    is_package: Optional[bool] = None
    package_includes: Optional[List[dict]] = None
    description: Optional[str] = None
    description_th: Optional[str] = None
    active: Optional[bool] = None


class ServiceOut(BaseModel):
    id: str
    service_code: str
    name_en: str
    name_th: Optional[str]
    category: str
    unit: Optional[str]
    unit_price: Decimal
    vat_rate: Decimal
    is_package: bool
    package_includes: Optional[Any]
    description: Optional[str]
    description_th: Optional[str]
    active: bool

    class Config:
        from_attributes = True


# ── Invoices ──────────────────────────────────────────────

class InvoiceItemCreate(BaseModel):
    service_id: Optional[str] = None
    description: str = Field(..., min_length=1)
    description_th: Optional[str] = None
    category: Optional[str] = None
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0")


class InvoiceCreate(BaseModel):
    patient_id: str
    invoice_date: Optional[date] = None          # defaults to today
    due_date: Optional[date] = None
    items: List[InvoiceItemCreate] = Field(..., min_length=1)
    discount_amount: Decimal = Decimal("0")
    discount_reason: Optional[str] = None
    is_tax_invoice: bool = False
    tax_id: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    notes_th: Optional[str] = None
    status: str = "issued"                       # draft | issued


class InvoiceVoid(BaseModel):
    void_reason: str = Field(..., min_length=1)


class InvoiceItemOut(BaseModel):
    id: str
    service_id: Optional[str]
    description: str
    description_th: Optional[str]
    category: Optional[str]
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: str
    invoice_number: str
    patient_id: str
    invoice_date: date
    due_date: Optional[date]
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    discount_reason: Optional[str]
    vat_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    is_tax_invoice: bool
    tax_invoice_number: Optional[str]
    tax_id: Optional[str]
    billing_name: Optional[str]
    notes: Optional[str]
    notes_th: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class InvoiceDetailOut(InvoiceOut):
    items: List[InvoiceItemOut] = []


# ── Payments ──────────────────────────────────────────────

class PaymentCreate(BaseModel):
    invoice_id: str
    payment_date: Optional[date] = None          # defaults to today
    amount: Decimal = Field(..., gt=0)
    method: str = Field(..., min_length=1)
    reference_number: Optional[str] = None
    card_last4: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None


class PaymentVoid(BaseModel):
    void_reason: str = Field(..., min_length=1)


class PaymentOut(BaseModel):
    id: str
    receipt_number: str
    invoice_id: str
    patient_id: str
    payment_date: date
    amount: Decimal
    method: str
    reference_number: Optional[str]
    card_last4: Optional[str]
    bank_name: Optional[str]
    notes: Optional[str]
    is_void: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Expenses ──────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    expense_date: Optional[date] = None
    category: str = Field(..., min_length=1)
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    description: str = Field(..., min_length=1)
    description_th: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    vat_amount: Decimal = Decimal("0")
    withholding_tax_rate: Decimal = Decimal("0")
    payment_method: str = "bank_transfer"
    reference_number: Optional[str] = None
    receipt_attached: bool = False


class ExpenseUpdate(BaseModel):
    expense_date: Optional[date] = None
    category: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    description: Optional[str] = None
    description_th: Optional[str] = None
    amount: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    withholding_tax_rate: Optional[Decimal] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    receipt_attached: Optional[bool] = None
    status: Optional[str] = None


class ExpenseOut(BaseModel):
    id: str
    expense_number: str
    expense_date: date
    category: str
    vendor_name: Optional[str]
    vendor_tax_id: Optional[str]
    description: str
    description_th: Optional[str]
    amount: Decimal
    vat_amount: Decimal
    withholding_tax_rate: Decimal
    withholding_tax_amount: Decimal
    net_paid: Decimal
    payment_method: Optional[str]
    reference_number: Optional[str]
    receipt_attached: bool
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Daily Closing ─────────────────────────────────────────

class ClosingCreate(BaseModel):
    closing_date: Optional[date] = None          # defaults to today
    cash_counted: Decimal = Decimal("0")
    notes: Optional[str] = None


class ClosingOut(BaseModel):
    id: str
    closing_date: date
    cash_expected: Decimal
    cash_counted: Decimal
    cash_variance: Decimal
    card_total: Decimal
    transfer_total: Decimal
    promptpay_total: Decimal
    insurance_total: Decimal
    other_total: Decimal
    total_revenue: Decimal
    invoice_count: int
    payment_count: int
    notes: Optional[str]
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True
