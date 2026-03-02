"""
FCMS Module 1 - Core Configuration & Security
Database connection, JWT auth, RBAC, password hashing
"""

# ═══════════════════════════════════════════════════════════
# config.py
# ═══════════════════════════════════════════════════════════

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "FCMS - Fertility Clinic Management System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://fcms_user:fcms_pass@localhost:5432/fcms_db"

    # JWT
    SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # MFA
    MFA_REQUIRED_ROLES: List[str] = ["physician", "embryologist", "lab_supervisor", "admin"]

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
