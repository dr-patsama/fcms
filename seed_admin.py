"""
FCMS — Seed default users (one per role) so hierarchical login can be tested.
Run from repo root after `alembic upgrade head`:
    PYTHONPATH=. python seed_admin.py            # admin only
    PYTHONPATH=. python seed_admin.py --all      # admin + one demo user per role
Passwords are read from env SEED_ADMIN_PASSWORD / SEED_DEMO_PASSWORD (defaults below).
"""
import os, sys, uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from module1.backend.core.database import SessionLocal
from module1.backend.core.security import hash_password
from module1.backend.core.auth import SYSTEM_ROLES
from module1.backend.models.user_models import User

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@lifeclinic.com")
ADMIN_PW    = os.getenv("SEED_ADMIN_PASSWORD", "LifeByDrPat2026!")
DEMO_PW     = os.getenv("SEED_DEMO_PASSWORD", "Fcms2026!")

TH_NAMES = {
    "admin": ("ผู้ดูแล", "ระบบ"), "it_admin": ("ไอที", "ผู้ดูแล"), "physician": ("แพทย์", "ตัวอย่าง"),
    "embryologist": ("นักวิทย์", "ตัวอ่อน"), "lab_supervisor": ("หัวหน้า", "ห้องแล็บ"),
    "lab_technician": ("เทคนิค", "ห้องแล็บ"), "nurse": ("พยาบาล", "ตัวอย่าง"), "sonographer": ("อัลตราซาวด์", "ตัวอย่าง"),
    "pharmacist": ("เภสัชกร", "ตัวอย่าง"), "pharmacy_staff": ("เจ้าหน้าที่", "ห้องยา"), "supply_manager": ("ผู้จัดการ", "เวชภัณฑ์"),
    "receptionist": ("ต้อนรับ", "ตัวอย่าง"), "billing_staff": ("การเงิน", "ตัวอย่าง"), "marketing_staff": ("การตลาด", "ตัวอย่าง"),
    "patient": ("ผู้ป่วย", "ตัวอย่าง"),
}

def upsert(db, email, pw, role, dept):
    u = db.query(User).filter(User.email == email).first()
    if u:
        return False
    th = TH_NAMES.get(role, (role, "ตัวอย่าง"))
    db.add(User(id=uuid.uuid4(), email=email, password_hash=hash_password(pw),
                first_name_en=role.replace("_", " ").title(), last_name_en="Demo",
                first_name_th=th[0], last_name_th=th[1], role=role, department=dept,
                is_active=True, is_mfa_enabled=False, failed_login_count=0,
                password_changed_at=datetime.now(timezone.utc)))
    return True

def seed(all_roles: bool):
    db = SessionLocal()
    try:
        created = []
        if upsert(db, ADMIN_EMAIL, ADMIN_PW, "admin", "IT"):
            created.append(("admin", ADMIN_EMAIL))
        if all_roles:
            for role in SYSTEM_ROLES:
                if role == "admin":
                    continue
                email = f"{role}@lifeclinic.com"
                if upsert(db, email, DEMO_PW, role, role):
                    created.append((role, email))
        db.commit()
        print("Seeded users (level = hierarchy rank):")
        for role, email in created:
            print(f"  {SYSTEM_ROLES[role]['level']:>3}  {role:<16} {email}")
        if not created:
            print("  (nothing new — users already exist)")
        print("⚠️  Change default passwords after first login.")
    finally:
        db.close()

if __name__ == "__main__":
    seed("--all" in sys.argv)
