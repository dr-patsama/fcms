"""
One-time script: create the initial admin user.
"""
import sys
sys.path.insert(0, ".")

from module1.backend.core.database import SessionLocal
from module1.backend.core.security import hash_password, verify_password
from module1.backend.models.user_models import User

EMAIL    = "admin@fcms.com"
PASSWORD = "admin123"
ROLE     = "admin"

db = SessionLocal()

existing = db.query(User).filter(User.email == EMAIL).first()
if existing:
    print(f"User '{EMAIL}' already exists — skipping insert.")
else:
    admin = User(
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        first_name_en="System",
        last_name_en="Admin",
        first_name_th="ผู้ดูแล",
        last_name_th="ระบบ",
        role=ROLE,
        is_active=True,
        is_mfa_enabled=False,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"Admin user created successfully.")

# Query back and display
user = db.query(User).filter(User.email == EMAIL).first()
print()
print("=" * 50)
print("  ADMIN USER")
print("=" * 50)
print(f"  UUID       {user.id}")
print(f"  Email      {user.email}")
print(f"  Name (EN)  {user.first_name_en} {user.last_name_en}")
print(f"  Name (TH)  {user.first_name_th} {user.last_name_th}")
print(f"  Role       {user.role}")
print(f"  Active     {user.is_active}")
print(f"  MFA        {user.is_mfa_enabled}")
print(f"  Created    {user.created_at}")
print("=" * 50)

# Verify the password hash works
assert verify_password(PASSWORD, user.password_hash), "Password verification FAILED!"
print(f"\n  Password hash verified OK.")
print(f"  Hash: {user.password_hash[:40]}...")

db.close()
