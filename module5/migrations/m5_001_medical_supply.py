"""
FCMS Module 5 — Medical Supply Database Migration
Tables: suppliers, medical_supplies, supply_stock_lots, supply_transactions,
        supply_requisitions, requisition_items, supply_usage_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "m5_001"
down_revision = "m4_001"
branch_labels = None
depends_on = None


def upgrade():
    # ── Suppliers ──────────────────────────────────────────
    op.create_table("suppliers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_th", sa.String(200)),
        sa.Column("code", sa.String(20), unique=True),
        sa.Column("contact_person", sa.String(100)),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(100)),
        sa.Column("address", sa.Text),
        sa.Column("address_th", sa.Text),
        sa.Column("tax_id", sa.String(30)),
        sa.Column("payment_terms", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_index("ix_suppliers_active", "suppliers", ["is_active"])

    # ── Medical Supplies Catalogue ─────────────────────────
    op.create_table("medical_supplies",
        sa.Column("id", UUID, primary_key=True),
        # Names (bilingual)
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_th", sa.String(200)),
        sa.Column("description_en", sa.Text),
        sa.Column("description_th", sa.Text),
        # Classification
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("subcategory", sa.String(50)),
        # Identifiers
        sa.Column("sku", sa.String(50), unique=True),
        sa.Column("catalog_number", sa.String(50)),
        # Physical
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("unit_th", sa.String(30)),
        sa.Column("pack_size", sa.Integer, default=1),
        # Supply chain
        sa.Column("manufacturer", sa.String(200)),
        sa.Column("default_supplier_id", UUID, sa.ForeignKey("suppliers.id")),
        sa.Column("reorder_level", sa.Integer, default=10),
        sa.Column("reorder_quantity", sa.Integer, default=50),
        sa.Column("unit_cost", sa.Numeric(10, 2)),
        # Storage
        sa.Column("storage_condition", sa.String(100)),
        sa.Column("storage_condition_th", sa.String(100)),
        sa.Column("requires_refrigeration", sa.Boolean, default=False),
        sa.Column("requires_sterile", sa.Boolean, default=False),
        # Department
        sa.Column("department", sa.String(30)),
        # Status
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("current_stock", sa.Integer, default=0),
        # Audit
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_medsupply_name", "medical_supplies", ["name_en"])
    op.create_index("ix_medsupply_category", "medical_supplies", ["category"])
    op.create_index("ix_medsupply_dept", "medical_supplies", ["department"])
    op.create_index("ix_medsupply_active", "medical_supplies", ["is_active"])

    # ── Supply Stock Lots ──────────────────────────────────
    op.create_table("supply_stock_lots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("supply_id", UUID, sa.ForeignKey("medical_supplies.id"), nullable=False),
        sa.Column("lot_number", sa.String(50), nullable=False),
        sa.Column("expiry_date", sa.Date),
        sa.Column("initial_quantity", sa.Integer, nullable=False),
        sa.Column("current_quantity", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2)),
        sa.Column("supplier_id", UUID, sa.ForeignKey("suppliers.id")),
        sa.Column("po_number", sa.String(50)),
        sa.Column("invoice_number", sa.String(50)),
        sa.Column("grn_number", sa.String(50)),
        sa.Column("received_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
    )
    op.create_index("ix_supply_lots_supply", "supply_stock_lots", ["supply_id"])
    op.create_index("ix_supply_lots_expiry", "supply_stock_lots", ["expiry_date"])
    op.create_index("ix_supply_lots_lot", "supply_stock_lots", ["lot_number"])
    op.create_check_constraint(
        "ck_supply_lot_qty_non_negative", "supply_stock_lots", "current_quantity >= 0"
    )

    # ── Supply Transactions ────────────────────────────────
    op.create_table("supply_transactions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("supply_id", UUID, sa.ForeignKey("medical_supplies.id"), nullable=False),
        sa.Column("lot_id", UUID, sa.ForeignKey("supply_stock_lots.id")),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer),
        sa.Column("reference_type", sa.String(30)),
        sa.Column("reference_id", UUID),
        sa.Column("department", sa.String(30)),
        sa.Column("reason", sa.Text),
        sa.Column("performed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supply_tx_supply", "supply_transactions", ["supply_id"])
    op.create_index("ix_supply_tx_type", "supply_transactions", ["transaction_type"])
    op.create_index("ix_supply_tx_date", "supply_transactions", ["created_at"])

    # ── Supply Requisitions ────────────────────────────────
    op.create_table("supply_requisitions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("req_number", sa.String(20), unique=True, nullable=False),
        sa.Column("department", sa.String(30), nullable=False),
        sa.Column("requested_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("priority", sa.String(10), default="normal"),
        sa.Column("notes", sa.Text),
        sa.Column("notes_th", sa.Text),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("issued_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("reject_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_req_number", "supply_requisitions", ["req_number"])
    op.create_index("ix_req_status", "supply_requisitions", ["status"])
    op.create_index("ix_req_dept", "supply_requisitions", ["department"])
    op.create_index("ix_req_date", "supply_requisitions", ["created_at"])

    # ── Requisition Items ──────────────────────────────────
    op.create_table("requisition_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("requisition_id", UUID, sa.ForeignKey("supply_requisitions.id"), nullable=False),
        sa.Column("supply_id", UUID, sa.ForeignKey("medical_supplies.id"), nullable=False),
        sa.Column("quantity_requested", sa.Integer, nullable=False),
        sa.Column("quantity_issued", sa.Integer, default=0),
        sa.Column("notes", sa.Text),
    )

    # ── Supply Usage Logs ──────────────────────────────────
    op.create_table("supply_usage_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("supply_id", UUID, sa.ForeignKey("medical_supplies.id"), nullable=False),
        sa.Column("lot_id", UUID, sa.ForeignKey("supply_stock_lots.id")),
        sa.Column("quantity_used", sa.Integer, nullable=False),
        sa.Column("department", sa.String(30), nullable=False),
        sa.Column("procedure_type", sa.String(50)),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("visit_id", UUID),
        sa.Column("used_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_supply", "supply_usage_logs", ["supply_id"])
    op.create_index("ix_usage_dept", "supply_usage_logs", ["department"])
    op.create_index("ix_usage_date", "supply_usage_logs", ["created_at"])


def downgrade():
    op.drop_table("supply_usage_logs")
    op.drop_table("requisition_items")
    op.drop_table("supply_requisitions")
    op.drop_table("supply_transactions")
    op.drop_table("supply_stock_lots")
    op.drop_table("medical_supplies")
    op.drop_table("suppliers")
