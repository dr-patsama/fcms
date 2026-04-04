"""
FCMS Module 6 — CRM Database Migration
Tables: appointments, virtual_consultations, appointment_reminders,
        communication_logs, patient_contact_preferences,
        provider_schedules, schedule_exceptions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "m6_001"
down_revision = "m5_001"
branch_labels = None
depends_on = None


def upgrade():
    # ── Appointments ───────────────────────────────────────
    op.create_table("appointments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("booking_number", sa.String(20), unique=True, nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_date", sa.Date, nullable=False),
        sa.Column("appointment_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time),
        sa.Column("duration_minutes", sa.Integer, default=30),
        sa.Column("appointment_type", sa.String(30), nullable=False),
        sa.Column("appointment_type_th", sa.String(50)),
        sa.Column("department", sa.String(30)),
        sa.Column("room", sa.String(50)),
        sa.Column("provider_id", UUID, sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(20), default="scheduled"),
        sa.Column("priority", sa.String(10), default="normal"),
        sa.Column("booking_source", sa.String(20), default="staff"),
        sa.Column("chief_complaint", sa.Text),
        sa.Column("chief_complaint_th", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("notes_th", sa.Text),
        sa.Column("preparation_instructions", sa.Text),
        sa.Column("preparation_instructions_th", sa.Text),
        sa.Column("cancelled_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text),
        sa.Column("rescheduled_from", UUID, sa.ForeignKey("appointments.id")),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_appt_patient", "appointments", ["patient_id"])
    op.create_index("ix_appt_date", "appointments", ["appointment_date"])
    op.create_index("ix_appt_type", "appointments", ["appointment_type"])
    op.create_index("ix_appt_status", "appointments", ["status"])
    op.create_index("ix_appt_provider", "appointments", ["provider_id"])

    # ── Virtual Consultations ──────────────────────────────
    op.create_table("virtual_consultations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("appointment_id", UUID, sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("provider_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_token", sa.String(200), unique=True),
        sa.Column("room_url", sa.String(500)),
        sa.Column("platform", sa.String(30), default="internal"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True)),
        sa.Column("actual_start", sa.DateTime(timezone=True)),
        sa.Column("actual_end", sa.DateTime(timezone=True)),
        sa.Column("duration_minutes", sa.Integer),
        sa.Column("status", sa.String(20), default="scheduled"),
        sa.Column("consultation_notes", sa.Text),
        sa.Column("consultation_notes_th", sa.Text),
        sa.Column("diagnosis", sa.Text),
        sa.Column("follow_up_plan", sa.Text),
        sa.Column("follow_up_plan_th", sa.Text),
        sa.Column("attachments", JSON),
        sa.Column("connection_quality", sa.String(20)),
        sa.Column("patient_satisfaction", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_vc_appt", "virtual_consultations", ["appointment_id"])
    op.create_index("ix_vc_patient", "virtual_consultations", ["patient_id"])

    # ── Appointment Reminders ──────────────────────────────
    op.create_table("appointment_reminders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("appointment_id", UUID, sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger_offset", sa.String(20)),
        sa.Column("template_key", sa.String(50)),
        sa.Column("message_en", sa.Text),
        sa.Column("message_th", sa.Text),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text),
        sa.Column("external_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reminder_appt", "appointment_reminders", ["appointment_id"])
    op.create_index("ix_reminder_status", "appointment_reminders", ["status"])

    # ── Communication Logs ─────────────────────────────────
    op.create_table("communication_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), default="outbound"),
        sa.Column("subject", sa.String(200)),
        sa.Column("message_en", sa.Text),
        sa.Column("message_th", sa.Text),
        sa.Column("template_key", sa.String(50)),
        sa.Column("recipient", sa.String(200)),
        sa.Column("status", sa.String(20), default="sent"),
        sa.Column("external_id", sa.String(100)),
        sa.Column("reference_type", sa.String(30)),
        sa.Column("reference_id", UUID),
        sa.Column("sent_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_comms_patient", "communication_logs", ["patient_id"])
    op.create_index("ix_comms_channel", "communication_logs", ["channel"])
    op.create_index("ix_comms_date", "communication_logs", ["created_at"])

    # ── Patient Contact Preferences ────────────────────────
    op.create_table("patient_contact_preferences",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("patient_id", UUID, sa.ForeignKey("patients.id"), unique=True, nullable=False),
        sa.Column("phone_primary", sa.String(20)),
        sa.Column("phone_secondary", sa.String(20)),
        sa.Column("email", sa.String(100)),
        sa.Column("line_id", sa.String(50)),
        sa.Column("whatsapp_number", sa.String(20)),
        sa.Column("preferred_channel", sa.String(20), default="line"),
        sa.Column("preferred_language", sa.String(5), default="th"),
        sa.Column("preferred_time", sa.String(20), default="anytime"),
        sa.Column("consent_sms", sa.Boolean, default=True),
        sa.Column("consent_line", sa.Boolean, default=True),
        sa.Column("consent_email", sa.Boolean, default=True),
        sa.Column("consent_whatsapp", sa.Boolean, default=True),
        sa.Column("consent_marketing", sa.Boolean, default=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Provider Schedules ─────────────────────────────────
    op.create_table("provider_schedules",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("provider_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("slot_duration", sa.Integer, default=30),
        sa.Column("max_patients", sa.Integer, default=1),
        sa.Column("appointment_types", JSON),
        sa.Column("location", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_until", sa.Date),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sched_provider", "provider_schedules", ["provider_id"])

    # ── Schedule Exceptions ────────────────────────────────
    op.create_table("schedule_exceptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("provider_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exception_date", sa.Date, nullable=False),
        sa.Column("exception_type", sa.String(20), nullable=False),
        sa.Column("start_time", sa.Time),
        sa.Column("end_time", sa.Time),
        sa.Column("reason", sa.Text),
        sa.Column("reason_th", sa.Text),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exc_provider", "schedule_exceptions", ["provider_id"])
    op.create_index("ix_exc_date", "schedule_exceptions", ["exception_date"])


def downgrade():
    op.drop_table("schedule_exceptions")
    op.drop_table("provider_schedules")
    op.drop_table("patient_contact_preferences")
    op.drop_table("communication_logs")
    op.drop_table("appointment_reminders")
    op.drop_table("virtual_consultations")
    op.drop_table("appointments")
