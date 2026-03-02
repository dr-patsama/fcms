"""
FCMS Module 1 - Database Migration
Creates all EMR foundation tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "m1_001_emr_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── Users ───────────────────────────────────────
    op.create_table("users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("first_name_en", sa.String(100), nullable=False),
        sa.Column("last_name_en", sa.String(100), nullable=False),
        sa.Column("first_name_th", sa.String(100)),
        sa.Column("last_name_th", sa.String(100)),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("license_number", sa.String(50)),
        sa.Column("department", sa.String(100)),
        sa.Column("phone", sa.String(20)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_mfa_enabled", sa.Boolean, default=False),
        sa.Column("mfa_secret", sa.String(64)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_count", sa.Integer, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # ── User Sessions ───────────────────────────────
    op.create_table("user_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_jti", sa.String(64), unique=True, nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, default=True),
    )

    # ── Audit Logs ──────────────────────────────────
    op.create_table("audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("module", sa.String(30)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(50)),
        sa.Column("detail", sa.Text),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user", "audit_logs", ["user_id"])
    op.create_index("ix_audit_module", "audit_logs", ["module"])
    op.create_index("ix_audit_created_at", "audit_logs", ["created_at"])

    # ── Patients ────────────────────────────────────
    op.create_table("patients",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hn_number", sa.String(20), unique=True, nullable=False),
        sa.Column("first_name_en", sa.String(100), nullable=False),
        sa.Column("last_name_en", sa.String(100), nullable=False),
        sa.Column("first_name_th", sa.String(100)),
        sa.Column("last_name_th", sa.String(100)),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("gender", sa.String(10)),
        sa.Column("id_number", sa.String(20)),
        sa.Column("id_type", sa.String(20)),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(200)),
        sa.Column("blood_type", sa.String(5)),
        sa.Column("allergies", sa.Text),
        sa.Column("marital_status", sa.String(20)),
        sa.Column("occupation", sa.String(100)),
        sa.Column("nationality", sa.String(50), default="Thai"),
        sa.Column("address", sa.Text),
        sa.Column("emergency_contact_name", sa.String(200)),
        sa.Column("emergency_contact_phone", sa.String(20)),
        sa.Column("referring_doctor", sa.String(200)),
        sa.Column("insurance_provider", sa.String(200)),
        sa.Column("insurance_number", sa.String(50)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_patients_hn", "patients", ["hn_number"])
    op.create_index("ix_patients_name", "patients", ["last_name_en", "first_name_en"])
    op.create_index("ix_patients_id_num", "patients", ["id_number"])
    op.create_index("ix_patients_phone", "patients", ["phone"])

    # ── Medical History ─────────────────────────────
    op.create_table("medical_histories",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("chronic_diseases", JSON, default=[]),
        sa.Column("previous_surgeries", JSON, default=[]),
        sa.Column("current_medications", JSON, default=[]),
        sa.Column("drug_allergies", JSON, default=[]),
        sa.Column("family_history", JSON, default=[]),
        sa.Column("smoking_status", sa.String(20)),
        sa.Column("alcohol_use", sa.String(20)),
        sa.Column("exercise_frequency", sa.String(30)),
        sa.Column("notes", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── Fertility History ───────────────────────────
    op.create_table("fertility_histories",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("gravida", sa.Integer, default=0),
        sa.Column("para", sa.Integer, default=0),
        sa.Column("abortion", sa.Integer, default=0),
        sa.Column("living_children", sa.Integer, default=0),
        sa.Column("menarche_age", sa.Integer),
        sa.Column("cycle_length_days", sa.Integer),
        sa.Column("cycle_regularity", sa.String(20)),
        sa.Column("last_menstrual_period", sa.Date),
        sa.Column("previous_contraception", JSON, default=[]),
        sa.Column("infertility_duration_months", sa.Integer),
        sa.Column("infertility_type", sa.String(20)),
        sa.Column("previous_treatments", JSON, default=[]),
        sa.Column("partner_id", UUID, sa.ForeignKey("patients.id")),
        sa.Column("notes", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── Visits ──────────────────────────────────────
    op.create_table("visits",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("visit_number", sa.String(20), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("physician_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("visit_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("visit_type", sa.String(30)),
        sa.Column("chief_complaint", sa.Text),
        sa.Column("status", sa.String(20), default="checked_in"),
        sa.Column("checkout_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_visits_patient", "visits", ["patient_id"])
    op.create_index("ix_visits_date", "visits", ["visit_date"])
    op.create_index("ix_visits_status", "visits", ["status"])

    # ── SOAP Notes ──────────────────────────────────
    op.create_table("soap_notes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("visit_id", UUID, sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subjective", sa.Text),
        sa.Column("objective", sa.Text),
        sa.Column("assessment", sa.Text),
        sa.Column("plan", sa.Text),
        sa.Column("addendum", sa.Text),
        sa.Column("is_signed", sa.Boolean, default=False),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ── Visit Diagnoses (ICD-10) ────────────────────
    op.create_table("visit_diagnoses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("visit_id", UUID, sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("icd10_code", sa.String(10), nullable=False),
        sa.Column("description", sa.String(300)),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("notes", sa.Text),
    )

    # ── Consent Forms ───────────────────────────────
    op.create_table("consent_forms",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(10)),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("witness_name", sa.String(200)),
        sa.Column("document_path", sa.String(500)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Seed admin user ─────────────────────────────
    op.execute("""
        INSERT INTO users (id, email, password_hash, first_name_en, last_name_en, role, is_active)
        VALUES (
            gen_random_uuid(),
            'admin@fcms.clinic',
            '$2b$12$LJ3m4ys5qGBfMkH.QORXnO8pyN9JhFHvXJEDlGq3G2v5qRuYWTqDi',
            'System', 'Admin', 'admin', true
        )
    """)
    # Default password: FCMSadmin2026!


def downgrade():
    tables = [
        "consent_forms", "visit_diagnoses", "soap_notes", "visits",
        "fertility_histories", "medical_histories", "patients",
        "audit_logs", "user_sessions", "users"
    ]
    for t in tables:
        op.drop_table(t)
