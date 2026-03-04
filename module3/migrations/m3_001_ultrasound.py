"""
FCMS Module 3 — Ultrasound Database Migration
Tables: dicom_studies, dicom_series, dicom_instances,
        ultrasound_measurements, ultrasound_follicles, ultrasound_reports
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "m3_001"
down_revision = "m2_001_lab_management"
branch_labels = None
depends_on = None


def upgrade():
    # ── DICOM Studies (linked to Orthanc) ───────────────
    op.create_table("dicom_studies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("orthanc_id", sa.String(64), unique=True, nullable=False),
        sa.Column("study_instance_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("cycle_id", UUID),  # FK to treatment_cycles when Module 10 is built
        sa.Column("study_date", sa.Date),
        sa.Column("study_time", sa.String(20)),
        sa.Column("study_description", sa.String(200)),
        sa.Column("accession_number", sa.String(64)),
        sa.Column("referring_physician", sa.String(200)),
        sa.Column("institution_name", sa.String(200)),
        sa.Column("modality", sa.String(10), default="US"),
        sa.Column("num_series", sa.Integer, default=0),
        sa.Column("num_instances", sa.Integer, default=0),
        sa.Column("matched_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("matched_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), default="unmatched"),  # unmatched | matched | reported
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_dicom_studies_patient", "dicom_studies", ["patient_id"])
    op.create_index("ix_dicom_studies_date", "dicom_studies", ["study_date"])
    op.create_index("ix_dicom_studies_status", "dicom_studies", ["status"])

    # ── DICOM Series ────────────────────────────────────
    op.create_table("dicom_series",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("orthanc_id", sa.String(64), unique=True, nullable=False),
        sa.Column("study_id", UUID, sa.ForeignKey("dicom_studies.id"), nullable=False),
        sa.Column("series_instance_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("series_number", sa.Integer),
        sa.Column("series_description", sa.String(200)),
        sa.Column("modality", sa.String(10)),
        sa.Column("num_instances", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Ultrasound Measurements ─────────────────────────
    op.create_table("ultrasound_measurements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("study_id", UUID, sa.ForeignKey("dicom_studies.id")),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("cycle_id", UUID),
        sa.Column("exam_type", sa.String(30), nullable=False),
        sa.Column("exam_date", sa.Date, nullable=False),
        sa.Column("measured_by", UUID, sa.ForeignKey("users.id")),

        # Endometrium
        sa.Column("endometrial_thickness_mm", sa.Numeric(5, 1)),
        sa.Column("endometrial_pattern", sa.String(30)),
        sa.Column("endometrial_echogenicity", sa.String(30)),

        # Right ovary
        sa.Column("right_ovary_length_mm", sa.Numeric(5, 1)),
        sa.Column("right_ovary_width_mm", sa.Numeric(5, 1)),
        sa.Column("right_ovary_height_mm", sa.Numeric(5, 1)),
        sa.Column("right_ovary_volume_ml", sa.Numeric(6, 1)),
        sa.Column("right_afc", sa.Integer),

        # Left ovary
        sa.Column("left_ovary_length_mm", sa.Numeric(5, 1)),
        sa.Column("left_ovary_width_mm", sa.Numeric(5, 1)),
        sa.Column("left_ovary_height_mm", sa.Numeric(5, 1)),
        sa.Column("left_ovary_volume_ml", sa.Numeric(6, 1)),
        sa.Column("left_afc", sa.Integer),

        # Computed
        sa.Column("total_afc", sa.Integer),
        sa.Column("lead_follicle_mm", sa.Numeric(5, 1)),
        sa.Column("follicles_gte_10mm", sa.Integer, default=0),
        sa.Column("follicles_gte_14mm", sa.Integer, default=0),
        sa.Column("follicles_gte_17mm", sa.Integer, default=0),

        # Uterus
        sa.Column("uterus_length_mm", sa.Numeric(5, 1)),
        sa.Column("uterus_width_mm", sa.Numeric(5, 1)),
        sa.Column("uterus_ap_mm", sa.Numeric(5, 1)),
        sa.Column("uterus_position", sa.String(20)),

        # Other
        sa.Column("free_fluid", sa.String(20)),
        sa.Column("adnexa_notes", sa.Text),
        sa.Column("impression", sa.Text),
        sa.Column("plan", sa.Text),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_us_meas_patient", "ultrasound_measurements", ["patient_id"])
    op.create_index("ix_us_meas_date", "ultrasound_measurements", ["exam_date"])
    op.create_index("ix_us_meas_cycle", "ultrasound_measurements", ["cycle_id"])

    # ── Follicle Measurements (individual) ──────────────
    op.create_table("ultrasound_follicles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("measurement_id", UUID, sa.ForeignKey("ultrasound_measurements.id"), nullable=False),
        sa.Column("side", sa.String(5), nullable=False),  # right | left
        sa.Column("diameter_mm", sa.Numeric(5, 1), nullable=False),
        sa.Column("diameter_2_mm", sa.Numeric(5, 1)),  # second measurement for mean
        sa.Column("mean_diameter_mm", sa.Numeric(5, 1)),
        sa.Column("volume_ml", sa.Numeric(6, 1)),
        sa.Column("follicle_number", sa.Integer),  # ordering
        sa.Column("notes", sa.String(200)),
    )

    # ── Ultrasound Reports ──────────────────────────────
    op.create_table("ultrasound_reports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("measurement_id", UUID, sa.ForeignKey("ultrasound_measurements.id")),
        sa.Column("study_id", UUID, sa.ForeignKey("dicom_studies.id")),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("cycle_id", UUID),
        sa.Column("template", sa.String(30)),
        sa.Column("findings_json", sa.Text),  # JSON blob of structured findings
        sa.Column("impression", sa.Text),
        sa.Column("plan", sa.Text),
        sa.Column("key_image_ids", sa.Text),  # comma-separated Orthanc instance IDs
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("signed", sa.Boolean, default=False),
        sa.Column("signed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("pdf_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_us_reports_patient", "ultrasound_reports", ["patient_id"])


def downgrade():
    op.drop_table("ultrasound_reports")
    op.drop_table("ultrasound_follicles")
    op.drop_table("ultrasound_measurements")
    op.drop_table("dicom_series")
    op.drop_table("dicom_studies")
