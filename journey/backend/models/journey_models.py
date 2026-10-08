"""
FCMS Journey layer — ORM models
The "Infans-style" patient-journey spine: packages → cycle → stimulation chart →
procedure scheduling → lab tasks → witnessing → observation → outcome → cryo billing.

Design rule: reuse Module 2's embryology tables (treatment_cycles, oocyte_retrievals,
oocytes, fertilization_records, embryos, embryo_assessments, cryopreservations,
warmings, transfers, semen/sperm tables). This file only ADDS the orchestration
tables and a few columns on treatment_cycles / appointments (see migration j1_001).
"""
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Time, Text,
    ForeignKey, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

# str-typed UUIDs end to end (SQLAlchemy 2.0 insertmanyvalues needs the Python value type to match the DB return type)
UUID = PG_UUID(as_uuid=False)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from module1.backend.core.database import Base
# Make sure every table we reference by FK is registered on the shared metadata before mappers configure
import module1.backend.models.user_models   # noqa: F401  users
import module1.backend.models.emr_models    # noqa: F401  patients, visits, consent_forms
import module2.backend.models.lab_models    # noqa: F401  treatment_cycles, embryos, oocytes
import module4.backend.models.pharmacy_models  # noqa: F401  drugs
import module6.backend.models.crm_models    # noqa: F401  appointments
import module7.backend.models.accounting_models  # noqa: F401  invoices
import module10.backend.models.timeline_models   # noqa: F401  cycle_timelines


def gen_uuid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════
# PACKAGES — the one template that drives all four lanes
# ═══════════════════════════════════════════════════════════════════════════

class TreatmentPackage(Base):
    """A treatment package (Binflux: 'Package', e.g. IVF-D5ET).
    Bundles the medication template, the lab-event template (with witness points and
    EMR write-back keys), the required consents, the patient-notification template and
    the billing items. Editable data, not code."""
    __tablename__ = "treatment_packages"

    id                  = Column(UUID, primary_key=True, default=gen_uuid)
    code                = Column(String(40), unique=True, nullable=False)       # IVF_ICSI_FRESH_D5
    name_en             = Column(String(200), nullable=False)
    name_th             = Column(String(200))
    cycle_type          = Column(String(40), nullable=False)                    # ivf_icsi_fresh | ivf_icsi_freeze_all | fet_hrt | fet_natural | fet_stimulated | iui | oocyte_cryo | sperm_cryo | episode_*
    is_episode          = Column(Boolean, default=False)                        # procedure-only episode (PRP, hysteroscopy, semen analysis)
    anchor              = Column(String(20), default="opu")                     # what D0 means: opu | et | iui | procedure | collection
    default_et_day      = Column(Integer)                                       # 3 | 5 (fresh transfer) — null for freeze-all
    pgt                 = Column(Boolean, default=False)
    freeze_all          = Column(Boolean, default=False)
    medication_template = Column(JSONB, default=list)   # [{drug_en, drug_th, dose, unit, route, slot, start, end, drug_code}]
    lab_events          = Column(JSONB, default=list)   # [{key, day, type, title_en, title_th, time, requires_witness, items, write_back, consents, lane}]
    consents            = Column(JSONB, default=list)   # [consent_type codes]
    notifications       = Column(JSONB, default=dict)   # {event_type: {en, th}} overrides
    billing_items       = Column(JSONB, default=list)   # [{code, description_en, description_th, amount, when: on_create|on_opu|on_et|on_freeze|storage_year}]
    description_en      = Column(Text)
    description_th      = Column(Text)
    is_active           = Column(Boolean, default=True)
    sort_order          = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# CYCLE SPINE (treatment_cycles gets new columns in the migration)
# ═══════════════════════════════════════════════════════════════════════════

class CycleDay(Base):
    """One calendar day of a cycle. day_index is relative to medication start (day 1 = first
    medication day); lab_day is the embryology day (D0 = OPU / insemination) once scheduled."""
    __tablename__ = "cycle_days"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id         = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_date    = Column(Date, nullable=False)
    day_index        = Column(Integer, nullable=False)          # 1-based from medication start
    stimulation_day  = Column(Integer)                          # S1.. (same as day_index for stimulation cycles)
    lab_day          = Column(Integer)                          # D0..D7 (null before procedure scheduled)
    label_en         = Column(String(120))                      # "Monitoring visit", "Trigger", "OPU", ...
    label_th         = Column(String(120))
    appointment_id   = Column(UUID, ForeignKey("appointments.id"))
    is_visit         = Column(Boolean, default=False)
    is_procedure     = Column(Boolean, default=False)
    notes            = Column(Text)

    __table_args__ = (UniqueConstraint("cycle_id", "calendar_date", name="uq_cycle_day"),)


class CycleMedication(Base):
    """A row of the stimulation chart: one drug, dose, route, slot, over a day range."""
    __tablename__ = "cycle_medications"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id        = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    drug_id         = Column(UUID, ForeignKey("drugs.id"))        # optional link to pharmacy catalogue
    drug_code       = Column(String(50))
    drug_en         = Column(String(200), nullable=False)
    drug_th         = Column(String(200))
    dose            = Column(Numeric(10, 2))
    unit            = Column(String(20))                         # IU | mg | mcg | tab | ml
    route           = Column(String(20))                         # SC | IM | PO | PV | IN
    slot            = Column(String(10), default="PM")           # AM | NOON | PM | HS | time "20:00"
    start_day_index = Column(Integer, nullable=False)
    end_day_index   = Column(Integer, nullable=False)
    instructions_en = Column(Text)
    instructions_th = Column(Text)
    sort_order      = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    doses = relationship("CycleMedicationDose", back_populates="medication", cascade="all, delete-orphan")


class CycleMedicationDose(Base):
    """One dose on one day — what the patient ticks in the app."""
    __tablename__ = "cycle_medication_doses"

    id             = Column(UUID, primary_key=True, default=gen_uuid)
    medication_id  = Column(UUID, ForeignKey("cycle_medications.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle_id       = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_date  = Column(Date, nullable=False, index=True)
    day_index      = Column(Integer, nullable=False)
    slot           = Column(String(10))
    dose           = Column(Numeric(10, 2))
    unit           = Column(String(20))
    taken_at       = Column(DateTime(timezone=True))
    taken_source   = Column(String(10))                         # patient | staff
    reminder_sent_at = Column(DateTime(timezone=True))
    notes          = Column(Text)

    medication = relationship("CycleMedication", back_populates="doses")

    __table_args__ = (UniqueConstraint("medication_id", "calendar_date", "slot", name="uq_dose_day_slot"),)


class CycleMonitoring(Base):
    """A monitoring visit on a cycle day: follicles (right/left), endometrium, hormones.
    Binflux: 'follicle entry' + treatment table. Ultrasound study UID links Module 3."""
    __tablename__ = "cycle_monitoring"

    id                   = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id             = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_date        = Column(Date, nullable=False)
    day_index            = Column(Integer)
    visit_id             = Column(UUID, ForeignKey("visits.id"))
    follicles_right      = Column(JSONB, default=list)         # [mm, mm, ...]
    follicles_left       = Column(JSONB, default=list)
    endometrium_mm       = Column(Numeric(4, 1))
    endometrium_pattern  = Column(String(20))                  # trilaminar | homogeneous | other
    e2                   = Column(Numeric(10, 2))              # pg/mL
    lh                   = Column(Numeric(10, 2))              # IU/L
    p4                   = Column(Numeric(10, 2))              # ng/mL
    fsh                  = Column(Numeric(10, 2))
    hcg                  = Column(Numeric(10, 2))
    orthanc_study_uid    = Column(String(120))
    decision_en          = Column(Text)                        # continue / adjust dose / trigger tonight
    decision_th          = Column(Text)
    recorded_by          = Column(UUID, ForeignKey("users.id"))
    released_to_patient  = Column(Boolean, default=False)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("cycle_id", "calendar_date", name="uq_monitoring_day"),)


class CycleEvent(Base):
    """Append-only domain event log. Every lane writes here; handlers react (lab tasks,
    notifications, calendar sync, billing, boards). `handlers` records what each did."""
    __tablename__ = "cycle_events"

    id          = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id    = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), index=True)
    patient_id  = Column(UUID, ForeignKey("patients.id"), index=True)
    type        = Column(String(60), nullable=False, index=True)   # cycle.created | plan.published | procedure.scheduled | ...
    payload     = Column(JSONB, default=dict)
    actor_id    = Column(UUID, ForeignKey("users.id"))
    handlers    = Column(JSONB, default=dict)                      # {handler_name: "ok" | "error: ..."}
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CycleOutcome(Base):
    """Cycle outcome and pregnancy follow-up (Binflux: cycle outcome / pregnancy tracking)."""
    __tablename__ = "cycle_outcomes"

    id                   = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id             = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, unique=True)
    patient_id           = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    cancelled_before_opu = Column(Boolean, default=False)
    cancel_reason        = Column(String(200))
    hcg_date             = Column(Date)
    hcg_value            = Column(Numeric(10, 2))
    hcg_positive         = Column(Boolean)
    biochemical_only     = Column(Boolean)
    clinical_pregnancy   = Column(Boolean)                      # gestational sac on ultrasound
    gestational_sacs     = Column(Integer)
    fetal_hearts         = Column(Integer)
    ongoing_pregnancy    = Column(Boolean)                      # ≥ 12 weeks
    miscarriage          = Column(Boolean)
    ectopic              = Column(Boolean)
    live_birth           = Column(Boolean)
    delivery_date        = Column(Date)
    babies               = Column(Integer)
    birth_details        = Column(JSONB, default=list)         # [{sex, weight_g, gestational_weeks}]
    ohss_grade           = Column(String(20))                   # none | mild | moderate | severe
    opu_complication     = Column(String(200))
    notes                = Column(Text)
    recorded_by          = Column(UUID, ForeignKey("users.id"))
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# CONSENTS (cycle-scoped, gating lab tasks)
# ═══════════════════════════════════════════════════════════════════════════

class ConsentTemplate(Base):
    __tablename__ = "consent_templates"

    id         = Column(UUID, primary_key=True, default=gen_uuid)
    code       = Column(String(50), unique=True, nullable=False)   # ivf_treatment | anaesthesia | lab_icsi | cryo_storage | pgt | disposal | iui | prp | hysteroscopy | pdpa
    title_en   = Column(String(200), nullable=False)
    title_th   = Column(String(200))
    body_en    = Column(Text)
    body_th    = Column(Text)
    version    = Column(String(10), default="1.0")
    signer     = Column(String(20), default="patient")             # patient | partner | both
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CycleConsent(Base):
    """A consent required for a cycle (from the package). Signed in clinic or in the patient app."""
    __tablename__ = "cycle_consents"

    id                = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id          = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id        = Column(UUID, ForeignKey("patients.id"), nullable=False)
    consent_type      = Column(String(50), nullable=False)
    template_id       = Column(UUID, ForeignKey("consent_templates.id"))
    template_version  = Column(String(10))
    status            = Column(String(20), default="pending")      # pending | signed | declined | revoked
    signed_at         = Column(DateTime(timezone=True))
    signed_by_patient_id = Column(UUID, ForeignKey("patients.id"))
    signed_channel    = Column(String(20))                          # clinic_tablet | patient_app | paper
    signature_path    = Column(String(500))
    document_path     = Column(String(500))
    document_hash     = Column(String(64))
    witness_user_id   = Column(UUID, ForeignKey("users.id"))
    ip_address        = Column(String(45))
    consent_form_id   = Column(UUID, ForeignKey("consent_forms.id"))  # Module 1 record, kept in sync
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("cycle_id", "consent_type", name="uq_cycle_consent"),)


# ═══════════════════════════════════════════════════════════════════════════
# LAB TASKS, LABELS, WITNESSING
# ═══════════════════════════════════════════════════════════════════════════

class LabTask(Base):
    """A lab to-do generated from the package when the procedure is scheduled
    (Binflux EWS: 'orders auto-create daily to-do events')."""
    __tablename__ = "lab_tasks"

    id                 = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id           = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id         = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    key                = Column(String(40), nullable=False)          # opu | sperm_collection | sperm_prep | denudation | insemination | icsi | fert_check | cleavage_check | blast_check | biopsy | vitrification | warming | et | iui ...
    task_type          = Column(String(40), nullable=False)          # grouping on the board (same vocabulary as key, minus day suffixes)
    title_en           = Column(String(200), nullable=False)
    title_th           = Column(String(200))
    lab_day            = Column(Integer)                             # D0..D7
    scheduled_date     = Column(Date, nullable=False, index=True)
    scheduled_time     = Column(Time)
    sort_order         = Column(Integer, default=0)
    status             = Column(String(20), default="pending", index=True)  # pending | done | failed | skipped
    requires_witness   = Column(Boolean, default=False)
    items_required     = Column(JSONB, default=list)                 # ["oocyte_dish", "sperm_tube"]
    write_back         = Column(String(60))                          # key resolved by witness service → EMR timestamp
    required_consents  = Column(JSONB, default=list)
    physician_order    = Column(String(200))                         # "D5 ET", "Freeze-all, PGT-A"
    done_at            = Column(DateTime(timezone=True))
    done_by            = Column(UUID, ForeignKey("users.id"))
    failed_reason      = Column(Text)
    witness_session_id = Column(UUID)                                # last successful witness session
    notes              = Column(Text)
    assigned_to        = Column(UUID, ForeignKey("users.id"), index=True)   # j1_002: who is responsible for this step
    assigned_at        = Column(DateTime(timezone=True))
    assigned_by        = Column(UUID, ForeignKey("users.id"))
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_lab_tasks_date_status", "scheduled_date", "status"),)


class LabItem(Base):
    """A labelled physical item (dish, tube, straw, cryo device, wristband). The QR on the
    label encodes `label_code`; scanning resolves it to this row → cycle → patient."""
    __tablename__ = "lab_items"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    label_code    = Column(String(40), unique=True, nullable=False)   # LBL-<base32>
    cycle_id      = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id    = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)   # the person whose material this is (partner for sperm)
    item_type     = Column(String(30), nullable=False)      # oocyte_dish | culture_dish | sperm_tube | prep_tube | cryo_device | straw | wristband | et_catheter_dish | warming_dish | opu_tube
    lab_day       = Column(Integer)
    description   = Column(String(200))
    lab_task_id   = Column(UUID, ForeignKey("lab_tasks.id"))
    reference_table = Column(String(40))                      # embryo_cryopreservations | sperm_cryopreservations
    reference_id  = Column(UUID)
    printed_at    = Column(DateTime(timezone=True))
    printed_by    = Column(UUID, ForeignKey("users.id"))
    print_count   = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class WitnessSession(Base):
    """One witness act for one lab task: a set of scans that must all resolve to the same
    cycle (or linked couple). Result: match | mismatch | manual."""
    __tablename__ = "witness_sessions"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    lab_task_id     = Column(UUID, ForeignKey("lab_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle_id        = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False)
    second_user_id  = Column(UUID, ForeignKey("users.id"))          # manual double-witness
    device          = Column(String(120))
    started_at      = Column(DateTime(timezone=True), server_default=func.now())
    completed_at    = Column(DateTime(timezone=True))
    result          = Column(String(20))                            # match | mismatch | manual | abandoned
    items_expected  = Column(JSONB, default=list)
    items_scanned   = Column(JSONB, default=list)
    error_count     = Column(Integer, default=0)
    notes           = Column(Text)

    scans = relationship("WitnessScan", back_populates="session", cascade="all, delete-orphan")


class WitnessScan(Base):
    __tablename__ = "witness_scans"

    id                  = Column(UUID, primary_key=True, default=gen_uuid)
    session_id          = Column(UUID, ForeignKey("witness_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_payload         = Column(String(200), nullable=False)
    label_code          = Column(String(40))
    item_type           = Column(String(30))
    lab_item_id         = Column(UUID, ForeignKey("lab_items.id"))
    resolved_cycle_id   = Column(UUID)
    resolved_patient_id = Column(UUID)
    matched             = Column(Boolean)
    message             = Column(String(200))
    scanned_at          = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("WitnessSession", back_populates="scans")


class WitnessIncident(Base):
    __tablename__ = "witness_incidents"

    id           = Column(UUID, primary_key=True, default=gen_uuid)
    session_id   = Column(UUID, ForeignKey("witness_sessions.id"), index=True)
    cycle_id     = Column(UUID, ForeignKey("treatment_cycles.id"), index=True)
    lab_task_id  = Column(UUID, ForeignKey("lab_tasks.id"))
    severity     = Column(String(10), default="high")          # high | medium
    description  = Column(Text, nullable=False)
    created_by   = Column(UUID, ForeignKey("users.id"))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    resolved_by  = Column(UUID, ForeignKey("users.id"))
    resolved_at  = Column(DateTime(timezone=True))
    resolution   = Column(Text)


class EmbryoPhoto(Base):
    """Photo of an oocyte/embryo on a lab day. `released_to_patient` publishes it to the app album."""
    __tablename__ = "embryo_photos"

    id                  = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_id            = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    embryo_id           = Column(UUID, ForeignKey("embryos.id"))
    oocyte_id           = Column(UUID, ForeignKey("oocytes.id"))
    lab_day             = Column(Integer)
    path                = Column(String(500), nullable=False)
    thumbnail_path      = Column(String(500))
    caption_en          = Column(String(200))
    caption_th          = Column(String(200))
    source              = Column(String(20), default="upload")      # upload | camera | timelapse
    taken_at            = Column(DateTime(timezone=True), server_default=func.now())
    taken_by            = Column(UUID, ForeignKey("users.id"))
    released_to_patient = Column(Boolean, default=False)
    released_at         = Column(DateTime(timezone=True))
    released_by         = Column(UUID, ForeignKey("users.id"))


# ═══════════════════════════════════════════════════════════════════════════
# CRYO STORAGE TERMS ↔ BILLING
# ═══════════════════════════════════════════════════════════════════════════

class CryoStorageTerm(Base):
    """Storage agreement for frozen material: term paid until a date; reminders before expiry;
    renewal extends `paid_until`. Links to the Module 2 cryo rows and the Module 7 invoice."""
    __tablename__ = "cryo_storage_terms"

    id                 = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id         = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    cycle_id           = Column(UUID, ForeignKey("treatment_cycles.id"), index=True)
    content_type       = Column(String(20), nullable=False)       # embryo | oocyte | sperm
    reference_table    = Column(String(40))                       # embryo_cryopreservations | sperm_cryopreservations
    reference_ids      = Column(JSONB, default=list)              # ids covered by this term
    device_count       = Column(Integer, default=1)
    stored_at          = Column(Date, nullable=False)
    paid_until         = Column(Date, nullable=False, index=True)
    term_months        = Column(Integer, default=12)
    annual_fee         = Column(Numeric(12, 2))
    status             = Column(String(20), default="active", index=True)   # active | due | overdue | thawed | discarded | transferred_out
    last_reminder_at   = Column(DateTime(timezone=True))
    reminders_sent     = Column(Integer, default=0)
    invoice_id         = Column(UUID, ForeignKey("invoices.id"))
    consent_status     = Column(String(20), default="pending")    # pending | signed
    notes              = Column(Text)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# PATIENT ACCOUNTS + NOTIFICATION FEED (Patient App lane)
# ═══════════════════════════════════════════════════════════════════════════

class PatientAccount(Base):
    """Login identity for the patient app: LINE Login (LIFF) user id and/or phone OTP.
    Issues a `patient` JWT carrying patient_id."""
    __tablename__ = "patient_accounts"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id       = Column(UUID, ForeignKey("patients.id"), nullable=False, unique=True)
    line_user_id     = Column(String(64), unique=True)
    line_display_name = Column(String(120))
    phone            = Column(String(20), index=True)
    email            = Column(String(200))
    otp_hash         = Column(String(200))
    otp_expires_at   = Column(DateTime(timezone=True))
    otp_attempts     = Column(Integer, default=0)
    pin_hash         = Column(String(200))
    language         = Column(String(5), default="th")
    push_enabled     = Column(Boolean, default=True)
    web_push_subscription = Column(JSONB)
    is_active        = Column(Boolean, default=True)
    last_login_at    = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class PatientNotification(Base):
    """In-app notification feed (what the patient sees in the app, regardless of channel delivery)."""
    __tablename__ = "patient_notifications"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id      = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    cycle_id        = Column(UUID, ForeignKey("treatment_cycles.id", ondelete="SET NULL"))
    type            = Column(String(60), nullable=False)          # same vocabulary as cycle_events.type
    title_en        = Column(String(200))
    title_th        = Column(String(200))
    body_en         = Column(Text)
    body_th         = Column(Text)
    action_url      = Column(String(300))
    channels        = Column(JSONB, default=dict)                 # {"line": "sent", "sms": "skipped: not configured"}
    scheduled_for   = Column(DateTime(timezone=True))
    sent_at         = Column(DateTime(timezone=True))
    read_at         = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class PortalBookingRequest(Base):
    """Patient-initiated booking request from the app; staff confirm into a Module 6 appointment."""
    __tablename__ = "portal_booking_requests"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id       = Column(UUID, ForeignKey("patients.id"), nullable=False, index=True)
    requested_date   = Column(Date, nullable=False)
    requested_time   = Column(Time)
    appointment_type = Column(String(30), nullable=False)
    note             = Column(Text)
    status           = Column(String(20), default="requested")    # requested | confirmed | declined | cancelled
    appointment_id   = Column(UUID, ForeignKey("appointments.id"))
    handled_by       = Column(UUID, ForeignKey("users.id"))
    handled_at       = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
