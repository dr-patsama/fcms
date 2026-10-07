"""
Journey layer settings — all external connections live here (read from .env).
Anything left blank is treated as "not connected": the system keeps working and
records what it would have sent (communication_logs / patient_notifications.channels).
"""
from typing import Optional
from pydantic_settings import BaseSettings


class JourneySettings(BaseSettings):
    # ── Clinic identity (used in messages, labels, PDFs) ───────────────────────
    CLINIC_NAME_EN: str = "LIFE by Dr. Pat"
    CLINIC_NAME_TH: str = "ไลฟ์ บาย ดอกเตอร์พัฒน์"
    CLINIC_PHONE: str = "083-432-4664"
    CLINIC_TIMEZONE: str = "Asia/Bangkok"

    # ── Patient app (LINE Mini App / LIFF + PWA) ───────────────────────────────
    PORTAL_BASE_URL: str = "http://localhost:8000/portal"      # public HTTPS URL in production
    LINE_LIFF_ID: Optional[str] = None                          # LIFF app id (LINE Developers console)
    LINE_LOGIN_CHANNEL_ID: Optional[str] = None                 # LINE Login channel id — verifies LIFF ID tokens
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None             # Messaging API channel access token (push messages)
    PATIENT_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30            # 30 days
    OTP_EXPIRE_MINUTES: int = 10
    OTP_DEV_ECHO: bool = True                                   # when no SMS/LINE is configured, return the OTP in the API response (DEBUG aid)

    # ── SMS (Thai gateway or Twilio) ──────────────────────────────────────────
    SMS_PROVIDER: str = "none"                                  # none | twilio | thaibulksms | generic
    SMS_SENDER_ID: Optional[str] = None
    SMS_API_KEY: Optional[str] = None
    SMS_API_SECRET: Optional[str] = None
    SMS_GENERIC_URL: Optional[str] = None                       # generic: POST {to, message} JSON with Bearer SMS_API_KEY
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM: Optional[str] = None

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "info@lifebydrpat.com"
    SMTP_USE_TLS: bool = True

    # ── WhatsApp (Meta Cloud API) ─────────────────────────────────────────────
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None

    # ── Google Calendar (service account, calendar shared with it as "Make changes") ──
    GOOGLE_CALENDAR_ID: Optional[str] = None                    # e.g. clinic@lifebydrpat.com or a secondary calendar id
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None           # path to the service-account key file
    GOOGLE_CALENDAR_PROCEDURES_ID: Optional[str] = None         # optional second calendar for OPU/ET/OR
    GOOGLE_IMPERSONATE_USER: Optional[str] = None               # Workspace domain-wide delegation subject (optional)

    # ── Payments ──────────────────────────────────────────────────────────────
    PROMPTPAY_ID: Optional[str] = None                          # phone (0xx…) or tax id (13 digits) for PromptPay QR
    PAYMENT_WEBHOOK_SECRET: Optional[str] = None                # payment-gateway webhook verification (Omise / 2C2P / GB Prime Pay)

    # ── Labels ────────────────────────────────────────────────────────────────
    LABEL_LAB_WIDTH_MM: float = 40
    LABEL_LAB_HEIGHT_MM: float = 20
    LABEL_CRYO_WIDTH_MM: float = 40
    LABEL_CRYO_HEIGHT_MM: float = 20

    # ── Cryo storage policy (defaults; Dr. Pat to confirm) ─────────────────────
    CRYO_TERM_MONTHS: int = 12
    CRYO_REMINDER_DAYS: str = "60,30,7"                         # days before paid_until
    CRYO_GRACE_DAYS: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cryo_reminder_days(self) -> list[int]:
        return [int(x) for x in str(self.CRYO_REMINDER_DAYS).split(",") if x.strip()]

    @property
    def line_push_enabled(self) -> bool:
        return bool(self.LINE_CHANNEL_ACCESS_TOKEN)

    @property
    def google_calendar_enabled(self) -> bool:
        return bool(self.GOOGLE_CALENDAR_ID and self.GOOGLE_SERVICE_ACCOUNT_JSON)


jsettings = JourneySettings()
