"""
FCMS - Module 2: Lab Management
Database Models
Sub-labs: General Lab | Embryology Lab | Andrology Lab
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, JSON, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum

from module1.backend.core.database import Base  # shared metadata

def gen_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────

class LabType(str, enum.Enum):
    GENERAL    = "general"
    EMBRYOLOGY = "embryology"
    ANDROLOGY  = "andrology"

class OrderStatus(str, enum.Enum):
    PENDING    = "pending"
    COLLECTED  = "collected"
    PROCESSING = "processing"
    RESULTED   = "resulted"
    VERIFIED   = "verified"
    CANCELLED  = "cancelled"

class SpecimenType(str, enum.Enum):
    BLOOD            = "blood"
    URINE            = "urine"
    SEMEN            = "semen"
    FOLLICULAR_FLUID = "follicular_fluid"
    EMBRYO           = "embryo"
    OOCYTE           = "oocyte"
    OTHER            = "other"

class ResultFlag(str, enum.Enum):
    NORMAL       = "N"
    LOW          = "L"
    HIGH         = "H"
    CRITICAL_LOW = "LL"
    CRITICAL_HIGH= "HH"
    ABNORMAL     = "A"

class FertilizationStatus(str, enum.Enum):
    NORMAL_2PN  = "2PN"
    ABNORMAL_1PN= "1PN"
    ABNORMAL_3PN= "3PN"
    UNFERTILIZED= "0PN"
    DEGENERATED = "DG"

class EmbryoDisposition(str, enum.Enum):
    FRESH_TRANSFER = "fresh_transfer"
    FROZEN         = "frozen"
    DISCARDED      = "discarded"
    DONATED        = "donated"
    THAWED         = "thawed"

class WarmingStatus(str, enum.Enum):
    SURVIVED           = "survived"
    PARTIALLY_SURVIVED = "partially_survived"
    DEGENERATED        = "degenerated"

class BlastocystExpansion(str, enum.Enum):
    EARLY      = "1"
    CAVITATING = "2"
    FULL       = "3"
    EXPANDED   = "4"
    HATCHING   = "5"
    HATCHED    = "6"

class ICMGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"

class TEGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


# ─────────────────────────────────────────────────────────────
# GENERAL LAB
# ─────────────────────────────────────────────────────────────

class LabTestPanel(Base):
    """Master catalogue of all available tests"""
    __tablename__ = "lab_test_panels"

    id                       = Column(UUID, primary_key=True, default=gen_uuid)
    code                     = Column(String(50), unique=True, nullable=False)  # e.g. FSH, AMH, CBC
    name_en                  = Column(String(200), nullable=False)
    name_th                  = Column(String(200))
    lab_type                 = Column(SAEnum(LabType), nullable=False)
    specimen_type            = Column(SAEnum(SpecimenType), nullable=False)
    unit                     = Column(String(50))
    normal_range_female_min  = Column(Numeric(12, 4))
    normal_range_female_max  = Column(Numeric(12, 4))
    normal_range_male_min    = Column(Numeric(12, 4))
    normal_range_male_max    = Column(Numeric(12, 4))
    critical_low             = Column(Numeric(12, 4))
    critical_high            = Column(Numeric(12, 4))
    turnaround_hours         = Column(Integer, default=24)
    collection_instructions  = Column(Text)
    is_active                = Column(Boolean, default=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("LabOrderItem", back_populates="test_panel")


class LabOrder(Base):
    """Lab order raised from EMR visit"""
    __tablename__ = "lab_orders"

    id                  = Column(UUID, primary_key=True, default=gen_uuid)
    order_number        = Column(String(30), unique=True, nullable=False)  # LO-2026-00001
    patient_id          = Column(UUID, ForeignKey("patients.id"), nullable=False)
    visit_id            = Column(UUID, ForeignKey("visits.id"))
    ordering_physician_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    lab_type            = Column(SAEnum(LabType), nullable=False)
    status              = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    priority            = Column(String(20), default="routine")  # routine | urgent | stat
    clinical_notes      = Column(Text)
    diagnosis_code      = Column(String(20))
    ordered_at          = Column(DateTime(timezone=True), server_default=func.now())
    collected_at        = Column(DateTime(timezone=True))
    resulted_at         = Column(DateTime(timezone=True))
    verified_at         = Column(DateTime(timezone=True))
    verified_by_id      = Column(UUID, ForeignKey("users.id"))
    cancelled_at        = Column(DateTime(timezone=True))
    cancel_reason       = Column(Text)

    items     = relationship("LabOrderItem", back_populates="order", cascade="all, delete-orphan")
    specimens = relationship("LabSpecimen",  back_populates="order")

    __table_args__ = (
        Index("ix_lab_orders_patient",    "patient_id"),
        Index("ix_lab_orders_status",     "status"),
        Index("ix_lab_orders_ordered_at", "ordered_at"),
    )


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    order_id      = Column(UUID, ForeignKey("lab_orders.id"), nullable=False)
    test_panel_id = Column(UUID, ForeignKey("lab_test_panels.id"), nullable=False)
    status        = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING)

    order      = relationship("LabOrder",     back_populates="items")
    test_panel = relationship("LabTestPanel", back_populates="order_items")
    result     = relationship("LabResult",    back_populates="order_item", uselist=False)


class LabSpecimen(Base):
    __tablename__ = "lab_specimens"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    barcode          = Column(String(50), unique=True, nullable=False)
    order_id         = Column(UUID, ForeignKey("lab_orders.id"), nullable=False)
    specimen_type    = Column(SAEnum(SpecimenType), nullable=False)
    container        = Column(String(100))   # EDTA tube, plain tube, universal container
    volume_ml        = Column(Numeric(6, 2))
    collected_by_id  = Column(UUID, ForeignKey("users.id"))
    collected_at     = Column(DateTime(timezone=True))
    received_at      = Column(DateTime(timezone=True))
    storage_location = Column(String(100))
    is_rejected      = Column(Boolean, default=False)
    rejection_reason = Column(Text)
    notes            = Column(Text)

    order = relationship("LabOrder", back_populates="specimens")


class LabResult(Base):
    __tablename__ = "lab_results"

    id             = Column(UUID, primary_key=True, default=gen_uuid)
    order_item_id  = Column(UUID, ForeignKey("lab_order_items.id"), nullable=False)
    numeric_value  = Column(Numeric(14, 4))
    text_value     = Column(String(500))
    unit           = Column(String(50))
    flag           = Column(SAEnum(ResultFlag))
    normal_range   = Column(String(100))
    method         = Column(String(100))
    instrument     = Column(String(100))
    resulted_by_id = Column(UUID, ForeignKey("users.id"))
    resulted_at    = Column(DateTime(timezone=True), server_default=func.now())
    verified_by_id = Column(UUID, ForeignKey("users.id"))
    verified_at    = Column(DateTime(timezone=True))
    comment        = Column(Text)

    order_item = relationship("LabOrderItem", back_populates="result")


# ─────────────────────────────────────────────────────────────
# EMBRYOLOGY LAB
# ─────────────────────────────────────────────────────────────

class TreatmentCycle(Base):
    """IVF/IUI treatment cycle - links all embryology records"""
    __tablename__ = "treatment_cycles"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    cycle_number    = Column(String(30), unique=True, nullable=False)  # CYC-2026-001
    patient_id      = Column(UUID, ForeignKey("patients.id"), nullable=False)
    partner_id      = Column(UUID, ForeignKey("patients.id"))
    cycle_type      = Column(String(30))   # IVF | ICSI | IUI | FET
    start_date      = Column(Date)
    end_date        = Column(Date)
    outcome         = Column(String(50))   # ongoing | pregnant | cancelled | failed
    physician_id    = Column(UUID, ForeignKey("users.id"))
    embryologist_id = Column(UUID, ForeignKey("users.id"))
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    oocyte_retrievals = relationship("OocyteRetrieval", back_populates="cycle")
    embryos           = relationship("Embryo",           back_populates="cycle")


class OocyteRetrieval(Base):
    """Egg collection procedure"""
    __tablename__ = "oocyte_retrievals"

    id                        = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id                = Column(UUID, ForeignKey("patients.id"), nullable=False)
    cycle_id                  = Column(UUID, ForeignKey("treatment_cycles.id"))
    visit_id                  = Column(UUID, ForeignKey("visits.id"))
    procedure_date            = Column(Date, nullable=False)
    start_time                = Column(DateTime(timezone=True))
    end_time                  = Column(DateTime(timezone=True))
    physician_id              = Column(UUID, ForeignKey("users.id"), nullable=False)
    embryologist_id           = Column(UUID, ForeignKey("users.id"), nullable=False)
    anesthesia_type           = Column(String(50))
    total_follicles_aspirated = Column(Integer)
    total_oocytes_retrieved   = Column(Integer)
    mii_count                 = Column(Integer)   # mature
    mi_count                  = Column(Integer)
    gv_count                  = Column(Integer)   # immature
    degenerated_count         = Column(Integer)
    follicular_fluid_ml       = Column(Numeric(6, 2))
    complications             = Column(Text)
    notes                     = Column(Text)
    created_at                = Column(DateTime(timezone=True), server_default=func.now())

    cycle   = relationship("TreatmentCycle",    back_populates="oocyte_retrievals")
    oocytes = relationship("Oocyte",            back_populates="retrieval")


class Oocyte(Base):
    __tablename__ = "oocytes"

    id                  = Column(UUID, primary_key=True, default=gen_uuid)
    retrieval_id        = Column(UUID, ForeignKey("oocyte_retrievals.id"), nullable=False)
    oocyte_number       = Column(Integer, nullable=False)
    maturity_stage      = Column(String(10))   # MII | MI | GV
    morphology_score    = Column(String(50))
    zona_pellucida      = Column(String(50))
    perivitelline_space = Column(String(50))
    polar_body          = Column(String(50))
    cytoplasm           = Column(String(50))
    is_inseminated      = Column(Boolean, default=False)
    insemination_method = Column(String(20))   # IVF | ICSI | PICSI
    insemination_time   = Column(DateTime(timezone=True))
    notes               = Column(Text)

    retrieval     = relationship("OocyteRetrieval", back_populates="oocytes")
    fertilization = relationship("FertilizationRecord", back_populates="oocyte", uselist=False)


class FertilizationRecord(Base):
    """Day 1 fertilization check"""
    __tablename__ = "fertilization_records"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    oocyte_id       = Column(UUID, ForeignKey("oocytes.id"), nullable=False)
    patient_id      = Column(UUID, ForeignKey("patients.id"), nullable=False)
    check_time      = Column(DateTime(timezone=True))
    embryologist_id = Column(UUID, ForeignKey("users.id"))
    status          = Column(SAEnum(FertilizationStatus), nullable=False)
    pronuclei_count = Column(Integer)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    oocyte = relationship("Oocyte", back_populates="fertilization")
    embryo = relationship("Embryo", back_populates="fertilization_record", uselist=False)


class Embryo(Base):
    """Core embryo record — tracked Day 1 through transfer/freeze"""
    __tablename__ = "embryos"

    id                      = Column(UUID, primary_key=True, default=gen_uuid)
    embryo_code             = Column(String(30), unique=True, nullable=False)  # EMB-2026-001
    patient_id              = Column(UUID, ForeignKey("patients.id"), nullable=False)
    partner_id              = Column(UUID, ForeignKey("patients.id"))
    cycle_id                = Column(UUID, ForeignKey("treatment_cycles.id"))
    fertilization_record_id = Column(UUID, ForeignKey("fertilization_records.id"))
    current_day             = Column(Integer, default=1)
    disposition             = Column(SAEnum(EmbryoDisposition))
    is_pgta_tested          = Column(Boolean, default=False)
    pgta_result             = Column(String(50))   # euploid | aneuploid | mosaic
    notes                   = Column(Text)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())

    cycle                = relationship("TreatmentCycle", back_populates="embryos")
    fertilization_record = relationship("FertilizationRecord", back_populates="embryo")
    assessments          = relationship("EmbryoAssessment", back_populates="embryo",
                                        order_by="EmbryoAssessment.assessment_day")
    cryopreservation     = relationship("EmbryoCryopreservation", back_populates="embryo", uselist=False)
    warming              = relationship("EmbryoWarming",          back_populates="embryo", uselist=False)
    transfer             = relationship("EmbryoTransfer",         back_populates="embryo", uselist=False)


class EmbryoAssessment(Base):
    """Daily embryo grading (Day 2, 3, 5, 6)"""
    __tablename__ = "embryo_assessments"

    id                   = Column(UUID, primary_key=True, default=gen_uuid)
    embryo_id            = Column(UUID, ForeignKey("embryos.id"), nullable=False)
    assessment_day       = Column(Integer, nullable=False)
    assessment_time      = Column(DateTime(timezone=True))
    embryologist_id      = Column(UUID, ForeignKey("users.id"))

    # Cleavage stage (Day 2-3)
    cell_count           = Column(Integer)
    fragmentation_pct    = Column(Numeric(5, 2))
    symmetry             = Column(String(30))   # equal | unequal
    multinucleation      = Column(Boolean, default=False)

    # Blastocyst stage (Day 5-6)
    expansion            = Column(SAEnum(BlastocystExpansion))
    icm_grade            = Column(SAEnum(ICMGrade))
    te_grade             = Column(SAEnum(TEGrade))

    # Overall
    overall_grade        = Column(String(20))
    is_suitable_transfer = Column(Boolean)
    is_suitable_freeze   = Column(Boolean)
    image_path           = Column(String(500))   # embryo photo
    notes                = Column(Text)

    embryo = relationship("Embryo", back_populates="assessments")


class EmbryoCryopreservation(Base):
    """Embryo freezing record"""
    __tablename__ = "embryo_cryopreservations"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    embryo_id       = Column(UUID, ForeignKey("embryos.id"), nullable=False)
    embryologist_id = Column(UUID, ForeignKey("users.id"))
    freeze_date     = Column(DateTime(timezone=True), nullable=False)
    method          = Column(String(50))       # vitrification | slow-freeze
    device          = Column(String(50))       # cryotop | cryolock | straw
    device_label    = Column(String(100))
    tank_id         = Column(String(50))       # liquid nitrogen tank
    canister        = Column(String(20))
    goblet          = Column(String(20))
    position        = Column(String(20))
    cryo_medium     = Column(String(100))
    verified_by_id  = Column(UUID, ForeignKey("users.id"))
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    embryo = relationship("Embryo", back_populates="cryopreservation")


class EmbryoWarming(Base):
    """Embryo warming/thaw record"""
    __tablename__ = "embryo_warmings"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    embryo_id       = Column(UUID, ForeignKey("embryos.id"), nullable=False)
    embryologist_id = Column(UUID, ForeignKey("users.id"))
    warming_date    = Column(DateTime(timezone=True), nullable=False)
    status          = Column(SAEnum(WarmingStatus), nullable=False)
    blastomeres_intact_pct = Column(Numeric(5, 2))
    post_warm_grade = Column(String(20))
    warming_medium  = Column(String(100))
    verified_by_id  = Column(UUID, ForeignKey("users.id"))
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    embryo = relationship("Embryo", back_populates="warming")


class EmbryoTransfer(Base):
    """Embryo transfer procedure"""
    __tablename__ = "embryo_transfers"

    id                    = Column(UUID, primary_key=True, default=gen_uuid)
    embryo_id             = Column(UUID, ForeignKey("embryos.id"), nullable=False)
    patient_id            = Column(UUID, ForeignKey("patients.id"), nullable=False)
    cycle_id              = Column(UUID, ForeignKey("treatment_cycles.id"))
    transfer_date         = Column(DateTime(timezone=True), nullable=False)
    physician_id          = Column(UUID, ForeignKey("users.id"), nullable=False)
    embryologist_id       = Column(UUID, ForeignKey("users.id"), nullable=False)
    transfer_type         = Column(String(20))   # fresh | frozen
    endometrial_thickness = Column(Numeric(4, 1))
    catheter_type         = Column(String(100))
    difficulty            = Column(String(20))   # easy | moderate | difficult
    ultrasound_guided     = Column(Boolean, default=True)
    embryo_position_mm    = Column(Numeric(4, 1))
    outcome_beta_hcg      = Column(Numeric(10, 2))
    outcome_date          = Column(Date)
    outcome               = Column(String(50))   # positive | negative | biochemical
    notes                 = Column(Text)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())

    embryo = relationship("Embryo", back_populates="transfer")


# ─────────────────────────────────────────────────────────────
# ANDROLOGY / UROLOGY LAB
# ─────────────────────────────────────────────────────────────

class SemenAnalysis(Base):
    """Semen analysis — WHO 2021 criteria"""
    __tablename__ = "semen_analyses"

    id                     = Column(UUID, primary_key=True, default=gen_uuid)
    analysis_number        = Column(String(30), unique=True, nullable=False)  # SA-2026-001
    patient_id             = Column(UUID, ForeignKey("patients.id"), nullable=False)
    order_id               = Column(UUID, ForeignKey("lab_orders.id"))
    collected_at           = Column(DateTime(timezone=True))
    received_at            = Column(DateTime(timezone=True))
    analyzed_at            = Column(DateTime(timezone=True))
    abstinence_days        = Column(Integer)
    collection_method      = Column(String(50))   # masturbation | surgical | other
    collection_location    = Column(String(50))   # clinic | home
    analyst_id             = Column(UUID, ForeignKey("users.id"))
    verified_by_id         = Column(UUID, ForeignKey("users.id"))

    # Macroscopic
    volume_ml              = Column(Numeric(5, 2))
    appearance             = Column(String(50))    # normal | abnormal
    color                  = Column(String(30))
    viscosity              = Column(String(30))    # normal | increased
    liquefaction_time_min  = Column(Integer)
    ph                     = Column(Numeric(4, 2))

    # Microscopic — WHO 2021
    concentration_M_per_ml = Column(Numeric(8, 2))   # million/ml
    total_count_M          = Column(Numeric(8, 2))   # million
    total_motility_pct     = Column(Numeric(5, 2))   # PR + NP
    progressive_motility_pct = Column(Numeric(5, 2)) # PR
    non_progressive_pct    = Column(Numeric(5, 2))   # NP
    immotile_pct           = Column(Numeric(5, 2))
    normal_morphology_pct  = Column(Numeric(5, 2))   # Kruger strict

    # Vitality
    vitality_pct           = Column(Numeric(5, 2))
    vitality_method        = Column(String(50))      # eosin-nigrosin | HOS

    # Additional
    wbc_per_ml             = Column(Numeric(8, 2))
    rbc_per_ml             = Column(Numeric(8, 2))
    agglutination          = Column(String(30))
    sperm_antibodies       = Column(Boolean)

    # DNA fragmentation
    dfi_pct                = Column(Numeric(5, 2))   # DNA fragmentation index
    dfi_method             = Column(String(50))      # TUNEL | SCSA | SCD

    # Overall assessment
    who_reference_met      = Column(Boolean)
    diagnosis              = Column(String(100))     # normozoospermia | oligozoospermia etc.
    recommendation         = Column(Text)
    notes                  = Column(Text)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_semen_patient",    "patient_id"),
        Index("ix_semen_analyzed_at","analyzed_at"),
    )


class SpermPreparation(Base):
    """Sperm preparation for IUI/IVF/ICSI"""
    __tablename__ = "sperm_preparations"

    id                       = Column(UUID, primary_key=True, default=gen_uuid)
    semen_analysis_id        = Column(UUID, ForeignKey("semen_analyses.id"))
    cycle_id                 = Column(UUID, ForeignKey("treatment_cycles.id"))
    patient_id               = Column(UUID, ForeignKey("patients.id"), nullable=False)
    preparation_method       = Column(String(50))   # swim-up | density gradient | wash
    prepared_at              = Column(DateTime(timezone=True))
    embryologist_id          = Column(UUID, ForeignKey("users.id"))

    # Post-prep parameters
    post_volume_ml           = Column(Numeric(5, 2))
    post_concentration_M_ml  = Column(Numeric(8, 2))
    post_motility_pct        = Column(Numeric(5, 2))
    post_progressive_pct     = Column(Numeric(5, 2))
    post_total_motile_M      = Column(Numeric(8, 2))
    recovery_rate_pct        = Column(Numeric(5, 2))
    used_for                 = Column(String(30))   # IUI | IVF | ICSI | freeze
    notes                    = Column(Text)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())


class SpermCryopreservation(Base):
    """Sperm freezing / banking"""
    __tablename__ = "sperm_cryopreservations"

    id               = Column(UUID, primary_key=True, default=gen_uuid)
    patient_id       = Column(UUID, ForeignKey("patients.id"), nullable=False)
    sample_number    = Column(String(30), unique=True, nullable=False)
    freeze_date      = Column(DateTime(timezone=True), nullable=False)
    embryologist_id  = Column(UUID, ForeignKey("users.id"))
    num_straws       = Column(Integer)
    tank_id          = Column(String(50))
    canister         = Column(String(20))
    goblet           = Column(String(20))
    cryo_medium      = Column(String(100))
    pre_freeze_motility_pct  = Column(Numeric(5, 2))
    post_thaw_motility_pct   = Column(Numeric(5, 2))
    expiry_date      = Column(Date)
    consent_form_ref = Column(String(100))
    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
