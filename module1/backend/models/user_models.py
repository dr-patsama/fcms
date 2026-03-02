"""
FCMS Module 1 - User & Authentication Models
15 role types, MFA support, session tracking
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid


def gen_uuid():
    return str(uuid.uuid4())


from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(UUID, primary_key=True, default=gen_uuid)
    email           = Column(String(200), unique=True, nullable=False)
    password_hash   = Column(String(200), nullable=False)
    first_name_en   = Column(String(100), nullable=False)
    last_name_en    = Column(String(100), nullable=False)
    first_name_th   = Column(String(100))
    last_name_th    = Column(String(100))
    role            = Column(String(30), nullable=False)  # matches SYSTEM_ROLES keys
    license_number  = Column(String(50))      # medical license for physicians
    department      = Column(String(100))
    phone           = Column(String(20))
    avatar_url      = Column(String(500))
    is_active       = Column(Boolean, default=True)
    is_mfa_enabled  = Column(Boolean, default=False)
    mfa_secret      = Column(String(64))
    last_login_at   = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    failed_login_count  = Column(Integer, default=0)
    locked_until    = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    created_by      = Column(UUID, ForeignKey("users.id"))

    sessions    = relationship("UserSession", back_populates="user")
    audit_logs  = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id          = Column(UUID, primary_key=True, default=gen_uuid)
    user_id     = Column(UUID, ForeignKey("users.id"), nullable=False)
    token_jti   = Column(String(64), unique=True, nullable=False)
    ip_address  = Column(String(45))
    user_agent  = Column(String(500))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    revoked_at  = Column(DateTime(timezone=True))
    is_active   = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """Full audit trail for PDPA compliance"""
    __tablename__ = "audit_logs"

    id            = Column(UUID, primary_key=True, default=gen_uuid)
    user_id       = Column(UUID, ForeignKey("users.id"))
    action        = Column(String(20), nullable=False)  # CREATE | READ | UPDATE | DELETE | LOGIN | LOGOUT
    module        = Column(String(30))                   # emr | lab | pharmacy etc.
    resource_type = Column(String(50))
    resource_id   = Column(String(50))
    detail        = Column(Text)
    ip_address    = Column(String(45))
    user_agent    = Column(String(500))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user",       "user_id"),
        Index("ix_audit_module",     "module"),
        Index("ix_audit_created_at", "created_at"),
    )
