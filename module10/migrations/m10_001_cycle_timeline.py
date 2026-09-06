"""FCMS Module 10 — Cycle Plan / Timeline Generator
Tables: cycle_timelines, cycle_timeline_files
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m10_001"
down_revision = "m4_002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cycle_timelines",
        sa.Column("id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("legacy_id", sa.BigInteger(), unique=True),
        sa.Column("patient_id", postgresql.UUID(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("hn", sa.String(30)),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("cycle_type", sa.String(10)),
        sa.Column("protocol", sa.String(50)),
        sa.Column("lmp", sa.Date()),
        sa.Column("day1_date", sa.Date()),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cycle_timelines_legacy_id", "cycle_timelines", ["legacy_id"])
    op.create_index("ix_cycle_timelines_patient_id", "cycle_timelines", ["patient_id"])
    op.create_index("ix_cycle_timelines_hn", "cycle_timelines", ["hn"])
    op.create_index("ix_cycle_timelines_cycle_type", "cycle_timelines", ["cycle_type"])
    op.create_index("ix_cycle_timelines_hn_type", "cycle_timelines", ["hn", "cycle_type"])

    op.create_table(
        "cycle_timeline_files",
        sa.Column("id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("timeline_id", postgresql.UUID(), sa.ForeignKey("cycle_timelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cycle_timeline_files_timeline_id", "cycle_timeline_files", ["timeline_id"])


def downgrade():
    op.drop_table("cycle_timeline_files")
    op.drop_table("cycle_timelines")
