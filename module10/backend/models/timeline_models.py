"""
FCMS Module 10 — Cycle Plan / Timeline Generator
Persists patient cycle timelines (OPU / FET / ORA / IUI) produced by the
Timeline Generator UI. The generator's document is stored as JSONB so the
existing renderer keeps working unchanged; key fields are lifted into columns
for search, joins to the patient record, and future cycle-day linking.
"""
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, BigInteger, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from module1.backend.core.database import Base


def gen_uuid():
    return uuid.uuid4()


class CycleTimeline(Base):
    __tablename__ = "cycle_timelines"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    legacy_id     = Column(BigInteger, unique=True, index=True)   # generator's Date.now() id
    patient_id    = Column(UUID, ForeignKey("patients.id"), nullable=True, index=True)
    hn            = Column(String(30), index=True)
    first_name    = Column(String(100))
    last_name     = Column(String(100))
    cycle_type    = Column(String(10), index=True)                 # OPU | FET | ORA | IUI
    protocol      = Column(String(50))
    lmp           = Column(Date)
    day1_date     = Column(Date)                                   # LMP or OPU/ovulation anchor
    generated_at  = Column(DateTime(timezone=True))
    document      = Column(JSONB, nullable=False)                  # full generator payload
    is_active     = Column(Boolean, default=True, nullable=False)
    created_by    = Column(UUID, ForeignKey("users.id"))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    files = relationship("CycleTimelineFile", back_populates="timeline", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_cycle_timelines_hn_type", "hn", "cycle_type"),)


class CycleTimelineFile(Base):
    """Rendered JPG / PDF exports of a timeline (stored on the uploads volume)."""
    __tablename__ = "cycle_timeline_files"

    id          = Column(UUID, primary_key=True, default=gen_uuid)
    timeline_id = Column(UUID, ForeignKey("cycle_timelines.id", ondelete="CASCADE"), nullable=False, index=True)
    kind        = Column(String(10), nullable=False)   # jpg | pdf
    filename    = Column(String(255), nullable=False)
    path        = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    timeline = relationship("CycleTimeline", back_populates="files")
