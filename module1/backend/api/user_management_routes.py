"""
FCMS — User Management Routes
Admin panel for managing staff accounts, roles, and permissions.
Only accessible by admin and it_admin roles.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, SYSTEM_ROLES
from ..core.security import hash_password, verify_password
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


# ── Helper: audit log ──────────────────────────────────────
def _audit(db: Session, user, action: str, resource_id: str = None,
           detail: str = None, request: Request = None):
    log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user.id if user else None,
        action=action,
        module="admin",
        resource_type="user",
        resource_id=resource_id,
        detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


# ── Helper: serialize user ─────────────────────────────────
def _user_out(user: User) -> dict:
    role_config = SYSTEM_ROLES.get(user.role, {})
    modules = role_config.get("modules", [])
    if "*" in modules:
        modules = ["emr", "lab", "ultrasound", "pharmacy", "supplies",
                   "crm", "accounting", "social_media", "webmaster",
                   "calculator", "certificate", "or", "admin"]
    return {
        "id": user.id,
        "email": user.email,
        "first_name_en": user.first_name_en,
        "last_name_en": user.last_name_en,
        "first_name_th": user.first_name_th,
        "last_name_th": user.last_name_th,
        "full_name_en": f"{user.first_name_en} {user.last_name_en}",
        "full_name_th": f"{user.first_name_th or ''} {user.last_name_th or ''}".strip() or None,
        "role": user.role,
        "role_level": role_config.get("level", 0),
        "phone": user.phone,
        "license_number": user.license_number,
        "department": user.department,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "is_mfa_enabled": user.is_mfa_enabled,
        "modules": modules,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "failed_login_count": user.failed_login_count or 0,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


# ══════════════════════════════════════════════════════════
# LIST USERS (paginated, searchable, filterable)
# ══════════════════════════════════════════════════════════
@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    department: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|last_login_at|first_name_en|role|email)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """List all users with pagination, search, and filters."""
    query = db.query(User)

    # Search across name, email
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            User.first_name_en.ilike(term),
            User.last_name_en.ilike(term),
            User.first_name_th.ilike(term),
            User.last_name_th.ilike(term),
            User.email.ilike(term),
            User.phone.ilike(term),
        ))

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if department:
        query = query.filter(User.department.ilike(f"%{department}%"))

    total = query.count()

    # Sort
    sort_col = getattr(User, sort_by, User.created_at)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else sort_col)

    # Paginate
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()

    return {
        "users": [_user_out(u) for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ══════════════════════════════════════════════════════════
# GET SINGLE USER
# ══════════════════════════════════════════════════════════
@router.get("/roles")
async def list_roles(
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
):
    """Return all available roles with their module access."""
    roles = []
    for role_key, config in SYSTEM_ROLES.items():
        modules = config["modules"]
        if "*" in modules:
            modules = ["emr", "lab", "ultrasound", "pharmacy", "supplies",
                       "crm", "accounting", "social_media", "webmaster",
                       "calculator", "certificate", "or", "admin"]
        roles.append({
            "value": role_key,
            "level": config["level"],
            "modules": modules,
        })
    return {"roles": sorted(roles, key=lambda r: r["level"], reverse=True)}


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Get a single user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)


# ══════════════════════════════════════════════════════════
# CREATE USER
# ══════════════════════════════════════════════════════════
@router.post("", status_code=201)
async def create_user(
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Create a new user account."""
    body = await request.json()

    # Validate required fields
    required = ["email", "password", "first_name_en", "last_name_en", "role"]
    for field in required:
        if not body.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")

    # Validate role
    if body["role"] not in SYSTEM_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body['role']}")

    # Check email uniqueness
    if db.query(User).filter(User.email == body["email"]).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate password strength
    pw = body["password"]
    if len(pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    new_id = str(uuid.uuid4())
    user = User(
        id=new_id,
        email=body["email"].lower().strip(),
        password_hash=hash_password(pw),
        first_name_en=body["first_name_en"].strip(),
        last_name_en=body["last_name_en"].strip(),
        first_name_th=body.get("first_name_th", "").strip() or None,
        last_name_th=body.get("last_name_th", "").strip() or None,
        role=body["role"],
        phone=body.get("phone"),
        license_number=body.get("license_number"),
        department=body.get("department"),
        is_active=body.get("is_active", True),
        is_mfa_enabled=False,
        failed_login_count=0,
        created_by=current_user.id,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)

    _audit(db, current_user, "CREATE", new_id,
           f"Created user {body['email']} with role {body['role']}", request)
    db.commit()
    db.refresh(user)

    return _user_out(user)


# ══════════════════════════════════════════════════════════
# UPDATE USER
# ══════════════════════════════════════════════════════════
@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Update user details (not password)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deactivating yourself
    body = await request.json()
    if user_id == str(current_user.id) and body.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    # Prevent demoting yourself
    if user_id == str(current_user.id) and body.get("role") and body["role"] != current_user.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    updatable = [
        "email", "first_name_en", "last_name_en", "first_name_th", "last_name_th",
        "role", "phone", "license_number", "department", "is_active", "avatar_url"
    ]

    changes = []
    for field in updatable:
        if field in body:
            old_val = getattr(user, field)
            new_val = body[field]
            if field == "role" and new_val not in SYSTEM_ROLES:
                raise HTTPException(status_code=400, detail=f"Invalid role: {new_val}")
            if field == "email":
                new_val = new_val.lower().strip()
                existing = db.query(User).filter(User.email == new_val, User.id != user_id).first()
                if existing:
                    raise HTTPException(status_code=409, detail="Email already in use")
            setattr(user, field, new_val)
            if old_val != new_val:
                changes.append(f"{field}: {old_val} → {new_val}")

    if changes:
        _audit(db, current_user, "UPDATE", user_id,
               f"Updated: {'; '.join(changes)}", request)
        db.commit()
        db.refresh(user)

    return _user_out(user)


# ══════════════════════════════════════════════════════════
# RESET PASSWORD (admin action)
# ══════════════════════════════════════════════════════════
@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Admin resets a user's password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    body = await request.json()
    new_pw = body.get("new_password")
    if not new_pw or len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(new_pw)
    user.password_changed_at = datetime.now(timezone.utc)
    user.failed_login_count = 0
    user.locked_until = None

    _audit(db, current_user, "UPDATE", user_id,
           f"Password reset for {user.email}", request)
    db.commit()

    return {"message": f"Password reset for {user.email}"}


# ══════════════════════════════════════════════════════════
# TOGGLE ACTIVE STATUS
# ══════════════════════════════════════════════════════════
@router.post("/{user_id}/toggle-active")
async def toggle_active(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Enable or disable a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = not user.is_active
    action = "activated" if user.is_active else "deactivated"

    _audit(db, current_user, "UPDATE", user_id,
           f"User {user.email} {action}", request)
    db.commit()

    return {"message": f"User {action}", "is_active": user.is_active}


# ══════════════════════════════════════════════════════════
# UNLOCK ACCOUNT
# ══════════════════════════════════════════════════════════
@router.post("/{user_id}/unlock")
async def unlock_account(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Unlock a locked user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.failed_login_count = 0
    user.locked_until = None

    _audit(db, current_user, "UPDATE", user_id,
           f"Account unlocked for {user.email}", request)
    db.commit()

    return {"message": f"Account unlocked for {user.email}"}


# ══════════════════════════════════════════════════════════
# RESET MFA
# ══════════════════════════════════════════════════════════
@router.post("/{user_id}/reset-mfa")
async def reset_mfa(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Reset MFA for a user (they will need to re-enroll)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_mfa_enabled = False
    user.mfa_secret = None

    _audit(db, current_user, "UPDATE", user_id,
           f"MFA reset for {user.email}", request)
    db.commit()

    return {"message": f"MFA reset for {user.email}"}


# ══════════════════════════════════════════════════════════
# USER ACTIVITY LOG
# ══════════════════════════════════════════════════════════
@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Get activity/audit log for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
    total = query.count()

    offset = (page - 1) * per_page
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(per_page).all()

    return {
        "user_id": user_id,
        "user_email": user.email,
        "total": total,
        "page": page,
        "per_page": per_page,
        "logs": [{
            "id": log.id,
            "action": log.action,
            "module": log.module,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
        } for log in logs],
    }


# ══════════════════════════════════════════════════════════
# DASHBOARD STATS
# ══════════════════════════════════════════════════════════
@router.get("/stats/overview")
async def user_stats(
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
    db: Session = Depends(get_db),
):
    """Get user management dashboard stats."""
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    inactive = total - active
    locked = db.query(User).filter(User.locked_until != None).count()
    mfa_enabled = db.query(User).filter(User.is_mfa_enabled == True).count()

    # Users by role
    role_counts = db.query(User.role, func.count(User.id))\
        .group_by(User.role).all()

    # Users by department
    dept_counts = db.query(User.department, func.count(User.id))\
        .filter(User.department != None)\
        .group_by(User.department).all()

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "locked": locked,
        "mfa_enabled": mfa_enabled,
        "mfa_percentage": round((mfa_enabled / total * 100) if total > 0 else 0, 1),
        "by_role": {role: count for role, count in role_counts},
        "by_department": {dept or "Unassigned": count for dept, count in dept_counts},
    }
