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

    # MFA — comma-separated in .env (declared as str so pydantic-settings does not try to JSON-decode it); split to a list in __init__
    MFA_REQUIRED_ROLES: str = "physician,embryologist,lab_supervisor,admin"

    # CORS — comma-separated in .env, e.g. CORS_ORIGINS=http://localhost:8000,http://192.168.1.10:8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 50

    @classmethod
    def _split(cls, v):
        """Accept 'a,b' or a JSON list '["a","b"]' from .env; return a clean list."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return [str(x).strip() for x in json.loads(v)]
            return [x.strip() for x in v.split(",") if x.strip()]
        return list(v)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.CORS_ORIGINS = self._split(self.CORS_ORIGINS)
        self.MFA_REQUIRED_ROLES = self._split(self.MFA_REQUIRED_ROLES)

settings = Settings()
