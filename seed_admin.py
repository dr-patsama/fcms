"""
FCMS — Seed Default Admin User
Run once after database migration to create initial admin account.

Usage:
    cd fcms
    source backend/.venv/bin/activate
    python seed_admin.py

Default credentials:
    Email:    admin@lifeclinic.com
    Password: LifeByDrPat2026!
"""

import sys
import os
import uuid
from datetime import datetime, timezone

# Adjust path to import from module1 backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "module1", "backend"))

from core.database import SessionLocal, engine, Base
from core.security import hash_password
from models.user_models import User


def seed():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == "admin").first()
        if existing:
            print(f"✅ Admin already exists: {existing.email}")
            return

        admin = User(
            id=str(uuid.uuid4()),
            email="admin@lifeclinic.com",
            password_hash=hash_password("LifeByDrPat2026!"),
            first_name_en="System",
            last_name_en="Administrator",
            first_name_th="ผู้ดูแล",
            last_name_th="ระบบ",
            role="admin",
            department="IT",
            is_active=True,
            is_mfa_enabled=False,
            failed_login_count=0,
            password_changed_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

        print("=" * 50)
        print("  ✅ Default Admin Account Created")
        print("=" * 50)
        print(f"  Email    : admin@lifeclinic.com")
        print(f"  Password : LifeByDrPat2026!")
        print(f"  Role     : System Administrator")
        print("=" * 50)
        print("  ⚠️  CHANGE THIS PASSWORD after first login!")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
