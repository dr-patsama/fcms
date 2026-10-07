"""FCMS Journey layer (j1_001) — the patient-journey spine adapted from Binflux Infans.

New tables: treatment_packages, cycle_days, cycle_medications, cycle_medication_doses,
cycle_monitoring, cycle_events, cycle_outcomes, consent_templates, cycle_consents,
lab_tasks, lab_items, witness_sessions, witness_scans, witness_incidents, embryo_photos,
cryo_storage_terms, patient_accounts, patient_notifications, portal_booking_requests.
Altered: treatment_cycles (+ package/status/dates/flags), appointments (+ cycle_id,
google_event_id, google_synced_at, queue_number).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "j1_001"
down_revision = "m10_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('treatment_packages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name_en', sa.String(length=200), nullable=False),
    sa.Column('name_th', sa.String(length=200), nullable=True),
    sa.Column('cycle_type', sa.String(length=40), nullable=False),
    sa.Column('is_episode', sa.Boolean(), nullable=True),
    sa.Column('anchor', sa.String(length=20), nullable=True),
    sa.Column('default_et_day', sa.Integer(), nullable=True),
    sa.Column('pgt', sa.Boolean(), nullable=True),
    sa.Column('freeze_all', sa.Boolean(), nullable=True),
    sa.Column('medication_template', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('lab_events', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('consents', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('notifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('billing_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('description_en', sa.Text(), nullable=True),
    sa.Column('description_th', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('cycle_days',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('calendar_date', sa.Date(), nullable=False),
    sa.Column('day_index', sa.Integer(), nullable=False),
    sa.Column('stimulation_day', sa.Integer(), nullable=True),
    sa.Column('lab_day', sa.Integer(), nullable=True),
    sa.Column('label_en', sa.String(length=120), nullable=True),
    sa.Column('label_th', sa.String(length=120), nullable=True),
    sa.Column('appointment_id', sa.UUID(), nullable=True),
    sa.Column('is_visit', sa.Boolean(), nullable=True),
    sa.Column('is_procedure', sa.Boolean(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id', 'calendar_date', name='uq_cycle_day')
    )
    op.create_table('cycle_medications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('drug_id', sa.UUID(), nullable=True),
    sa.Column('drug_code', sa.String(length=50), nullable=True),
    sa.Column('drug_en', sa.String(length=200), nullable=False),
    sa.Column('drug_th', sa.String(length=200), nullable=True),
    sa.Column('dose', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('route', sa.String(length=20), nullable=True),
    sa.Column('slot', sa.String(length=10), nullable=True),
    sa.Column('start_day_index', sa.Integer(), nullable=False),
    sa.Column('end_day_index', sa.Integer(), nullable=False),
    sa.Column('instructions_en', sa.Text(), nullable=True),
    sa.Column('instructions_th', sa.Text(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['drug_id'], ['drugs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cycle_medication_doses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('medication_id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('calendar_date', sa.Date(), nullable=False),
    sa.Column('day_index', sa.Integer(), nullable=False),
    sa.Column('slot', sa.String(length=10), nullable=True),
    sa.Column('dose', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('taken_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('taken_source', sa.String(length=10), nullable=True),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['medication_id'], ['cycle_medications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('medication_id', 'calendar_date', 'slot', name='uq_dose_day_slot')
    )
    op.create_table('cycle_monitoring',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('calendar_date', sa.Date(), nullable=False),
    sa.Column('day_index', sa.Integer(), nullable=True),
    sa.Column('visit_id', sa.UUID(), nullable=True),
    sa.Column('follicles_right', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('follicles_left', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('endometrium_mm', sa.Numeric(precision=4, scale=1), nullable=True),
    sa.Column('endometrium_pattern', sa.String(length=20), nullable=True),
    sa.Column('e2', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('lh', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('p4', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('fsh', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('hcg', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('orthanc_study_uid', sa.String(length=120), nullable=True),
    sa.Column('decision_en', sa.Text(), nullable=True),
    sa.Column('decision_th', sa.Text(), nullable=True),
    sa.Column('recorded_by', sa.UUID(), nullable=True),
    sa.Column('released_to_patient', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['visit_id'], ['visits.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id', 'calendar_date', name='uq_monitoring_day')
    )
    op.create_table('cycle_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=True),
    sa.Column('patient_id', sa.UUID(), nullable=True),
    sa.Column('type', sa.String(length=60), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('handlers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cycle_outcomes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('cancelled_before_opu', sa.Boolean(), nullable=True),
    sa.Column('cancel_reason', sa.String(length=200), nullable=True),
    sa.Column('hcg_date', sa.Date(), nullable=True),
    sa.Column('hcg_value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('hcg_positive', sa.Boolean(), nullable=True),
    sa.Column('biochemical_only', sa.Boolean(), nullable=True),
    sa.Column('clinical_pregnancy', sa.Boolean(), nullable=True),
    sa.Column('gestational_sacs', sa.Integer(), nullable=True),
    sa.Column('fetal_hearts', sa.Integer(), nullable=True),
    sa.Column('ongoing_pregnancy', sa.Boolean(), nullable=True),
    sa.Column('miscarriage', sa.Boolean(), nullable=True),
    sa.Column('ectopic', sa.Boolean(), nullable=True),
    sa.Column('live_birth', sa.Boolean(), nullable=True),
    sa.Column('delivery_date', sa.Date(), nullable=True),
    sa.Column('babies', sa.Integer(), nullable=True),
    sa.Column('birth_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ohss_grade', sa.String(length=20), nullable=True),
    sa.Column('opu_complication', sa.String(length=200), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('recorded_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id')
    )
    op.create_table('consent_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=False),
    sa.Column('title_th', sa.String(length=200), nullable=True),
    sa.Column('body_en', sa.Text(), nullable=True),
    sa.Column('body_th', sa.Text(), nullable=True),
    sa.Column('version', sa.String(length=10), nullable=True),
    sa.Column('signer', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('cycle_consents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('consent_type', sa.String(length=50), nullable=False),
    sa.Column('template_id', sa.UUID(), nullable=True),
    sa.Column('template_version', sa.String(length=10), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signed_by_patient_id', sa.UUID(), nullable=True),
    sa.Column('signed_channel', sa.String(length=20), nullable=True),
    sa.Column('signature_path', sa.String(length=500), nullable=True),
    sa.Column('document_path', sa.String(length=500), nullable=True),
    sa.Column('document_hash', sa.String(length=64), nullable=True),
    sa.Column('witness_user_id', sa.UUID(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('consent_form_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['consent_form_id'], ['consent_forms.id'], ),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['signed_by_patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['template_id'], ['consent_templates.id'], ),
    sa.ForeignKeyConstraint(['witness_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cycle_id', 'consent_type', name='uq_cycle_consent')
    )
    op.create_table('lab_tasks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=40), nullable=False),
    sa.Column('task_type', sa.String(length=40), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=False),
    sa.Column('title_th', sa.String(length=200), nullable=True),
    sa.Column('lab_day', sa.Integer(), nullable=True),
    sa.Column('scheduled_date', sa.Date(), nullable=False),
    sa.Column('scheduled_time', sa.Time(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('requires_witness', sa.Boolean(), nullable=True),
    sa.Column('items_required', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('write_back', sa.String(length=60), nullable=True),
    sa.Column('required_consents', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('physician_order', sa.String(length=200), nullable=True),
    sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('done_by', sa.UUID(), nullable=True),
    sa.Column('failed_reason', sa.Text(), nullable=True),
    sa.Column('witness_session_id', sa.UUID(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['done_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lab_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('label_code', sa.String(length=40), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('item_type', sa.String(length=30), nullable=False),
    sa.Column('lab_day', sa.Integer(), nullable=True),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('lab_task_id', sa.UUID(), nullable=True),
    sa.Column('reference_table', sa.String(length=40), nullable=True),
    sa.Column('reference_id', sa.UUID(), nullable=True),
    sa.Column('printed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('printed_by', sa.UUID(), nullable=True),
    sa.Column('print_count', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['lab_task_id'], ['lab_tasks.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['printed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('label_code')
    )
    op.create_table('witness_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lab_task_id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('second_user_id', sa.UUID(), nullable=True),
    sa.Column('device', sa.String(length=120), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('result', sa.String(length=20), nullable=True),
    sa.Column('items_expected', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('items_scanned', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error_count', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['lab_task_id'], ['lab_tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['second_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('witness_scans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('raw_payload', sa.String(length=200), nullable=False),
    sa.Column('label_code', sa.String(length=40), nullable=True),
    sa.Column('item_type', sa.String(length=30), nullable=True),
    sa.Column('lab_item_id', sa.UUID(), nullable=True),
    sa.Column('resolved_cycle_id', sa.UUID(), nullable=True),
    sa.Column('resolved_patient_id', sa.UUID(), nullable=True),
    sa.Column('matched', sa.Boolean(), nullable=True),
    sa.Column('message', sa.String(length=200), nullable=True),
    sa.Column('scanned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['lab_item_id'], ['lab_items.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['witness_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('witness_incidents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('cycle_id', sa.UUID(), nullable=True),
    sa.Column('lab_task_id', sa.UUID(), nullable=True),
    sa.Column('severity', sa.String(length=10), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('resolved_by', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolution', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ),
    sa.ForeignKeyConstraint(['lab_task_id'], ['lab_tasks.id'], ),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['witness_sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('embryo_photos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=False),
    sa.Column('embryo_id', sa.UUID(), nullable=True),
    sa.Column('oocyte_id', sa.UUID(), nullable=True),
    sa.Column('lab_day', sa.Integer(), nullable=True),
    sa.Column('path', sa.String(length=500), nullable=False),
    sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
    sa.Column('caption_en', sa.String(length=200), nullable=True),
    sa.Column('caption_th', sa.String(length=200), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=True),
    sa.Column('taken_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('taken_by', sa.UUID(), nullable=True),
    sa.Column('released_to_patient', sa.Boolean(), nullable=True),
    sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('released_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['embryo_id'], ['embryos.id'], ),
    sa.ForeignKeyConstraint(['oocyte_id'], ['oocytes.id'], ),
    sa.ForeignKeyConstraint(['released_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['taken_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cryo_storage_terms',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=True),
    sa.Column('content_type', sa.String(length=20), nullable=False),
    sa.Column('reference_table', sa.String(length=40), nullable=True),
    sa.Column('reference_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('device_count', sa.Integer(), nullable=True),
    sa.Column('stored_at', sa.Date(), nullable=False),
    sa.Column('paid_until', sa.Date(), nullable=False),
    sa.Column('term_months', sa.Integer(), nullable=True),
    sa.Column('annual_fee', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('last_reminder_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reminders_sent', sa.Integer(), nullable=True),
    sa.Column('invoice_id', sa.UUID(), nullable=True),
    sa.Column('consent_status', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('patient_accounts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('line_user_id', sa.String(length=64), nullable=True),
    sa.Column('line_display_name', sa.String(length=120), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('otp_hash', sa.String(length=200), nullable=True),
    sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('otp_attempts', sa.Integer(), nullable=True),
    sa.Column('pin_hash', sa.String(length=200), nullable=True),
    sa.Column('language', sa.String(length=5), nullable=True),
    sa.Column('push_enabled', sa.Boolean(), nullable=True),
    sa.Column('web_push_subscription', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('line_user_id'),
    sa.UniqueConstraint('patient_id')
    )
    op.create_table('patient_notifications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('cycle_id', sa.UUID(), nullable=True),
    sa.Column('type', sa.String(length=60), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=True),
    sa.Column('title_th', sa.String(length=200), nullable=True),
    sa.Column('body_en', sa.Text(), nullable=True),
    sa.Column('body_th', sa.Text(), nullable=True),
    sa.Column('action_url', sa.String(length=300), nullable=True),
    sa.Column('channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['cycle_id'], ['treatment_cycles.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('portal_booking_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('requested_date', sa.Date(), nullable=False),
    sa.Column('requested_time', sa.Time(), nullable=True),
    sa.Column('appointment_type', sa.String(length=30), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('appointment_id', sa.UUID(), nullable=True),
    sa.Column('handled_by', sa.UUID(), nullable=True),
    sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
    sa.ForeignKeyConstraint(['handled_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_accounts_phone'), 'patient_accounts', ['phone'], unique=False)
    op.create_index(op.f('ix_cryo_storage_terms_cycle_id'), 'cryo_storage_terms', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cryo_storage_terms_paid_until'), 'cryo_storage_terms', ['paid_until'], unique=False)
    op.create_index(op.f('ix_cryo_storage_terms_patient_id'), 'cryo_storage_terms', ['patient_id'], unique=False)
    op.create_index(op.f('ix_cryo_storage_terms_status'), 'cryo_storage_terms', ['status'], unique=False)
    op.create_index(op.f('ix_cycle_consents_cycle_id'), 'cycle_consents', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_events_created_at'), 'cycle_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_cycle_events_cycle_id'), 'cycle_events', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_events_patient_id'), 'cycle_events', ['patient_id'], unique=False)
    op.create_index(op.f('ix_cycle_events_type'), 'cycle_events', ['type'], unique=False)
    op.create_index(op.f('ix_cycle_medications_cycle_id'), 'cycle_medications', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_monitoring_cycle_id'), 'cycle_monitoring', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_outcomes_patient_id'), 'cycle_outcomes', ['patient_id'], unique=False)
    op.create_index(op.f('ix_lab_tasks_cycle_id'), 'lab_tasks', ['cycle_id'], unique=False)
    op.create_index('ix_lab_tasks_date_status', 'lab_tasks', ['scheduled_date', 'status'], unique=False)
    op.create_index(op.f('ix_lab_tasks_patient_id'), 'lab_tasks', ['patient_id'], unique=False)
    op.create_index(op.f('ix_lab_tasks_scheduled_date'), 'lab_tasks', ['scheduled_date'], unique=False)
    op.create_index(op.f('ix_lab_tasks_status'), 'lab_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_patient_notifications_created_at'), 'patient_notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_patient_notifications_patient_id'), 'patient_notifications', ['patient_id'], unique=False)
    op.create_index(op.f('ix_cycle_days_cycle_id'), 'cycle_days', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_medication_doses_calendar_date'), 'cycle_medication_doses', ['calendar_date'], unique=False)
    op.create_index(op.f('ix_cycle_medication_doses_cycle_id'), 'cycle_medication_doses', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_cycle_medication_doses_medication_id'), 'cycle_medication_doses', ['medication_id'], unique=False)
    op.create_index(op.f('ix_lab_items_cycle_id'), 'lab_items', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_lab_items_patient_id'), 'lab_items', ['patient_id'], unique=False)
    op.create_index(op.f('ix_portal_booking_requests_patient_id'), 'portal_booking_requests', ['patient_id'], unique=False)
    op.create_index(op.f('ix_witness_sessions_cycle_id'), 'witness_sessions', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_witness_sessions_lab_task_id'), 'witness_sessions', ['lab_task_id'], unique=False)
    op.create_index(op.f('ix_witness_incidents_cycle_id'), 'witness_incidents', ['cycle_id'], unique=False)
    op.create_index(op.f('ix_witness_incidents_session_id'), 'witness_incidents', ['session_id'], unique=False)
    op.create_index(op.f('ix_witness_scans_session_id'), 'witness_scans', ['session_id'], unique=False)
    op.create_index(op.f('ix_embryo_photos_cycle_id'), 'embryo_photos', ['cycle_id'], unique=False)
    op.add_column('appointments', sa.Column('cycle_id', sa.UUID(), nullable=True))
    op.add_column('appointments', sa.Column('google_event_id', sa.String(length=120), nullable=True))
    op.add_column('appointments', sa.Column('google_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('queue_number', sa.Integer(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('package_id', sa.UUID(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('status', sa.String(length=30), nullable=True))
    op.add_column('treatment_cycles', sa.Column('medication_start_date', sa.Date(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('d0_date', sa.Date(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('trigger_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('treatment_cycles', sa.Column('planned_et_day', sa.Integer(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('pgt', sa.Boolean(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('freeze_all', sa.Boolean(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('registry_report_status', sa.String(length=20), nullable=True))
    op.add_column('treatment_cycles', sa.Column('timeline_id', sa.UUID(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('physician_order', sa.String(length=200), nullable=True))
    op.add_column('treatment_cycles', sa.Column('plan_published_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('treatment_cycles', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('treatment_cycles', sa.Column('closure_reason', sa.String(length=200), nullable=True))
    op.add_column('treatment_cycles', sa.Column('created_by', sa.UUID(), nullable=True))
    op.add_column('treatment_cycles', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_appointments_cycle_id', 'appointments', 'treatment_cycles', ['cycle_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_treatment_cycles_timeline_id', 'treatment_cycles', 'cycle_timelines', ['timeline_id'], ['id'])
    op.create_foreign_key('fk_treatment_cycles_created_by', 'treatment_cycles', 'users', ['created_by'], ['id'])
    op.create_foreign_key('fk_treatment_cycles_package_id', 'treatment_cycles', 'treatment_packages', ['package_id'], ['id'])
    # Widen Module 2 enum-backed columns so SQLAlchemy Enum *names* fit (latent bug: 'ABNORMAL_1PN' > 10 chars, 'EXPANDED' > 5)
    op.alter_column('fertilization_records', 'status', type_=sa.String(20), existing_type=sa.String(10))
    op.alter_column('embryo_assessments', 'expansion', type_=sa.String(12), existing_type=sa.String(5))
    op.alter_column('lab_results', 'flag', type_=sa.String(15), existing_type=sa.String(5))


def downgrade():
    op.alter_column('lab_results', 'flag', type_=sa.String(5), existing_type=sa.String(15))
    op.alter_column('embryo_assessments', 'expansion', type_=sa.String(5), existing_type=sa.String(12))
    op.alter_column('fertilization_records', 'status', type_=sa.String(10), existing_type=sa.String(20))
    op.drop_constraint('fk_treatment_cycles_package_id', 'treatment_cycles', type_='foreignkey')
    op.drop_constraint('fk_treatment_cycles_created_by', 'treatment_cycles', type_='foreignkey')
    op.drop_constraint('fk_treatment_cycles_timeline_id', 'treatment_cycles', type_='foreignkey')
    op.drop_constraint('fk_appointments_cycle_id', 'appointments', type_='foreignkey')
    op.drop_column('treatment_cycles', 'updated_at')
    op.drop_column('treatment_cycles', 'created_by')
    op.drop_column('treatment_cycles', 'closure_reason')
    op.drop_column('treatment_cycles', 'closed_at')
    op.drop_column('treatment_cycles', 'plan_published_at')
    op.drop_column('treatment_cycles', 'physician_order')
    op.drop_column('treatment_cycles', 'timeline_id')
    op.drop_column('treatment_cycles', 'registry_report_status')
    op.drop_column('treatment_cycles', 'freeze_all')
    op.drop_column('treatment_cycles', 'pgt')
    op.drop_column('treatment_cycles', 'planned_et_day')
    op.drop_column('treatment_cycles', 'trigger_at')
    op.drop_column('treatment_cycles', 'd0_date')
    op.drop_column('treatment_cycles', 'medication_start_date')
    op.drop_column('treatment_cycles', 'status')
    op.drop_column('treatment_cycles', 'package_id')
    op.drop_column('appointments', 'queue_number')
    op.drop_column('appointments', 'google_synced_at')
    op.drop_column('appointments', 'google_event_id')
    op.drop_column('appointments', 'cycle_id')
    op.drop_table('portal_booking_requests')
    op.drop_table('patient_notifications')
    op.drop_table('patient_accounts')
    op.drop_table('cryo_storage_terms')
    op.drop_table('embryo_photos')
    op.drop_table('witness_incidents')
    op.drop_table('witness_scans')
    op.drop_table('witness_sessions')
    op.drop_table('lab_items')
    op.drop_table('lab_tasks')
    op.drop_table('cycle_consents')
    op.drop_table('consent_templates')
    op.drop_table('cycle_outcomes')
    op.drop_table('cycle_events')
    op.drop_table('cycle_monitoring')
    op.drop_table('cycle_medication_doses')
    op.drop_table('cycle_medications')
    op.drop_table('cycle_days')
    op.drop_table('treatment_packages')
