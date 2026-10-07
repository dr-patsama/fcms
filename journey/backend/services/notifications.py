"""
Patient notifications: bilingual templates per event, in-app feed (patient_notifications),
and channel delivery through LINE Messaging API / SMS / Email / WhatsApp (the CRM standing
decision). A channel that is not configured is recorded as "skipped: not configured" — nothing
is lost; the in-app feed always has the message. Every delivery is also logged in Module 6
communication_logs so the CRM screens see it.
"""
from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import httpx
from sqlalchemy.orm import Session

from module1.backend.models.emr_models import Patient
from module6.backend.models.crm_models import CommunicationLog, PatientContactPreference

from ..core.config import jsettings
from ..models.journey_models import PatientNotification, PatientAccount
from .common import now, TZ

log = logging.getLogger("fcms.journey.notify")

# ── Templates (EN / TH). Placeholders: {name} {clinic} {date} {time} {cycle} {drug} {dose} {unit} {days} {url} {amount} {queue} ──
TEMPLATES = {
    "visit.booked":        ("Appointment confirmed", "ยืนยันนัดหมาย",
                            "Your appointment at {clinic} is on {date} at {time}. Reply here if you need to change it.",
                            "นัดหมายของคุณที่ {clinic} วันที่ {date} เวลา {time} หากต้องการเลื่อนนัด แจ้งเจ้าหน้าที่ได้ที่นี่"),
    "visit.reminder":      ("Appointment tomorrow", "แจ้งเตือนนัดหมายพรุ่งนี้",
                            "Reminder: your visit at {clinic} is tomorrow {date} at {time}.",
                            "เตือนความจำ: นัดหมายของคุณที่ {clinic} พรุ่งนี้ {date} เวลา {time}"),
    "queue.called":        ("It is your turn", "ถึงคิวของคุณแล้ว",
                            "Queue {queue}: please come to the consultation room.",
                            "คิว {queue}: เชิญเข้าห้องตรวจได้เลยค่ะ"),
    "plan.published":      ("Your treatment plan is ready", "แผนการรักษาของคุณพร้อมแล้ว",
                            "Your medication plan for {cycle} starts {date}. Open the app to see each day's medications.",
                            "แผนการใช้ยาสำหรับรอบ {cycle} เริ่มวันที่ {date} เปิดแอปเพื่อดูยาในแต่ละวัน"),
    "plan.updated":        ("Your plan was updated", "มีการปรับแผนการรักษา",
                            "Your doctor adjusted your medication plan. Please check today's doses in the app.",
                            "แพทย์ปรับแผนการใช้ยาของคุณ กรุณาตรวจสอบยาของวันนี้ในแอป"),
    "dose.reminder":       ("Medication reminder", "เตือนใช้ยา",
                            "Time for {drug} {dose} {unit}. Tap to confirm when taken.",
                            "ถึงเวลา {drug} {dose} {unit} แตะยืนยันเมื่อใช้ยาแล้ว"),
    "trigger.set":         ("Trigger injection tonight", "ฉีดยากระตุ้นไข่สุกคืนนี้",
                            "Please give your trigger injection at exactly {time} on {date}. This timing matters for your procedure.",
                            "กรุณาฉีดยากระตุ้นไข่สุกเวลา {time} ตรงของวันที่ {date} เวลานี้สำคัญต่อหัตถการของคุณ"),
    "procedure.scheduled": ("Procedure scheduled", "นัดหมายหัตถการ",
                            "Your procedure is scheduled for {date} at {time}. Instructions: {instructions}",
                            "นัดหมายหัตถการของคุณคือวันที่ {date} เวลา {time} คำแนะนำ: {instructions}"),
    "procedure.rescheduled": ("Procedure rescheduled", "เลื่อนนัดหัตถการ",
                            "Your procedure has been moved to {date} at {time}.",
                            "นัดหมายหัตถการของคุณเลื่อนเป็นวันที่ {date} เวลา {time}"),
    "results.released":    ("New results available", "ผลตรวจใหม่",
                            "Your doctor has released new results. Open the app to view them.",
                            "แพทย์ปล่อยผลตรวจใหม่แล้ว เปิดแอปเพื่อดูผล"),
    "album.released":      ("New embryo photos", "รูปตัวอ่อนใหม่",
                            "New photos from the laboratory have been added to your album.",
                            "ห้องปฏิบัติการเพิ่มรูปตัวอ่อนในอัลบั้มของคุณแล้ว"),
    "consent.pending":     ("Please sign your consent forms", "กรุณาลงนามเอกสารยินยอม",
                            "Consent forms for {cycle} are ready to review and sign in the app before your next visit.",
                            "เอกสารยินยอมสำหรับรอบ {cycle} พร้อมให้อ่านและลงนามในแอปก่อนนัดครั้งถัดไป"),
    "outcome.recorded":    ("Your cycle report", "รายงานผลรอบการรักษา",
                            "Your cycle report for {cycle} is available in the app.",
                            "รายงานผลรอบ {cycle} พร้อมให้ดูในแอปแล้ว"),
    "cryo.renewal_due":    ("Storage renewal due", "ครบกำหนดต่ออายุการฝากแช่แข็ง",
                            "Storage for your frozen {content} is paid until {date} ({days} days). Renew in the app or contact us.",
                            "การฝากแช่แข็ง{content}ของคุณชำระถึงวันที่ {date} (อีก {days} วัน) ต่ออายุได้ในแอปหรือติดต่อคลินิก"),
    "cryo.renewed":        ("Storage renewed", "ต่ออายุการฝากแช่แข็งแล้ว",
                            "Thank you — storage is now paid until {date}.",
                            "ขอบคุณค่ะ การฝากแช่แข็งชำระถึงวันที่ {date} แล้ว"),
    "payment.received":    ("Payment received", "ได้รับการชำระเงิน",
                            "We received your payment of {amount} THB. Your receipt is in the app.",
                            "ได้รับการชำระเงิน {amount} บาท ใบเสร็จอยู่ในแอป"),
    "broadcast":           ("{title}", "{title}", "{body}", "{body}"),
}
CONTENT_TH = {"embryo": "ตัวอ่อน", "oocyte": "ไข่", "sperm": "น้ำเชื้อ"}


def render(event_type: str, ctx: dict) -> tuple[str, str, str, str]:
    t = TEMPLATES.get(event_type) or ("Update", "แจ้งเตือน", "{body}", "{body}")
    ctx = {"clinic": jsettings.CLINIC_NAME_EN, "clinic_th": jsettings.CLINIC_NAME_TH, "instructions": "", **{k: ("" if v is None else v) for k, v in ctx.items()}}
    ctx_th = {**ctx, "clinic": jsettings.CLINIC_NAME_TH, "content": CONTENT_TH.get(str(ctx.get("content", "")), ctx.get("content", ""))}

    def f(s, c):
        try:
            return s.format(**c)
        except (KeyError, IndexError):
            return s
    return f(t[0], ctx), f(t[1], ctx_th), f(t[2], ctx), f(t[3], ctx_th)


# ── Channel adapters ─────────────────────────────────────────────────────────
def _line_push(line_user_id: str, text: str) -> str:
    if not jsettings.LINE_CHANNEL_ACCESS_TOKEN:
        return "skipped: LINE not configured"
    r = httpx.post("https://api.line.me/v2/bot/message/push",
                   headers={"Authorization": f"Bearer {jsettings.LINE_CHANNEL_ACCESS_TOKEN}"},
                   json={"to": line_user_id, "messages": [{"type": "text", "text": text[:4900]}]}, timeout=10)
    return "sent" if r.status_code == 200 else f"error {r.status_code}: {r.text[:120]}"


def _sms(phone: str, text: str) -> str:
    p = (jsettings.SMS_PROVIDER or "none").lower()
    if p == "none":
        return "skipped: SMS not configured"
    if p == "twilio":
        r = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{jsettings.TWILIO_ACCOUNT_SID}/Messages.json",
                       auth=(jsettings.TWILIO_ACCOUNT_SID, jsettings.TWILIO_AUTH_TOKEN),
                       data={"To": _e164(phone), "From": jsettings.TWILIO_FROM, "Body": text}, timeout=10)
        return "sent" if r.status_code in (200, 201) else f"error {r.status_code}"
    if p == "thaibulksms":
        r = httpx.post("https://api-v2.thaibulksms.com/sms", auth=(jsettings.SMS_API_KEY, jsettings.SMS_API_SECRET),
                       data={"msisdn": phone, "message": text, "sender": jsettings.SMS_SENDER_ID or ""}, timeout=10)
        return "sent" if r.status_code in (200, 201) else f"error {r.status_code}"
    if p == "generic" and jsettings.SMS_GENERIC_URL:
        r = httpx.post(jsettings.SMS_GENERIC_URL, headers={"Authorization": f"Bearer {jsettings.SMS_API_KEY}"},
                       json={"to": phone, "message": text, "sender": jsettings.SMS_SENDER_ID}, timeout=10)
        return "sent" if r.status_code in (200, 201, 202) else f"error {r.status_code}"
    return "skipped: unknown SMS provider"


def _email(to: str, subject: str, text: str) -> str:
    if not jsettings.SMTP_HOST:
        return "skipped: SMTP not configured"
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, jsettings.SMTP_FROM, to
    with smtplib.SMTP(jsettings.SMTP_HOST, jsettings.SMTP_PORT, timeout=15) as s:
        if jsettings.SMTP_USE_TLS:
            s.starttls()
        if jsettings.SMTP_USER:
            s.login(jsettings.SMTP_USER, jsettings.SMTP_PASSWORD or "")
        s.sendmail(jsettings.SMTP_FROM, [to], msg.as_string())
    return "sent"


def _whatsapp(phone: str, text: str) -> str:
    if not (jsettings.WHATSAPP_PHONE_NUMBER_ID and jsettings.WHATSAPP_ACCESS_TOKEN):
        return "skipped: WhatsApp not configured"
    r = httpx.post(f"https://graph.facebook.com/v20.0/{jsettings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                   headers={"Authorization": f"Bearer {jsettings.WHATSAPP_ACCESS_TOKEN}"},
                   json={"messaging_product": "whatsapp", "to": _e164(phone).lstrip("+"), "type": "text", "text": {"body": text}},
                   timeout=10)
    return "sent" if r.status_code == 200 else f"error {r.status_code}"


def _e164(phone: str) -> str:
    p = "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")
    if p.startswith("0"):
        p = "+66" + p[1:]
    elif p and not p.startswith("+"):
        p = "+" + p
    return p


# ── Core: notify a patient about an event ────────────────────────────────────
def notify(db: Session, patient_id: str, event_type: str, ctx: dict | None = None, *, cycle_id=None,
           channels: list[str] | None = None, action_url: str | None = None, scheduled_for: datetime | None = None,
           deliver: bool = True) -> PatientNotification:
    ctx = ctx or {}
    p = db.query(Patient).filter(Patient.id == str(patient_id)).first()
    ctx.setdefault("name", f"{p.first_name_en}" if p else "")
    title_en, title_th, body_en, body_th = render(event_type, ctx)
    n = PatientNotification(patient_id=str(patient_id), cycle_id=str(cycle_id) if cycle_id else None, type=event_type,
                            title_en=title_en, title_th=title_th, body_en=body_en, body_th=body_th,
                            action_url=action_url or jsettings.PORTAL_BASE_URL, scheduled_for=scheduled_for, channels={})
    db.add(n)
    db.flush()
    if deliver and (scheduled_for is None or scheduled_for <= now()):
        deliver_now(db, n, p, channels)
    return n


def deliver_now(db: Session, n: PatientNotification, p: Patient | None = None, channels: list[str] | None = None):
    p = p or db.query(Patient).filter(Patient.id == n.patient_id).first()
    pref = db.query(PatientContactPreference).filter(PatientContactPreference.patient_id == n.patient_id).first()
    acct = db.query(PatientAccount).filter(PatientAccount.patient_id == n.patient_id).first()
    lang = (acct.language if acct else None) or (pref.preferred_language if pref else None) or (p.preferred_language if p else "th")
    title = n.title_th if lang == "th" else n.title_en
    body = n.body_th if lang == "th" else n.body_en
    text = f"{title}\n{body}"
    chosen = channels or [(pref.preferred_channel if pref else "line") or "line"]
    results = dict(n.channels or {})
    for ch in chosen:
        try:
            if ch == "line":
                lid = acct.line_user_id if acct else None
                results["line"] = _line_push(lid, text) if lid else "skipped: patient has no LINE login"
                recipient = lid
            elif ch == "sms":
                phone = (pref.phone_primary if pref else None) or (p.phone if p else None)
                results["sms"] = _sms(phone, text) if phone else "skipped: no phone"
                recipient = phone
            elif ch == "email":
                em = (pref.email if pref else None) or (p.email if p else None)
                results["email"] = _email(em, title, body) if em else "skipped: no email"
                recipient = em
            elif ch == "whatsapp":
                wa = (pref.whatsapp_number if pref else None) or (p.phone if p else None)
                results["whatsapp"] = _whatsapp(wa, text) if wa else "skipped: no WhatsApp number"
                recipient = wa
            else:
                results[ch] = "skipped: unknown channel"
                recipient = None
        except Exception as e:
            log.exception("delivery failed")
            results[ch] = f"error: {type(e).__name__}"
            recipient = None
        db.add(CommunicationLog(patient_id=n.patient_id, channel=ch, direction="outbound", subject=title,
                                message_en=n.body_en, message_th=n.body_th, template_key=n.type, recipient=recipient,
                                status="sent" if results.get(ch) == "sent" else ("failed" if str(results.get(ch, "")).startswith("error") else "sent"),
                                reference_type="journey", reference_id=n.cycle_id))
    n.channels = results
    n.sent_at = now()
    db.flush()


def send_due(db: Session, limit: int = 500) -> int:
    """Deliver scheduled notifications whose time has come (dose reminders, visit reminders). Called by the daily/5-min job."""
    due = db.query(PatientNotification).filter(PatientNotification.sent_at == None,
                                               PatientNotification.scheduled_for != None,
                                               PatientNotification.scheduled_for <= now()).limit(limit).all()
    for n in due:
        deliver_now(db, n)
    db.commit()
    return len(due)


def broadcast(db: Session, patient_ids: list[str], title_en: str, title_th: str, body_en: str, body_th: str,
              channels: list[str] | None = None) -> int:
    for pid in patient_ids:
        n = PatientNotification(patient_id=pid, type="broadcast", title_en=title_en, title_th=title_th,
                                body_en=body_en, body_th=body_th, channels={})
        db.add(n)
        db.flush()
        deliver_now(db, n, None, channels)
    db.commit()
    return len(patient_ids)
