"""
FCMS Module 1 - Auth Dependencies
FastAPI dependency injection for authentication & RBAC
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from .security import decode_access_token
from .database import get_db

security_scheme = HTTPBearer()

# ─── 15 USER ROLES ──────────────────────────────────────

SYSTEM_ROLES = {
    "admin":            {"level": 100, "modules": ["*"]},
    "physician":        {"level": 90,  "modules": ["emr", "lab", "ultrasound", "pharmacy", "or", "crm"]},
    "embryologist":     {"level": 85,  "modules": ["emr", "lab", "ultrasound", "or"]},
    "lab_supervisor":   {"level": 80,  "modules": ["lab"]},
    "lab_technician":   {"level": 70,  "modules": ["lab"]},
    "nurse":            {"level": 70,  "modules": ["emr", "lab", "ultrasound", "pharmacy", "or", "crm"]},
    "sonographer":      {"level": 65,  "modules": ["ultrasound"]},
    "pharmacist":       {"level": 65,  "modules": ["pharmacy"]},
    "pharmacy_staff":   {"level": 55,  "modules": ["pharmacy", "supplies"]},
    "supply_manager":   {"level": 60,  "modules": ["supplies"]},
    "receptionist":     {"level": 50,  "modules": ["emr", "crm"]},
    "billing_staff":    {"level": 50,  "modules": ["accounting"]},
    "marketing_staff":  {"level": 40,  "modules": ["social_media", "crm"]},
    "it_admin":         {"level": 95,  "modules": ["*"]},
    "patient":          {"level": 10,  "modules": ["patient_portal"]},
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
):
    """Decode JWT and return current user"""
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from ..models.user_models import User
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(allowed_roles: List[str]):
    """Dependency factory: restrict endpoint to specific roles"""
    async def _check(
        credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
        db: Session = Depends(get_db)
    ):
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            role = payload.get("role")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        if role not in allowed_roles and role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        from ..models.user_models import User
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    return _check


def require_module_access(module_name: str):
    """Dependency factory: restrict endpoint to users with module access"""
    async def _check(
        credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
        db: Session = Depends(get_db)
    ):
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            role = payload.get("role")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

        role_config = SYSTEM_ROLES.get(role)
        if not role_config:
            raise HTTPException(status_code=403, detail="Unknown role")

        if "*" not in role_config["modules"] and module_name not in role_config["modules"]:
            raise HTTPException(status_code=403, detail=f"No access to {module_name} module")

        from ..models.user_models import User
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    return _check
