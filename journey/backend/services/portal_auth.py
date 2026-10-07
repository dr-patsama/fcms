"""
Patient-app authentication.
  • LINE Login via LIFF: the app sends the LIFF ID token → verified with LINE → `sub` is the LINE user id.
    First time: the patient proves identity with HN + date of birth (or phone) → account linked.
  • OTP fallback: phone (or e-mail) → 6-digit code via SMS/LINE/e-mail → patient JWT.
Patient JWT = Module 1 token with role "patient" + patient_id claim, 30-day expiry.
"""
from __future__ import annotations

import secrets
from datetime import timedelta, datetime, timezone

import httpx
import jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from module1.backend.core.config import settings
from module1.backend.core.database import get_db
from module1.backend.core.security import hash_password, verify_password
from module1.backend.models.emr_models import Patient

from ..core.config import jsettings
from ..models.journey_models import PatientAccount
from . import notifications
from .common import now, parse_date

bearer = HTTPBearer(auto_error=False)


def issue_patient_token(patient_id: str, account_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=jsettings.PATIENT_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(account_id), "role": "patient", "patient_id": str(patient_id), "exp": exp,
               "iat": datetime.now(timezone.utc), "jti": secrets.token_hex(8)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def current_patient(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> Patient:
    if not creds:
        raise HTTPException(401, "Login required")
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    if payload.get("role") != "patient" or not payload.get("patient_id"):
        raise HTTPException(403, "Patient token required")
    acct = db.query(PatientAccount).filter(PatientAccount.id == payload["sub"], PatientAccount.is_active == True).first()
    if not acct:
        raise HTTPException(401, "Account not found")
    p = db.query(Patient).filter(Patient.id == payload["patient_id"], Patient.is_active == True).first()
    if not p:
        raise HTTPException(401, "Patient not found")
    return p


def _account_for(db: Session, patient: Patient) -> PatientAccount:
    acct = db.query(PatientAccount).filter(PatientAccount.patient_id == patient.id).first()
    if not acct:
        acct = PatientAccount(patient_id=patient.id, phone=patient.phone, email=patient.email,
                              language=patient.preferred_language or "th")
        db.add(acct)
        db.flush()
    return acct


def _find_patient(db: Session, hn: str | None, dob, phone: str | None) -> Patient:
    q = db.query(Patient).filter(Patient.is_active == True)
    if hn:
        q = q.filter(Patient.hn_number == hn.strip())
    elif phone:
        digits = "".join(ch for ch in phone if ch.isdigit())
        q = q.filter(Patient.phone.like(f"%{digits[-9:]}"))
    else:
        raise HTTPException(400, "hn or phone required")
    cands = q.all()
    d = parse_date(dob) if dob else None
    if d:
        cands = [p for p in cands if p.date_of_birth == d]
    if len(cands) != 1:
        raise HTTPException(404, "We could not match these details. Please contact the clinic. / ไม่พบข้อมูลที่ตรงกัน กรุณาติดต่อคลินิก")
    return cands[0]


# ── LINE ─────────────────────────────────────────────────────────────────────
def verify_line_id_token(id_token: str) -> dict:
    if not jsettings.LINE_LOGIN_CHANNEL_ID:
        raise HTTPException(503, "LINE Login is not configured on this server")
    r = httpx.post("https://api.line.me/oauth2/v2.1/verify",
                   data={"id_token": id_token, "client_id": jsettings.LINE_LOGIN_CHANNEL_ID}, timeout=10)
    if r.status_code != 200:
        raise HTTPException(401, f"LINE token invalid: {r.text[:120]}")
    return r.json()   # {sub, name, picture, email?, ...}


def line_login(db: Session, id_token: str, *, hn: str | None = None, dob=None, phone: str | None = None) -> dict:
    info = verify_line_id_token(id_token)
    line_uid = info["sub"]
    acct = db.query(PatientAccount).filter(PatientAccount.line_user_id == line_uid).first()
    if not acct:
        if not (hn or phone):
            return {"status": "link_required", "line_display_name": info.get("name")}
        p = _find_patient(db, hn, dob, phone)
        acct = _account_for(db, p)
        acct.line_user_id, acct.line_display_name = line_uid, info.get("name")
    acct.last_login_at = now()
    db.commit()
    return {"status": "ok", "access_token": issue_patient_token(acct.patient_id, acct.id), "patient_id": acct.patient_id}


# ── OTP ───────────────────────────────────────────────────────────────────────
def request_otp(db: Session, *, hn: str | None, dob, phone: str | None, channel: str = "sms") -> dict:
    p = _find_patient(db, hn, dob, phone)
    acct = _account_for(db, p)
    code = f"{secrets.randbelow(10**6):06d}"
    acct.otp_hash = hash_password(code)
    acct.otp_expires_at = now() + timedelta(minutes=jsettings.OTP_EXPIRE_MINUTES)
    acct.otp_attempts = 0
    db.flush()
    text_en = f"{jsettings.CLINIC_NAME_EN}: your login code is {code} (valid {jsettings.OTP_EXPIRE_MINUTES} min)."
    text_th = f"{jsettings.CLINIC_NAME_TH}: รหัสเข้าสู่ระบบของคุณคือ {code} (ใช้ได้ {jsettings.OTP_EXPIRE_MINUTES} นาที)"
    results = {}
    try:
        if channel == "sms":
            results["sms"] = notifications._sms(p.phone or "", text_th if (p.preferred_language or "th") == "th" else text_en) if p.phone else "skipped: no phone"
        elif channel == "email":
            results["email"] = notifications._email(p.email, "Login code", text_en) if p.email else "skipped: no email"
        elif channel == "line" and acct.line_user_id:
            results["line"] = notifications._line_push(acct.line_user_id, text_th)
    except Exception as e:
        results[channel] = f"error: {type(e).__name__}"
    db.commit()
    out = {"status": "sent", "account_id": acct.id, "channels": results, "expires_in_minutes": jsettings.OTP_EXPIRE_MINUTES}
    delivered = any(v == "sent" for v in results.values())
    if not delivered and (jsettings.OTP_DEV_ECHO or settings.DEBUG):
        out["dev_code"] = code   # no messaging channel configured yet — surface the code so the flow can be tested
    return out


def verify_otp(db: Session, account_id: str, code: str) -> dict:
    acct = db.query(PatientAccount).filter(PatientAccount.id == account_id).first()
    if not acct or not acct.otp_hash or not acct.otp_expires_at:
        raise HTTPException(400, "No code requested")
    if acct.otp_expires_at < now():
        raise HTTPException(400, "Code expired")
    if (acct.otp_attempts or 0) >= 5:
        raise HTTPException(429, "Too many attempts")
    if not verify_password(code, acct.otp_hash):
        acct.otp_attempts = (acct.otp_attempts or 0) + 1
        db.commit()
        raise HTTPException(401, "Incorrect code")
    acct.otp_hash, acct.otp_expires_at, acct.last_login_at = None, None, now()
    db.commit()
    return {"status": "ok", "access_token": issue_patient_token(acct.patient_id, acct.id), "patient_id": acct.patient_id}
