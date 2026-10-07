"""
Patient App API (/api/v1/portal) — the CareU equivalent on LINE Mini App + PWA.
Login: LINE (LIFF id token) or OTP. Everything else requires the patient JWT.
Only released / verified clinical content is exposed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import desc
from sqlalchemy.orm import Session

from module1.backend.core.database import get_db
from module1.backend.models.emr_models import Patient
from module1.backend.models.user_models import User
from module2.backend.models.lab_models import TreatmentCycle, LabOrder, LabOrderItem, LabResult, LabTestPanel, OrderStatus
from module6.backend.models.crm_models import Appointment
from module7.backend.models.accounting_models import Invoice, Payment

from ..core.config import jsettings
from ..models.journey_models import (
    CycleDay, CycleMedication, CycleMedicationDose, CycleMonitoring, CycleConsent, ConsentTemplate, CycleOutcome,
    EmbryoPhoto, CryoStorageTerm, PatientNotification, PortalBookingRequest, PatientAccount, TreatmentPackage,
)
from ..services import portal_auth as pa, cycles as cyc, consents as cons, cryo, report as rpt, promptpay
from ..services.common import row, rows, now, today, parse_date, parse_time, patient_name, age_years, TZ

router = APIRouter(prefix="/api/v1/portal", tags=["Patient App (portal)"])


# ── Config & auth ─────────────────────────────────────────────────────────────
@router.get("/config")
def config():
    return {"clinic_en": jsettings.CLINIC_NAME_EN, "clinic_th": jsettings.CLINIC_NAME_TH, "phone": jsettings.CLINIC_PHONE,
            "liff_id": jsettings.LINE_LIFF_ID, "line_login": bool(jsettings.LINE_LOGIN_CHANNEL_ID),
            "otp_channels": [c for c, ok in (("sms", (jsettings.SMS_PROVIDER or "none") != "none"), ("email", bool(jsettings.SMTP_HOST))) if ok] or ["sms"],
            "promptpay": bool(jsettings.PROMPTPAY_ID)}


@router.post("/auth/line")
async def auth_line(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    return pa.line_login(db, b.get("id_token", ""), hn=b.get("hn"), dob=b.get("dob"), phone=b.get("phone"))


@router.post("/auth/otp/request")
async def otp_request(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    return pa.request_otp(db, hn=b.get("hn"), dob=b.get("dob"), phone=b.get("phone"), channel=b.get("channel", "sms"))


@router.post("/auth/otp/verify")
async def otp_verify(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    return pa.verify_otp(db, b.get("account_id", ""), b.get("code", ""))


# ── Me / home ─────────────────────────────────────────────────────────────────
def _active_cycle(db: Session, p: Patient) -> TreatmentCycle | None:
    ids = [p.id]
    partner = cyc.partner_of(db, p.id)
    if partner:
        ids.append(partner.id)
    return (db.query(TreatmentCycle).filter(TreatmentCycle.patient_id.in_(ids), TreatmentCycle.status.notin_(("closed", "cancelled")))
            .order_by(desc(TreatmentCycle.created_at)).first())


def _cycles_for(db: Session, p: Patient):
    ids = [p.id]
    partner = cyc.partner_of(db, p.id)
    if partner:
        ids.append(partner.id)
    return db.query(TreatmentCycle).filter(TreatmentCycle.patient_id.in_(ids)).order_by(desc(TreatmentCycle.created_at)).all()


@router.get("/me")
def me(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    partner = cyc.partner_of(db, p.id)
    acct = db.query(PatientAccount).filter(PatientAccount.patient_id == p.id).first()
    return {"id": p.id, "hn": p.hn_number, "name_en": patient_name(p), "name_th": patient_name(p, "th"), "nickname": p.nickname_th or p.nickname_en,
            "language": (acct.language if acct else None) or p.preferred_language or "th", "line_linked": bool(acct and acct.line_user_id),
            "partner": {"name_en": patient_name(partner), "name_th": patient_name(partner, "th"), "hn": partner.hn_number} if partner else None}


@router.post("/me/language")
async def set_language(request: Request, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    b = await request.json()
    acct = db.query(PatientAccount).filter(PatientAccount.patient_id == p.id).first()
    if acct:
        acct.language = b.get("language", "th")
        db.commit()
    return {"language": acct.language if acct else "th"}


@router.get("/home")
def home(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    c = _active_cycle(db, p)
    t = today()
    doses_today = []
    if c:
        meds = {m.id: m for m in db.query(CycleMedication).filter(CycleMedication.cycle_id == c.id).all()}
        for d in db.query(CycleMedicationDose).filter(CycleMedicationDose.cycle_id == c.id, CycleMedicationDose.calendar_date == t).order_by(CycleMedicationDose.slot).all():
            m = meds.get(d.medication_id)
            doses_today.append({**row(d), "drug_en": m.drug_en if m else "", "drug_th": m.drug_th if m else "", "route": m.route if m else "",
                                "instructions_en": m.instructions_en if m else None, "instructions_th": m.instructions_th if m else None})
    next_appt = (db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.status.in_(("scheduled", "confirmed", "checked_in")),
                                              Appointment.appointment_date >= t).order_by(Appointment.appointment_date, Appointment.appointment_time).first())
    queue = None
    if next_appt and next_appt.appointment_date == t and next_appt.status == "checked_in":
        ahead = db.query(Appointment).filter(Appointment.appointment_date == t, Appointment.status == "checked_in",
                                             Appointment.queue_number != None, Appointment.queue_number < (next_appt.queue_number or 0)).count()
        queue = {"number": next_appt.queue_number, "ahead": ahead}
    day_index = (t - c.medication_start_date).days + 1 if c and c.medication_start_date else None
    lab_day = (t - c.d0_date).days if c and c.d0_date else None
    pending_consents = db.query(CycleConsent).filter(CycleConsent.patient_id == p.id, CycleConsent.status == "pending").count()
    unread = db.query(PatientNotification).filter(PatientNotification.patient_id == p.id, PatientNotification.read_at == None,
                                                  PatientNotification.sent_at != None).count()
    pkg = db.query(TreatmentPackage).filter(TreatmentPackage.id == c.package_id).first() if c and c.package_id else None
    return {"date": str(t), "cycle": {**row(c), "package_name_en": pkg.name_en if pkg else None, "package_name_th": pkg.name_th if pkg else None,
                                       "day_index": day_index, "lab_day": lab_day} if c else None,
            "doses_today": doses_today, "next_appointment": row(next_appt), "queue": queue,
            "pending_consents": pending_consents, "unread_notifications": unread,
            "trigger_at": c.trigger_at.astimezone(TZ).isoformat() if c and c.trigger_at else None}


# ── Cycle calendar ────────────────────────────────────────────────────────────
@router.get("/cycles")
def my_cycles(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    out = []
    pkgs = {str(x.id): x for x in db.query(TreatmentPackage).all()}
    for c in _cycles_for(db, p):
        pkg = pkgs.get(str(c.package_id))
        out.append({**row(c), "package_name_en": pkg.name_en if pkg else None, "package_name_th": pkg.name_th if pkg else None})
    return out


@router.get("/cycles/{cycle_id}")
def my_cycle(cycle_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    c = _own_cycle(db, p, cycle_id)
    meds = db.query(CycleMedication).filter(CycleMedication.cycle_id == c.id).order_by(CycleMedication.sort_order).all()
    doses = db.query(CycleMedicationDose).filter(CycleMedicationDose.cycle_id == c.id).order_by(CycleMedicationDose.calendar_date).all()
    days = db.query(CycleDay).filter(CycleDay.cycle_id == c.id).order_by(CycleDay.day_index).all()
    appts = db.query(Appointment).filter(Appointment.cycle_id == c.id, Appointment.status != "cancelled").all()
    mon = db.query(CycleMonitoring).filter(CycleMonitoring.cycle_id == c.id, CycleMonitoring.released_to_patient == True).all()
    photos = db.query(EmbryoPhoto).filter(EmbryoPhoto.cycle_id == c.id, EmbryoPhoto.released_to_patient == True).order_by(EmbryoPhoto.lab_day).all()
    outcome = db.query(CycleOutcome).filter(CycleOutcome.cycle_id == c.id).first()
    med_map = {m.id: m for m in meds}
    calendar = {}
    for d in days:
        calendar[str(d.calendar_date)] = {"day_index": d.day_index, "lab_day": d.lab_day, "label_en": d.label_en, "label_th": d.label_th,
                                          "is_procedure": d.is_procedure, "doses": [], "events": []}
    for d in doses:
        m = med_map.get(d.medication_id)
        calendar.setdefault(str(d.calendar_date), {"doses": [], "events": []})["doses"].append(
            {**row(d), "drug_en": m.drug_en if m else "", "drug_th": m.drug_th if m else "", "route": m.route if m else ""})
    for a in appts:
        calendar.setdefault(str(a.appointment_date), {"doses": [], "events": []})["events"].append(
            {"type": a.appointment_type, "type_th": a.appointment_type_th, "time": a.appointment_time.strftime("%H:%M") if a.appointment_time else None,
             "status": a.status, "instructions_en": a.preparation_instructions, "instructions_th": a.preparation_instructions_th})
    if c.trigger_at:
        tdt = c.trigger_at.astimezone(TZ)
        calendar.setdefault(str(tdt.date()), {"doses": [], "events": []})["events"].append({"type": "trigger", "type_th": "ฉีดยากระตุ้นไข่สุก", "time": tdt.strftime("%H:%M")})
    return {"cycle": row(c), "medications": rows(meds), "calendar": calendar, "monitoring": rows(mon),
            "album": [{"id": ph.id, "lab_day": ph.lab_day, "caption_en": ph.caption_en, "caption_th": ph.caption_th, "taken_at": str(ph.taken_at)} for ph in photos],
            "outcome": _patient_outcome(outcome), "report_available": bool(outcome)}


def _patient_outcome(o: CycleOutcome | None):
    if not o:
        return None
    return {"hcg_date": str(o.hcg_date) if o.hcg_date else None, "hcg_positive": o.hcg_positive, "clinical_pregnancy": o.clinical_pregnancy,
            "fetal_hearts": o.fetal_hearts, "ongoing_pregnancy": o.ongoing_pregnancy, "live_birth": o.live_birth}


def _own_cycle(db: Session, p: Patient, cycle_id: str) -> TreatmentCycle:
    c = db.query(TreatmentCycle).filter(TreatmentCycle.id == cycle_id).first()
    partner = cyc.partner_of(db, p.id)
    if not c or str(c.patient_id) not in {str(p.id), str(partner.id) if partner else ""}:
        raise HTTPException(404, "Cycle not found")
    return c


@router.post("/doses/{dose_id}/taken")
async def dose_taken(dose_id: str, request: Request, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    d = db.query(CycleMedicationDose).filter(CycleMedicationDose.id == dose_id).first()
    if not d:
        raise HTTPException(404, "Dose not found")
    _own_cycle(db, p, d.cycle_id)
    b = await request.json() if request.headers.get("content-length", "0") not in ("0", "") else {}
    d.taken_at = None if b.get("undo") else now()
    d.taken_source = None if b.get("undo") else "patient"
    db.commit()
    return row(d)


# ── Appointments & booking ────────────────────────────────────────────────────
@router.get("/appointments")
def my_appointments(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    appts = db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.appointment_date >= today() - timedelta(days=90)).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    reqs = db.query(PortalBookingRequest).filter(PortalBookingRequest.patient_id == p.id).order_by(desc(PortalBookingRequest.created_at)).limit(10).all()
    return {"appointments": rows(appts), "requests": rows(reqs)}


@router.post("/booking-requests")
async def booking_request(request: Request, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    b = await request.json()
    d = parse_date(b.get("date"))
    if not d or d < today():
        raise HTTPException(400, "Choose a future date")
    r = PortalBookingRequest(patient_id=p.id, requested_date=d, requested_time=parse_time(b.get("time")),
                             appointment_type=b.get("appointment_type", "follow_up"), note=b.get("note"))
    db.add(r)
    db.commit()
    db.refresh(r)
    return row(r)


@router.get("/queue")
def queue(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    t = today()
    a = db.query(Appointment).filter(Appointment.patient_id == p.id, Appointment.appointment_date == t,
                                     Appointment.status.in_(("checked_in", "in_progress", "scheduled", "confirmed"))).first()
    if not a:
        return {"today": False}
    ahead = db.query(Appointment).filter(Appointment.appointment_date == t, Appointment.status == "checked_in",
                                         Appointment.queue_number != None, Appointment.queue_number < (a.queue_number or 10**6)).count()
    return {"today": True, "status": a.status, "queue_number": a.queue_number, "ahead": ahead if a.status == "checked_in" else None,
            "time": a.appointment_time.strftime("%H:%M") if a.appointment_time else None}


# ── Results ───────────────────────────────────────────────────────────────────
@router.get("/results")
def results(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    """Verified general-lab results + released monitoring."""
    out = []
    q = (db.query(LabResult, LabOrderItem, LabTestPanel, LabOrder).join(LabOrderItem, LabOrderItem.id == LabResult.order_item_id)
         .join(LabTestPanel, LabTestPanel.id == LabOrderItem.test_panel_id).join(LabOrder, LabOrder.id == LabOrderItem.order_id)
         .filter(LabOrder.patient_id == p.id, LabResult.verified_at != None).order_by(desc(LabResult.resulted_at)).limit(200))
    for r, item, panel, order in q.all():
        out.append({"date": str(r.resulted_at.date()) if r.resulted_at else None, "code": panel.code, "name_en": panel.name_en, "name_th": panel.name_th,
                    "value": float(r.numeric_value) if r.numeric_value is not None else r.text_value, "unit": r.unit or panel.unit,
                    "flag": r.flag.value if r.flag else None, "reference": r.normal_range})
    mon = db.query(CycleMonitoring).join(TreatmentCycle, TreatmentCycle.id == CycleMonitoring.cycle_id).filter(
        TreatmentCycle.patient_id == p.id, CycleMonitoring.released_to_patient == True).order_by(desc(CycleMonitoring.calendar_date)).all()
    return {"lab": out, "monitoring": rows(mon)}


# ── Album ─────────────────────────────────────────────────────────────────────
@router.get("/album")
def album(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    ids = [c.id for c in _cycles_for(db, p)]
    photos = db.query(EmbryoPhoto).filter(EmbryoPhoto.cycle_id.in_(ids), EmbryoPhoto.released_to_patient == True).order_by(desc(EmbryoPhoto.released_at)).all() if ids else []
    return [{"id": ph.id, "cycle_id": ph.cycle_id, "lab_day": ph.lab_day, "caption_en": ph.caption_en, "caption_th": ph.caption_th, "taken_at": str(ph.taken_at)} for ph in photos]


@router.get("/album/{photo_id}/file")
def album_file(photo_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    ph = db.query(EmbryoPhoto).filter(EmbryoPhoto.id == photo_id, EmbryoPhoto.released_to_patient == True).first()
    if not ph:
        raise HTTPException(404, "Photo not found")
    _own_cycle(db, p, ph.cycle_id)
    if not Path(ph.path).exists():
        raise HTTPException(404, "File missing")
    return FileResponse(ph.path)


# ── Consents ──────────────────────────────────────────────────────────────────
@router.get("/consents")
def my_consents(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    partner = cyc.partner_of(db, p.id)
    ids = [c.id for c in _cycles_for(db, p)]
    ccs = db.query(CycleConsent).filter(CycleConsent.cycle_id.in_(ids)).all() if ids else []
    templates = {t.id: t for t in db.query(ConsentTemplate).all()}
    out = []
    for cc in ccs:
        t = templates.get(cc.template_id)
        out.append({**row(cc), "title_en": t.title_en if t else cc.consent_type, "title_th": t.title_th if t else cc.consent_type,
                    "body_en": t.body_en if t else "", "body_th": t.body_th if t else "", "signer": t.signer if t else "patient",
                    "can_sign": cc.status == "pending"})
    return out


@router.post("/consents/{consent_id}/sign")
async def sign(consent_id: str, request: Request, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    cc = db.query(CycleConsent).filter(CycleConsent.id == consent_id).first()
    if not cc:
        raise HTTPException(404, "Consent not found")
    _own_cycle(db, p, cc.cycle_id)
    b = await request.json()
    if not b.get("signature"):
        raise HTTPException(400, "Signature required")
    cc = cons.sign(db, cc, signature_data_url=b["signature"], signer_patient_id=p.id, channel="patient_app",
                   ip=request.client.host if request.client else None, actor_id=None)
    return row(cc)


@router.get("/consents/{consent_id}/file")
def consent_pdf(consent_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    cc = db.query(CycleConsent).filter(CycleConsent.id == consent_id).first()
    if not cc or not cc.document_path:
        raise HTTPException(404, "Document not found")
    _own_cycle(db, p, cc.cycle_id)
    return FileResponse(cc.document_path, media_type="application/pdf")


# ── Cryo & payments ───────────────────────────────────────────────────────────
@router.get("/cryo")
def my_cryo(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    inv = cryo.inventory_for_patient(db, p.id)
    partner = cyc.partner_of(db, p.id)
    if partner:
        inv["partner_sperm"] = cryo.inventory_for_patient(db, partner.id)["sperm"]
    for t in inv["terms"]:
        t["days_left"] = (parse_date(t["paid_until"]) - today()).days if t.get("paid_until") else None
        if t.get("invoice_id"):
            i = db.query(Invoice).filter(Invoice.id == t["invoice_id"]).first()
            t["invoice"] = {"number": i.invoice_number, "status": i.status, "balance_due": float(i.balance_due or 0), "total": float(i.total_amount or 0)} if i else None
    return inv


@router.get("/invoices")
def my_invoices(db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    out = []
    for i in db.query(Invoice).filter(Invoice.patient_id == p.id, Invoice.status != "void").order_by(desc(Invoice.invoice_date)).limit(50).all():
        pays = db.query(Payment).filter(Payment.invoice_id == i.id, Payment.is_void == False).all()
        out.append({"id": i.id, "number": i.invoice_number, "date": str(i.invoice_date), "status": i.status, "total": float(i.total_amount or 0),
                    "paid": float(i.paid_amount or 0), "balance_due": float(i.balance_due or 0), "notes": i.notes, "notes_th": i.notes_th,
                    "receipts": [{"number": x.receipt_number, "date": str(x.payment_date), "amount": float(x.amount), "method": x.method} for x in pays]})
    return out


@router.get("/invoices/{invoice_id}/promptpay.png")
def promptpay_png(invoice_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    if not jsettings.PROMPTPAY_ID:
        raise HTTPException(503, "PromptPay not configured")
    i = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.patient_id == p.id).first()
    if not i:
        raise HTTPException(404, "Invoice not found")
    amt = float(i.balance_due or 0)
    return Response(promptpay.png(jsettings.PROMPTPAY_ID, amt if amt > 0 else None), media_type="image/png")


# ── Notifications, reports, education ─────────────────────────────────────────
@router.get("/notifications")
def my_notifications(limit: int = 50, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    return rows(db.query(PatientNotification).filter(PatientNotification.patient_id == p.id, PatientNotification.sent_at != None)
                .order_by(desc(PatientNotification.sent_at)).limit(limit).all())


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    n = db.query(PatientNotification).filter(PatientNotification.id == notification_id, PatientNotification.patient_id == p.id).first()
    if n and not n.read_at:
        n.read_at = now()
        db.commit()
    return {"status": "ok"}


@router.get("/reports/{cycle_id}.pdf")
def my_report(cycle_id: str, db: Session = Depends(get_db), p: Patient = Depends(pa.current_patient)):
    c = _own_cycle(db, p, cycle_id)
    if not db.query(CycleOutcome).filter(CycleOutcome.cycle_id == c.id).first():
        raise HTTPException(404, "Report not yet available")
    return Response(rpt.cycle_report_pdf(db, c), media_type="application/pdf")


EDUCATION = [
    {"id": "ivf-steps", "title_en": "The IVF journey, step by step", "title_th": "ขั้นตอนการทำเด็กหลอดแก้ว", "url": "https://www.lifebydrpat.com", "tag": "Patient Guide"},
    {"id": "injections", "title_en": "How to give your injections", "title_th": "วิธีฉีดยาด้วยตนเอง", "url": "https://www.youtube.com/@lifebydrpat", "tag": "Patient Guide"},
    {"id": "after-et", "title_en": "After embryo transfer: what to expect", "title_th": "หลังย้ายตัวอ่อน ควรปฏิบัติตัวอย่างไร", "url": "https://www.lifebydrpat.com", "tag": "Patient Guide"},
    {"id": "podcast", "title_en": "Deep Dive into Reproduction (podcast)", "title_th": "พอดแคสต์ เม้ามอยกับหมอพัฒน์ศมา", "url": "https://podcast.lifebydrpat.com", "tag": "Podcast"},
]


@router.get("/education")
def education(p: Patient = Depends(pa.current_patient)):
    return EDUCATION
