"""
FCMS Module 1 - API Routes
Auth, Patients, Visits, SOAP Notes, Diagnoses
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access, SYSTEM_ROLES
from ..core.security import (
    hash_password, verify_password, create_access_token,
    generate_mfa_secret, get_mfa_uri, verify_mfa_code
)
from ..models.user_models import User, UserSession, AuditLog
from ..models.emr_models import (
    Patient, MedicalHistory, FertilityHistory,
    Visit, SOAPNote, VisitDiagnosis, ConsentForm
)
from ..schemas.emr_schemas import (
    LoginRequest, TokenResponse, UserCreate, UserOut,
    PasswordChange, MFASetupResponse,
    PatientCreate, PatientUpdate, PatientOut, PatientSearch,
    MedicalHistoryUpdate, FertilityHistoryUpdate,
    VisitCreate, VisitOut, SOAPNoteCreate, SOAPNoteOut,
    DiagnosisCreate
)


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _gen_hn(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Patient).filter(Patient.hn_number.like(f"HN-{year}-%")).count()
    return f"HN-{year}-{count + 1:05d}"

def _gen_visit(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Visit).filter(Visit.visit_number.like(f"V-{year}-%")).count()
    return f"V-{year}-{count + 1:05d}"


@auth_router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            db.commit()
        raise HTTPException(401, "Invalid credentials")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(423, "Account locked")

    # MFA check
    if user.is_mfa_enabled:
        if not data.mfa_code:
            raise HTTPException(428, "MFA code required")
        if not verify_mfa_code(user.mfa_secret, data.mfa_code):
            raise HTTPException(401, "Invalid MFA code")

    token = create_access_token(str(user.id), user.role)
    user.last_login_at = datetime.now(timezone.utc)
    user.failed_login_count = 0

    # Audit
    db.add(AuditLog(
        user_id=user.id, action="LOGIN", module="auth",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "")[:500]
    ))
    db.commit()

    return TokenResponse(
        access_token=token, role=user.role,
        user_id=str(user.id),
        name=f"{user.first_name_en} {user.last_name_en}"
    )


@auth_router.post("/register", response_model=UserOut, status_code=201)
async def register_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "it_admin"]))
):
    if data.role not in SYSTEM_ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {list(SYSTEM_ROLES.keys())}")
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(409, "Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name_en=data.first_name_en,
        last_name_en=data.last_name_en,
        first_name_th=data.first_name_th,
        last_name_th=data.last_name_th,
        role=data.role,
        license_number=data.license_number,
        department=data.department,
        phone=data.phone,
        created_by=current_user.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@auth_router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    secret = generate_mfa_secret()
    current_user.mfa_secret = secret
    current_user.is_mfa_enabled = True
    db.commit()
    return MFASetupResponse(secret=secret, uri=get_mfa_uri(secret, current_user.email))


@auth_router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


# ═══════════════════════════════════════════════════════════
# PATIENTS
# ═══════════════════════════════════════════════════════════

patient_router = APIRouter(prefix="/api/v1/patients", tags=["Patients - EMR"])


@patient_router.post("/", response_model=PatientOut, status_code=201)
async def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    patient = Patient(
        hn_number=_gen_hn(db),
        **data.model_dump(),
        created_by=current_user.id
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@patient_router.get("/", response_model=List[PatientOut])
async def list_patients(
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    query = db.query(Patient).filter(Patient.is_active == True)
    if q:
        query = query.filter(or_(
            Patient.hn_number.ilike(f"%{q}%"),
            Patient.first_name_en.ilike(f"%{q}%"),
            Patient.last_name_en.ilike(f"%{q}%"),
            Patient.first_name_th.ilike(f"%{q}%"),
            Patient.last_name_th.ilike(f"%{q}%"),
            Patient.phone.ilike(f"%{q}%"),
            Patient.id_number.ilike(f"%{q}%"),
        ))
    return query.order_by(desc(Patient.created_at)).offset((page - 1) * per_page).limit(per_page).all()


@patient_router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    p = db.query(Patient).filter(Patient.id == str(patient_id)).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


@patient_router.patch("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    p = db.query(Patient).filter(Patient.id == str(patient_id)).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(p, key, val)
    db.commit()
    db.refresh(p)
    return p


@patient_router.put("/{patient_id}/medical-history")
async def update_medical_history(
    patient_id: uuid.UUID,
    data: MedicalHistoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "nurse"]))
):
    mh = db.query(MedicalHistory).filter(MedicalHistory.patient_id == str(patient_id)).first()
    if not mh:
        mh = MedicalHistory(patient_id=str(patient_id))
        db.add(mh)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(mh, key, val)
    db.commit()
    return {"status": "updated"}


@patient_router.put("/{patient_id}/fertility-history")
async def update_fertility_history(
    patient_id: uuid.UUID,
    data: FertilityHistoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "nurse", "embryologist"]))
):
    fh = db.query(FertilityHistory).filter(FertilityHistory.patient_id == str(patient_id)).first()
    if not fh:
        fh = FertilityHistory(patient_id=str(patient_id))
        db.add(fh)
    for key, val in data.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(fh, key, str(val) if isinstance(val, uuid.UUID) else val)
    db.commit()
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════
# VISITS
# ═══════════════════════════════════════════════════════════

visit_router = APIRouter(prefix="/api/v1/visits", tags=["Visits - EMR"])


@visit_router.post("/", response_model=VisitOut, status_code=201)
async def create_visit(
    data: VisitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    visit = Visit(
        visit_number=_gen_visit(db),
        patient_id=str(data.patient_id),
        physician_id=str(data.physician_id) if data.physician_id else None,
        visit_type=data.visit_type,
        chief_complaint=data.chief_complaint,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@visit_router.get("/patient/{patient_id}", response_model=List[VisitOut])
async def list_patient_visits(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    return db.query(Visit).filter(
        Visit.patient_id == str(patient_id)
    ).order_by(desc(Visit.visit_date)).all()


@visit_router.patch("/{visit_id}/status")
async def update_visit_status(
    visit_id: uuid.UUID,
    new_status: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_module_access("emr"))
):
    visit = db.query(Visit).filter(Visit.id == str(visit_id)).first()
    if not visit:
        raise HTTPException(404, "Visit not found")
    visit.status = new_status
    if new_status == "completed":
        visit.checkout_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": new_status}


@visit_router.post("/soap-notes", response_model=SOAPNoteOut, status_code=201)
async def create_soap_note(
    data: SOAPNoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician", "nurse"]))
):
    note = SOAPNote(
        visit_id=str(data.visit_id),
        author_id=current_user.id,
        subjective=data.subjective,
        objective=data.objective,
        assessment=data.assessment,
        plan=data.plan,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@visit_router.patch("/soap-notes/{note_id}/sign")
async def sign_soap_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician"]))
):
    note = db.query(SOAPNote).filter(SOAPNote.id == str(note_id)).first()
    if not note:
        raise HTTPException(404, "Note not found")
    note.is_signed = True
    note.signed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "signed"}


@visit_router.post("/diagnoses", status_code=201)
async def add_diagnosis(
    data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["physician"]))
):
    dx = VisitDiagnosis(
        visit_id=str(data.visit_id),
        icd10_code=data.icd10_code,
        description=data.description,
        is_primary=data.is_primary,
        notes=data.notes,
    )
    db.add(dx)
    db.commit()
    db.refresh(dx)
    return dx

