"""
FCMS Module 2 - Database Migration
Creates all Lab Management tables + Import support tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "m2_001_lab_management"
down_revision = None  # Link to Module 1's last migration
branch_labels = None
depends_on = None


def upgrade():
    # ── Lab Test Panels ─────────────────────────────
    op.create_table("lab_test_panels",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_th", sa.String(200)),
        sa.Column("lab_type", sa.String(20), nullable=False),
        sa.Column("specimen_type", sa.String(30), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("normal_range_female_min", sa.Numeric(12, 4)),
        sa.Column("normal_range_female_max", sa.Numeric(12, 4)),
        sa.Column("normal_range_male_min", sa.Numeric(12, 4)),
        sa.Column("normal_range_male_max", sa.Numeric(12, 4)),
        sa.Column("critical_low", sa.Numeric(12, 4)),
        sa.Column("critical_high", sa.Numeric(12, 4)),
        sa.Column("turnaround_hours", sa.Integer, default=24),
        sa.Column("collection_instructions", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Lab Orders ──────────────────────────────────
    op.create_table("lab_orders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("order_number", sa.String(30), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("visit_id", UUID, sa.ForeignKey("visits.id")),
        sa.Column("ordering_physician_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lab_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("priority", sa.String(20), default="routine"),
        sa.Column("clinical_notes", sa.Text),
        sa.Column("diagnosis_code", sa.String(20)),
        sa.Column("ordered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("resulted_at", sa.DateTime(timezone=True)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text),
    )
    op.create_index("ix_lab_orders_patient", "lab_orders", ["patient_id"])
    op.create_index("ix_lab_orders_status", "lab_orders", ["status"])
    op.create_index("ix_lab_orders_ordered_at", "lab_orders", ["ordered_at"])

    # ── Lab Order Items ─────────────────────────────
    op.create_table("lab_order_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("order_id", UUID, sa.ForeignKey("lab_orders.id"), nullable=False),
        sa.Column("test_panel_id", UUID, sa.ForeignKey("lab_test_panels.id"), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
    )

    # ── Lab Specimens ───────────────────────────────
    op.create_table("lab_specimens",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("barcode", sa.String(50), unique=True, nullable=False),
        sa.Column("order_id", UUID, sa.ForeignKey("lab_orders.id"), nullable=False),
        sa.Column("specimen_type", sa.String(30), nullable=False),
        sa.Column("container", sa.String(100)),
        sa.Column("volume_ml", sa.Numeric(6, 2)),
        sa.Column("collected_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("storage_location", sa.String(100)),
        sa.Column("is_rejected", sa.Boolean, default=False),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("notes", sa.Text),
    )

    # ── Lab Results ─────────────────────────────────
    op.create_table("lab_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("order_item_id", UUID, sa.ForeignKey("lab_order_items.id"), nullable=False),
        sa.Column("numeric_value", sa.Numeric(14, 4)),
        sa.Column("text_value", sa.String(500)),
        sa.Column("unit", sa.String(50)),
        sa.Column("flag", sa.String(5)),
        sa.Column("normal_range", sa.String(100)),
        sa.Column("method", sa.String(100)),
        sa.Column("instrument", sa.String(100)),
        sa.Column("resulted_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("resulted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("comment", sa.Text),
    )

    # ── Treatment Cycles ────────────────────────────
    op.create_table("treatment_cycles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("cycle_number", sa.String(30), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("partner_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("cycle_type", sa.String(30)),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("outcome", sa.String(50)),
        sa.Column("physician_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Oocyte Retrievals ───────────────────────────
    op.create_table("oocyte_retrievals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("cycle_id", UUID, sa.ForeignKey("treatment_cycles.id")),
        sa.Column("visit_id", UUID, sa.ForeignKey("visits.id")),
        sa.Column("procedure_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("physician_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("anesthesia_type", sa.String(50)),
        sa.Column("total_follicles_aspirated", sa.Integer),
        sa.Column("total_oocytes_retrieved", sa.Integer),
        sa.Column("mii_count", sa.Integer),
        sa.Column("mi_count", sa.Integer),
        sa.Column("gv_count", sa.Integer),
        sa.Column("degenerated_count", sa.Integer),
        sa.Column("follicular_fluid_ml", sa.Numeric(6, 2)),
        sa.Column("complications", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Oocytes ─────────────────────────────────────
    op.create_table("oocytes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("retrieval_id", UUID, sa.ForeignKey("oocyte_retrievals.id"), nullable=False),
        sa.Column("oocyte_number", sa.Integer, nullable=False),
        sa.Column("maturity_stage", sa.String(10)),
        sa.Column("morphology_score", sa.String(50)),
        sa.Column("zona_pellucida", sa.String(50)),
        sa.Column("perivitelline_space", sa.String(50)),
        sa.Column("polar_body", sa.String(50)),
        sa.Column("cytoplasm", sa.String(50)),
        sa.Column("is_inseminated", sa.Boolean, default=False),
        sa.Column("insemination_method", sa.String(20)),
        sa.Column("insemination_time", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
    )

    # ── Fertilization Records ───────────────────────
    op.create_table("fertilization_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("oocyte_id", UUID, sa.ForeignKey("oocytes.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("check_time", sa.DateTime(timezone=True)),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("pronuclei_count", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Embryos ─────────────────────────────────────
    op.create_table("embryos",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("embryo_code", sa.String(30), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("partner_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("cycle_id", UUID, sa.ForeignKey("treatment_cycles.id")),
        sa.Column("fertilization_record_id", UUID, sa.ForeignKey("fertilization_records.id")),
        sa.Column("current_day", sa.Integer, default=1),
        sa.Column("disposition", sa.String(20)),
        sa.Column("is_pgta_tested", sa.Boolean, default=False),
        sa.Column("pgta_result", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Embryo Assessments ──────────────────────────
    op.create_table("embryo_assessments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("embryo_id", UUID, sa.ForeignKey("embryos.id"), nullable=False),
        sa.Column("assessment_day", sa.Integer, nullable=False),
        sa.Column("assessment_time", sa.DateTime(timezone=True)),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("cell_count", sa.Integer),
        sa.Column("fragmentation_pct", sa.Numeric(5, 2)),
        sa.Column("symmetry", sa.String(30)),
        sa.Column("multinucleation", sa.Boolean, default=False),
        sa.Column("expansion", sa.String(5)),
        sa.Column("icm_grade", sa.String(1)),
        sa.Column("te_grade", sa.String(1)),
        sa.Column("overall_grade", sa.String(20)),
        sa.Column("is_suitable_transfer", sa.Boolean),
        sa.Column("is_suitable_freeze", sa.Boolean),
        sa.Column("image_path", sa.String(500)),
        sa.Column("notes", sa.Text),
    )

    # ── Embryo Cryopreservation ─────────────────────
    op.create_table("embryo_cryopreservations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("embryo_id", UUID, sa.ForeignKey("embryos.id"), nullable=False),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("freeze_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(50)),
        sa.Column("device", sa.String(50)),
        sa.Column("device_label", sa.String(100)),
        sa.Column("tank_id", sa.String(50)),
        sa.Column("canister", sa.String(20)),
        sa.Column("goblet", sa.String(20)),
        sa.Column("position", sa.String(20)),
        sa.Column("cryo_medium", sa.String(100)),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Embryo Warming ──────────────────────────────
    op.create_table("embryo_warmings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("embryo_id", UUID, sa.ForeignKey("embryos.id"), nullable=False),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("warming_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("blastomeres_intact_pct", sa.Numeric(5, 2)),
        sa.Column("post_warm_grade", sa.String(20)),
        sa.Column("warming_medium", sa.String(100)),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Embryo Transfers ────────────────────────────
    op.create_table("embryo_transfers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("embryo_id", UUID, sa.ForeignKey("embryos.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("cycle_id", UUID, sa.ForeignKey("treatment_cycles.id")),
        sa.Column("transfer_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("physician_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transfer_type", sa.String(20)),
        sa.Column("endometrial_thickness", sa.Numeric(4, 1)),
        sa.Column("catheter_type", sa.String(100)),
        sa.Column("difficulty", sa.String(20)),
        sa.Column("ultrasound_guided", sa.Boolean, default=True),
        sa.Column("embryo_position_mm", sa.Numeric(4, 1)),
        sa.Column("outcome_beta_hcg", sa.Numeric(10, 2)),
        sa.Column("outcome_date", sa.Date),
        sa.Column("outcome", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Semen Analyses ──────────────────────────────
    op.create_table("semen_analyses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("analysis_number", sa.String(30), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("order_id", UUID, sa.ForeignKey("lab_orders.id")),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("abstinence_days", sa.Integer),
        sa.Column("collection_method", sa.String(50)),
        sa.Column("collection_location", sa.String(50)),
        sa.Column("analyst_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("verified_by_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("volume_ml", sa.Numeric(5, 2)),
        sa.Column("appearance", sa.String(50)),
        sa.Column("color", sa.String(30)),
        sa.Column("viscosity", sa.String(30)),
        sa.Column("liquefaction_time_min", sa.Integer),
        sa.Column("ph", sa.Numeric(4, 2)),
        sa.Column("concentration_M_per_ml", sa.Numeric(8, 2)),
        sa.Column("total_count_M", sa.Numeric(8, 2)),
        sa.Column("total_motility_pct", sa.Numeric(5, 2)),
        sa.Column("progressive_motility_pct", sa.Numeric(5, 2)),
        sa.Column("non_progressive_pct", sa.Numeric(5, 2)),
        sa.Column("immotile_pct", sa.Numeric(5, 2)),
        sa.Column("normal_morphology_pct", sa.Numeric(5, 2)),
        sa.Column("vitality_pct", sa.Numeric(5, 2)),
        sa.Column("vitality_method", sa.String(50)),
        sa.Column("wbc_per_ml", sa.Numeric(8, 2)),
        sa.Column("rbc_per_ml", sa.Numeric(8, 2)),
        sa.Column("agglutination", sa.String(30)),
        sa.Column("sperm_antibodies", sa.Boolean),
        sa.Column("dfi_pct", sa.Numeric(5, 2)),
        sa.Column("dfi_method", sa.String(50)),
        sa.Column("who_reference_met", sa.Boolean),
        sa.Column("diagnosis", sa.String(100)),
        sa.Column("recommendation", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_semen_patient", "semen_analyses", ["patient_id"])

    # ── Sperm Preparations ──────────────────────────
    op.create_table("sperm_preparations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("semen_analysis_id", UUID, sa.ForeignKey("semen_analyses.id")),
        sa.Column("cycle_id", UUID, sa.ForeignKey("treatment_cycles.id")),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("preparation_method", sa.String(50)),
        sa.Column("prepared_at", sa.DateTime(timezone=True)),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("post_volume_ml", sa.Numeric(5, 2)),
        sa.Column("post_concentration_M_ml", sa.Numeric(8, 2)),
        sa.Column("post_motility_pct", sa.Numeric(5, 2)),
        sa.Column("post_progressive_pct", sa.Numeric(5, 2)),
        sa.Column("post_total_motile_M", sa.Numeric(8, 2)),
        sa.Column("recovery_rate_pct", sa.Numeric(5, 2)),
        sa.Column("used_for", sa.String(30)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Sperm Cryopreservation ──────────────────────
    op.create_table("sperm_cryopreservations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("sample_number", sa.String(30), unique=True, nullable=False),
        sa.Column("freeze_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embryologist_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("num_straws", sa.Integer),
        sa.Column("tank_id", sa.String(50)),
        sa.Column("canister", sa.String(20)),
        sa.Column("goblet", sa.String(20)),
        sa.Column("cryo_medium", sa.String(100)),
        sa.Column("pre_freeze_motility_pct", sa.Numeric(5, 2)),
        sa.Column("post_thaw_motility_pct", sa.Numeric(5, 2)),
        sa.Column("expiry_date", sa.Date),
        sa.Column("consent_form_ref", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Inventory Items (for import) ────────────────
    op.create_table("inventory_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("item_code", sa.String(50), unique=True, nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_th", sa.String(200)),
        sa.Column("category", sa.String(100)),
        sa.Column("unit", sa.String(50)),
        sa.Column("quantity_on_hand", sa.Numeric(12, 2), default=0),
        sa.Column("reorder_level", sa.Numeric(12, 2), default=0),
        sa.Column("unit_price", sa.Numeric(12, 2)),
        sa.Column("supplier", sa.String(200)),
        sa.Column("expiry_date", sa.Date),
        sa.Column("storage_location", sa.String(100)),
        sa.Column("lot_number", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", UUID),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── Patient Import History ──────────────────────
    op.create_table("patient_import_history",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("diagnosis", sa.Text),
        sa.Column("treatment_notes", sa.Text),
        sa.Column("source_file", sa.String(200)),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("imported_by", UUID, sa.ForeignKey("users.id")),
    )

    # ── Seed default fertility test panels ──────────
    op.execute("""
        INSERT INTO lab_test_panels (id, code, name_en, name_th, lab_type, specimen_type, unit,
            normal_range_female_min, normal_range_female_max, normal_range_male_min, normal_range_male_max,
            turnaround_hours, is_active) VALUES
        (gen_random_uuid(), 'FSH', 'Follicle-Stimulating Hormone', 'ฮอร์โมนกระตุ้นรังไข่', 'general', 'blood', 'mIU/mL', 3.5, 12.5, 1.5, 12.4, 4, true),
        (gen_random_uuid(), 'LH', 'Luteinizing Hormone', 'ฮอร์โมนลูทีไนซิง', 'general', 'blood', 'mIU/mL', 2.4, 12.6, 1.7, 8.6, 4, true),
        (gen_random_uuid(), 'E2', 'Estradiol', 'เอสตราไดออล', 'general', 'blood', 'pg/mL', 12.4, 233, NULL, NULL, 4, true),
        (gen_random_uuid(), 'AMH', 'Anti-Müllerian Hormone', 'แอนตี้มูลเลอเรียน', 'general', 'blood', 'ng/mL', 1.0, 3.5, NULL, NULL, 24, true),
        (gen_random_uuid(), 'PRG', 'Progesterone', 'โปรเจสเตอโรน', 'general', 'blood', 'ng/mL', 0.2, 1.5, NULL, NULL, 4, true),
        (gen_random_uuid(), 'PRL', 'Prolactin', 'โปรแลคติน', 'general', 'blood', 'ng/mL', 4.8, 23.3, 4.0, 15.2, 4, true),
        (gen_random_uuid(), 'TSH', 'Thyroid-Stimulating Hormone', 'ฮอร์โมนกระตุ้นไทรอยด์', 'general', 'blood', 'mIU/L', 0.27, 4.2, 0.27, 4.2, 4, true),
        (gen_random_uuid(), 'FT4', 'Free Thyroxine', 'ฟรีไทรอกซิน', 'general', 'blood', 'ng/dL', 0.93, 1.7, 0.93, 1.7, 4, true),
        (gen_random_uuid(), 'TESTO', 'Testosterone', 'เทสโทสเทอโรน', 'general', 'blood', 'ng/dL', 15, 70, 264, 916, 4, true),
        (gen_random_uuid(), 'DHEAS', 'DHEA-Sulfate', 'ดีเอชอีเอ-ซัลเฟต', 'general', 'blood', 'µg/dL', 35, 430, 80, 560, 24, true),
        (gen_random_uuid(), 'BHCG', 'Beta-hCG', 'เบต้า-เอชซีจี', 'general', 'blood', 'mIU/mL', NULL, NULL, NULL, NULL, 2, true),
        (gen_random_uuid(), 'CBC', 'Complete Blood Count', 'ตรวจนับเม็ดเลือด', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 2, true),
        (gen_random_uuid(), 'UA', 'Urinalysis', 'ตรวจปัสสาวะ', 'general', 'urine', NULL, NULL, NULL, NULL, NULL, 2, true),
        (gen_random_uuid(), 'HBSAG', 'Hepatitis B Surface Antigen', 'แอนติเจนไวรัสตับอักเสบบี', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 4, true),
        (gen_random_uuid(), 'ANTIHCV', 'Anti-HCV', 'แอนติบอดีไวรัสตับอักเสบซี', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 4, true),
        (gen_random_uuid(), 'HIV', 'HIV Antibody', 'แอนติบอดีเอชไอวี', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 4, true),
        (gen_random_uuid(), 'VDRL', 'Syphilis Screen', 'ตรวจซิฟิลิส', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 4, true),
        (gen_random_uuid(), 'BG', 'Blood Group & Rh', 'หมู่เลือดและอาร์เอช', 'general', 'blood', NULL, NULL, NULL, NULL, NULL, 2, true),
        (gen_random_uuid(), 'SA', 'Semen Analysis (WHO 2021)', 'วิเคราะห์น้ำอสุจิ', 'andrology', 'semen', NULL, NULL, NULL, NULL, NULL, 4, true),
        (gen_random_uuid(), 'DFI', 'Sperm DNA Fragmentation', 'ดีเอ็นเอสเปิร์ม', 'andrology', 'semen', '%', NULL, NULL, NULL, 25, 48, true)
    """)


def downgrade():
    tables = [
        "patient_import_history", "inventory_items",
        "sperm_cryopreservations", "sperm_preparations",
        "semen_analyses", "embryo_transfers", "embryo_warmings",
        "embryo_cryopreservations", "embryo_assessments",
        "embryos", "fertilization_records", "oocytes",
        "oocyte_retrievals", "treatment_cycles",
        "lab_results", "lab_specimens", "lab_order_items",
        "lab_orders", "lab_test_panels"
    ]
    for t in tables:
        op.drop_table(t)
