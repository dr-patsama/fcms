"""
FCMS Module 1 - Migration: Patient Demographics v2
Adds Thai-specific fields, structured address, PDPA consent columns,
emergency contact relation, and missing search indexes.

Applies on top of m1_001_emr_foundation — does not recreate any tables.
"""

from alembic import op
import sqlalchemy as sa

revision      = "m1_002_patient_demographics_v2"
down_revision = "m1_001_emr_foundation"
branch_labels = None
depends_on    = None


def upgrade():
    # ── Name (bilingual prefixes + nicknames) ────────────────
    op.add_column("patients", sa.Column("prefix_en",  sa.String(20)))   # Mr. / Mrs. / Miss / Ms. / Dr. / Prof.
    op.add_column("patients", sa.Column("prefix_th",  sa.String(20)))   # นาย / นาง / นางสาว / ดร. / ศ.
    op.add_column("patients", sa.Column("nickname_en", sa.String(50)))
    op.add_column("patients", sa.Column("nickname_th", sa.String(50)))

    # ── Demographics ─────────────────────────────────────────
    op.add_column("patients", sa.Column("religion",           sa.String(30)))   # Buddhist | Christian | Muslim | Other
    op.add_column("patients", sa.Column("preferred_language", sa.String(5),  server_default="th"))  # en | th

    # ── Contact ───────────────────────────────────────────────
    op.add_column("patients", sa.Column("line_id", sa.String(50)))  # LINE app — primary messaging in Thailand

    # ── Structured Thai address ───────────────────────────────
    # Existing `address` (Text) is kept for free-text / international addresses
    op.add_column("patients", sa.Column("subdistrict", sa.String(100)))  # แขวง / ตำบล
    op.add_column("patients", sa.Column("district",    sa.String(100)))  # เขต / อำเภอ
    op.add_column("patients", sa.Column("province",    sa.String(100)))  # จังหวัด
    op.add_column("patients", sa.Column("postal_code", sa.String(10)))
    op.add_column("patients", sa.Column("country",     sa.String(50), server_default="Thailand"))

    # ── Emergency contact relation ────────────────────────────
    op.add_column("patients", sa.Column("emergency_contact_relation", sa.String(50)))  # spouse | parent | sibling | child | other

    # ── PDPA compliance ───────────────────────────────────────
    # Thai Personal Data Protection Act requires recorded consent for health data processing
    op.add_column("patients", sa.Column("pdpa_consented_at",    sa.DateTime(timezone=True)))
    op.add_column("patients", sa.Column("pdpa_consent_version", sa.String(10)))  # e.g. "v1.0"

    # ── New search indexes ────────────────────────────────────
    op.create_index("ix_patients_name_th", "patients", ["last_name_th", "first_name_th"])
    op.create_index("ix_patients_email",   "patients", ["email"])
    op.create_index("ix_patients_line_id", "patients", ["line_id"])


def downgrade():
    # Indexes first
    op.drop_index("ix_patients_line_id", table_name="patients")
    op.drop_index("ix_patients_email",   table_name="patients")
    op.drop_index("ix_patients_name_th", table_name="patients")

    # PDPA
    op.drop_column("patients", "pdpa_consent_version")
    op.drop_column("patients", "pdpa_consented_at")

    # Emergency contact
    op.drop_column("patients", "emergency_contact_relation")

    # Address
    op.drop_column("patients", "country")
    op.drop_column("patients", "postal_code")
    op.drop_column("patients", "province")
    op.drop_column("patients", "district")
    op.drop_column("patients", "subdistrict")

    # Contact
    op.drop_column("patients", "line_id")

    # Demographics
    op.drop_column("patients", "preferred_language")
    op.drop_column("patients", "religion")

    # Name
    op.drop_column("patients", "nickname_th")
    op.drop_column("patients", "nickname_en")
    op.drop_column("patients", "prefix_th")
    op.drop_column("patients", "prefix_en")
