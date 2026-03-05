"""
FCMS Module 4 — Pharmacy Database Migration
Tables: drugs, drug_stock_lots, stock_transactions, prescriptions,
        prescription_items, dispensing_records, dispensing_items
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "m4_001"
down_revision = "m3_001_ultrasound"
branch_labels = None
depends_on = None


def upgrade():
    # ── Drug Catalogue ──────────────────────────────────
    op.create_table("drugs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("generic_name", sa.String(200), nullable=False),
        sa.Column("brand_name", sa.String(200)),
        sa.Column("category", sa.String(50)),
        sa.Column("form", sa.String(30), nullable=False),  # Tablet, Capsule, Injection...
        sa.Column("strength", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),  # tablet, capsule, vial, ml...
        sa.Column("manufacturer", sa.String(200)),
        sa.Column("supplier", sa.String(200)),
        sa.Column("reorder_level", sa.Integer, default=50),
        sa.Column("reorder_quantity", sa.Integer, default=200),
        sa.Column("unit_cost", sa.Numeric(10, 2)),
        sa.Column("selling_price", sa.Numeric(10, 2)),
        sa.Column("storage_condition", sa.String(100)),
        sa.Column("instructions_en", sa.Text),
        sa.Column("instructions_th", sa.Text),
        sa.Column("requires_refrigeration", sa.Boolean, default=False),
        sa.Column("is_controlled", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("current_stock", sa.Integer, default=0),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_drugs_generic", "drugs", ["generic_name"])
    op.create_index("ix_drugs_category", "drugs", ["category"])
    op.create_index("ix_drugs_active", "drugs", ["is_active"])

    # ── Stock Lots (per lot/expiry tracking) ────────────
    op.create_table("drug_stock_lots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("drug_id", UUID, sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("lot_number", sa.String(50), nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("initial_quantity", sa.Integer, nullable=False),
        sa.Column("current_quantity", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2)),
        sa.Column("supplier", sa.String(200)),
        sa.Column("po_number", sa.String(50)),
        sa.Column("invoice_number", sa.String(50)),
        sa.Column("received_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
    )
    op.create_index("ix_stock_lots_drug", "drug_stock_lots", ["drug_id"])
    op.create_index("ix_stock_lots_expiry", "drug_stock_lots", ["expiry_date"])
    op.create_index("ix_stock_lots_lot", "drug_stock_lots", ["lot_number"])

    # ── Stock Transactions (receipt, adjustment, dispense) ──
    op.create_table("stock_transactions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("drug_id", UUID, sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("lot_id", UUID, sa.ForeignKey("drug_stock_lots.id")),
        sa.Column("transaction_type", sa.String(20), nullable=False),  # receive | dispense | adjust | return
        sa.Column("quantity", sa.Integer, nullable=False),  # +ve for in, -ve for out
        sa.Column("balance_after", sa.Integer),
        sa.Column("reference_type", sa.String(20)),  # prescription | adjustment | po
        sa.Column("reference_id", UUID),
        sa.Column("reason", sa.Text),
        sa.Column("performed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stock_tx_drug", "stock_transactions", ["drug_id"])
    op.create_index("ix_stock_tx_type", "stock_transactions", ["transaction_type"])
    op.create_index("ix_stock_tx_date", "stock_transactions", ["created_at"])

    # ── Prescriptions (from EMR) ────────────────────────
    op.create_table("prescriptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("visit_id", UUID),
        sa.Column("prescriber_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),  # pending | verified | dispensed | cancelled
        sa.Column("priority", sa.String(10), default="normal"),  # normal | urgent | stat
        sa.Column("notes", sa.Text),
        sa.Column("verified_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("dispensed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("dispensed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rx_patient", "prescriptions", ["patient_id"])
    op.create_index("ix_rx_status", "prescriptions", ["status"])
    op.create_index("ix_rx_date", "prescriptions", ["created_at"])

    # ── Prescription Items ──────────────────────────────
    op.create_table("prescription_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("prescription_id", UUID, sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("drug_id", UUID, sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("dosage", sa.String(100)),
        sa.Column("frequency", sa.String(100)),
        sa.Column("frequency_th", sa.String(100)),
        sa.Column("route", sa.String(50)),
        sa.Column("route_th", sa.String(50)),
        sa.Column("duration_days", sa.Integer),
        sa.Column("instructions_en", sa.Text),
        sa.Column("instructions_th", sa.Text),
        sa.Column("warnings", sa.Text),  # JSON array
    )

    # ── Dispensing Records ──────────────────────────────
    op.create_table("dispensing_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("prescription_id", UUID, sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("dispensed_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("counseling_notes", sa.Text),
        sa.Column("labels_printed", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Dispensing Items (with lot tracking) ────────────
    op.create_table("dispensing_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("dispensing_id", UUID, sa.ForeignKey("dispensing_records.id"), nullable=False),
        sa.Column("drug_id", UUID, sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("lot_id", UUID, sa.ForeignKey("drug_stock_lots.id")),
        sa.Column("quantity_dispensed", sa.Integer, nullable=False),
        sa.Column("instructions_en", sa.Text),
        sa.Column("instructions_th", sa.Text),
    )


def downgrade():
    op.drop_table("dispensing_items")
    op.drop_table("dispensing_records")
    op.drop_table("prescription_items")
    op.drop_table("prescriptions")
    op.drop_table("stock_transactions")
    op.drop_table("drug_stock_lots")
    op.drop_table("drugs")
