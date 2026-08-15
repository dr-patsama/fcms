"""
FCMS Module 4 — Prescription Generator Migration
Adds: drugs.pack_size (round-up dispensing),
      prescriptions.diagnosis_en/th (printed document),
      prescription_items structured sig fields
      (dose_per_time, times_per_day, quantity_needed, sig_en, sig_th).
"""

from alembic import op
import sqlalchemy as sa

revision = "m4_002"
down_revision = "m7_001"
branch_labels = None
depends_on = None


def upgrade():
    # Drug pack size — drives automatic quantity round-up to full packs
    op.add_column("drugs", sa.Column("pack_size", sa.Integer, nullable=True))

    # Diagnosis printed on the prescription document
    op.add_column("prescriptions", sa.Column("diagnosis_en", sa.Text, nullable=True))
    op.add_column("prescriptions", sa.Column("diagnosis_th", sa.Text, nullable=True))

    # Structured sig on prescription items
    op.add_column("prescription_items", sa.Column("quantity_needed", sa.Integer, nullable=True))
    op.add_column("prescription_items", sa.Column("dose_per_time", sa.Numeric(6, 2), nullable=True))
    op.add_column("prescription_items", sa.Column("times_per_day", sa.Integer, nullable=True))
    op.add_column("prescription_items", sa.Column("sig_en", sa.Text, nullable=True))
    op.add_column("prescription_items", sa.Column("sig_th", sa.Text, nullable=True))


def downgrade():
    op.drop_column("prescription_items", "sig_th")
    op.drop_column("prescription_items", "sig_en")
    op.drop_column("prescription_items", "times_per_day")
    op.drop_column("prescription_items", "dose_per_time")
    op.drop_column("prescription_items", "quantity_needed")
    op.drop_column("prescriptions", "diagnosis_th")
    op.drop_column("prescriptions", "diagnosis_en")
    op.drop_column("drugs", "pack_size")
