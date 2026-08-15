"""
FCMS Module 7 — Accounting Database Migration
Tables: service_catalog, invoices, invoice_items, payments, expenses, daily_closings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "m7_001"
down_revision = "m6_001"
branch_labels = None
depends_on = None


def upgrade():
    # ── Service Catalog ────────────────────────────────────
    op.create_table("service_catalog",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("service_code", sa.String(20), unique=True, nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_th", sa.String(200)),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("unit", sa.String(30), server_default="service"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="0"),
        sa.Column("is_package", sa.Boolean, server_default=sa.text("false")),
        sa.Column("package_includes", JSON),
        sa.Column("description", sa.Text),
        sa.Column("description_th", sa.Text),
        sa.Column("active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_svc_category", "service_catalog", ["category"])
    op.create_index("ix_svc_active", "service_catalog", ["active"])

    # ── Invoices ───────────────────────────────────────────
    op.create_table("invoices",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("invoice_number", sa.String(20), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date),
        sa.Column("status", sa.String(20), server_default="issued"),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("discount_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("discount_reason", sa.String(200)),
        sa.Column("vat_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("balance_due", sa.Numeric(12, 2), server_default="0"),
        sa.Column("is_tax_invoice", sa.Boolean, server_default=sa.text("false")),
        sa.Column("tax_invoice_number", sa.String(30)),
        sa.Column("tax_id", sa.String(20)),
        sa.Column("billing_name", sa.String(200)),
        sa.Column("billing_address", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("notes_th", sa.Text),
        sa.Column("void_reason", sa.Text),
        sa.Column("voided_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_inv_patient", "invoices", ["patient_id"])
    op.create_index("ix_inv_date", "invoices", ["invoice_date"])
    op.create_index("ix_inv_status", "invoices", ["status"])

    # ── Invoice Items ──────────────────────────────────────
    op.create_table("invoice_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("invoice_id", UUID, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("service_id", UUID, sa.ForeignKey("service_catalog.id")),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("description_th", sa.String(300)),
        sa.Column("category", sa.String(30)),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="0"),
        sa.Column("line_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_invitem_invoice", "invoice_items", ["invoice_id"])
    op.create_index("ix_invitem_category", "invoice_items", ["category"])

    # ── Payments ───────────────────────────────────────────
    op.create_table("payments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("receipt_number", sa.String(20), unique=True, nullable=False),
        sa.Column("invoice_id", UUID, sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("card_last4", sa.String(4)),
        sa.Column("bank_name", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("is_void", sa.Boolean, server_default=sa.text("false")),
        sa.Column("void_reason", sa.Text),
        sa.Column("voided_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("received_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pay_invoice", "payments", ["invoice_id"])
    op.create_index("ix_pay_patient", "payments", ["patient_id"])
    op.create_index("ix_pay_date", "payments", ["payment_date"])
    op.create_index("ix_pay_method", "payments", ["method"])

    # ── Expenses ───────────────────────────────────────────
    op.create_table("expenses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("expense_number", sa.String(20), unique=True, nullable=False),
        sa.Column("expense_date", sa.Date, nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("vendor_name", sa.String(200)),
        sa.Column("vendor_tax_id", sa.String(20)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("description_th", sa.Text),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("withholding_tax_rate", sa.Numeric(5, 2), server_default="0"),
        sa.Column("withholding_tax_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("net_paid", sa.Numeric(12, 2), server_default="0"),
        sa.Column("payment_method", sa.String(20), server_default="bank_transfer"),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("receipt_attached", sa.Boolean, server_default=sa.text("false")),
        sa.Column("status", sa.String(20), server_default="recorded"),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_exp_date", "expenses", ["expense_date"])
    op.create_index("ix_exp_category", "expenses", ["category"])
    op.create_index("ix_exp_status", "expenses", ["status"])

    # ── Daily Closings ─────────────────────────────────────
    op.create_table("daily_closings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("closing_date", sa.Date, unique=True, nullable=False),
        sa.Column("cash_expected", sa.Numeric(12, 2), server_default="0"),
        sa.Column("cash_counted", sa.Numeric(12, 2), server_default="0"),
        sa.Column("cash_variance", sa.Numeric(12, 2), server_default="0"),
        sa.Column("card_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("transfer_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("promptpay_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("insurance_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("other_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_revenue", sa.Numeric(12, 2), server_default="0"),
        sa.Column("invoice_count", sa.Integer, server_default="0"),
        sa.Column("payment_count", sa.Integer, server_default="0"),
        sa.Column("notes", sa.Text),
        sa.Column("closed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_closing_date", "daily_closings", ["closing_date"])


def downgrade():
    op.drop_table("daily_closings")
    op.drop_table("expenses")
    op.drop_table("payments")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("service_catalog")
