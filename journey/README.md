# FCMS Journey layer — the patient-journey spine (adapted from Binflux Infans)

One cycle object is the spine; three lanes (clinic · lab · patient) are stitched together by
automatic handoffs. Nothing here replaces an existing module: it orchestrates Modules 1, 2, 6, 7 and 10
and adds the lanes Binflux sells as EWS (electronic witnessing) and CareU (patient app).

```
package  →  cycle  →  stimulation chart  →  publish (patient calendar + dose reminders)
         →  monitoring  →  trigger (push with exact time)
         →  schedule procedure (OR appointment · D0–D7 numbering · lab to-do · labels · push · Google Calendar)
         →  witness each lab step by scanning labels (match / mismatch · EMR write-back)
         →  Day0–Day7 observation · album released to the patient
         →  outcome  →  cycle report PDF  →  cryo storage term → renewal reminders → PromptPay
         →  KPIs (Vienna / Maribor)
```

## Pages (all bilingual, LIFE by Dr. Pat design system, Cloud font)

| URL | Who | What |
|---|---|---|
| `/cycles` | physician, nurse | cycle list · create a cycle from a package |
| `/cycles/{id}` | clinical | workspace: overview · stimulation chart · monitoring · schedule & lab tasks · observation (OPU, D0–D7, summary, album, cryo, PGT) · consents (tablet e-sign) · outcome · events & scan record |
| `/lab/todo` | lab | generated to-do list by day and step · consent gating · QR label printing · incidents |
| `/lab/witness` | lab (tablet) | electronic witnessing: camera or USB scanner · MATCH / MISMATCH · manual double-witness |
| `/desk` | front desk | today's queue (check-in, call → patient push) · booking requests from the app · cryo renewals · broadcast · connection status · Google Calendar sync |
| `/admin/packages` | physician/admin | package templates (medications, lab events, witness points, consents, billing) · consent templates |
| `/insight` | clinical | KPIs (laboratory = Vienna consensus, clinical = Maribor consensus, operational) · monthly series · Excel export |
| `/portal` | patients | LINE Mini App / PWA: today's doses with "taken" ticks · calendar · trigger · queue · results · album · consents · cryo & PromptPay · notifications · booking request |

API: `/api/v1/journey/*` (staff, JWT) and `/api/v1/portal/*` (patients, patient JWT). Swagger at `/docs`.

## Run

```bash
export PYTHONPATH=.
alembic upgrade head                       # adds j1_001 (19 tables, widens 3 Module 2 columns)
python seed_admin.py --all
uvicorn app.main:app --port 8000
# then in the UI: /admin/packages → "Seed defaults"  (or POST /api/v1/journey/packages/seed)
PYTHONPATH=. python scripts/e2e_journey.py  # full scenario against the live DB (70 checks)
```

Scheduled housekeeping — call once a day (Synology Task Scheduler / cron / launchd on the Mac mini):
`curl -X POST -H "Authorization: Bearer <staff token>" http://<server>:8000/api/v1/journey/jobs/daily`
(delivers due notifications, cryo renewal reminders, imports Google busy blocks). Dose reminders are
delivered by the same job — run it every 5–15 minutes if you want reminders at the exact slot time.

## External connections (`.env`) — what the clinic has to set up

Everything is optional: a channel that is not configured is recorded as "skipped: not configured" and the
in-app feed still carries the message. `GET /api/v1/journey/connections` shows the live status (also on `/desk`).

| Purpose | Keys | Where to get it | Cost model |
|---|---|---|---|
| **LINE push to patients** (primary Thai channel) | `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers console → Messaging API channel of the clinic's LINE Official Account | LINE OA plan; push messages beyond the free monthly quota are metered |
| **LINE Login / Mini App** (patients sign in with LINE) | `LINE_LIFF_ID`, `LINE_LOGIN_CHANNEL_ID` | LINE Developers console → LINE Login channel + LIFF app pointing at `PORTAL_BASE_URL` (HTTPS required) | free |
| **SMS** (OTP + reminders fallback) | `SMS_PROVIDER` = `thaibulksms` \| `twilio` \| `generic`, `SMS_API_KEY/SECRET`, `SMS_SENDER_ID`, or `TWILIO_*` | Thai gateway account (sender-name registration needed) or Twilio | per message |
| **E-mail** | `SMTP_HOST/PORT/USER/PASSWORD/FROM` | Google Workspace SMTP or any SMTP relay | included in Workspace |
| **WhatsApp** (international patients) | `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN` | Meta Business → WhatsApp Cloud API | per conversation |
| **Google Calendar mirror** | `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, optional `GOOGLE_CALENDAR_PROCEDURES_ID`, `GOOGLE_IMPERSONATE_USER` | Google Cloud project → enable Calendar API → service account key; share the clinic calendar with the service-account e-mail ("Make changes to events") | free |
| **PromptPay QR** in the patient app | `PROMPTPAY_ID` (clinic phone or 13-digit tax id) | the clinic's bank PromptPay registration | free; payment confirmation stays manual unless a gateway is added (`PAYMENT_WEBHOOK_SECRET` reserved for Omise / 2C2P / GB Prime Pay) |
| **Public HTTPS for the patient app** | `PORTAL_BASE_URL` | reverse proxy / Cloudflare Tunnel to the Mac mini (`/portal`) | Cloudflare free tier |
| Labels | `LABEL_LAB_WIDTH_MM`/`HEIGHT_MM` (default 40×20), cryo size | cryo-resistant label printer on the lab network + 2D barcode scanner (USB/Bluetooth, keyboard mode) or tablet camera | hardware only — no metered consumables |
| Cryo policy | `CRYO_TERM_MONTHS`, `CRYO_REMINDER_DAYS` (60,30,7), `CRYO_GRACE_DAYS` | clinic policy | — |

Python packages added: `qrcode[pil]`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`.

## Design decisions

* The cycle **reuses `treatment_cycles`** (Module 2) with new columns; embryology data stays in Module 2 tables.
* **Packages are data**, not code — edit at `/admin/packages`. Default templates are starting points for the physician to adjust; billing amounts default to 0 until the clinic prices them.
* **Witness rule**: every item scanned in one session must resolve to the same cycle (sperm items may be the linked partner's). A mismatch is a hard stop with an incident; a successful match writes the step's timestamp back to the EMR.
* **Consent gating**: a lab task whose required consents are unsigned is `blocked` — it cannot be done or witnessed until the patient signs (tablet or app).
* **Events**: every handoff is a `cycle_events` row; handlers (`services/handlers.py`) are isolated so a failed push never breaks a clinical save.
* **PDPA**: Google Calendar titles carry only type + HN + first name; the patient API exposes only released/verified content; all actions audit-log.
* No AI chatbot. "Virtual consultation" wording. EN/TH everywhere. Buddhist-calendar dates on labels/PDFs.

## Files

```
journey/
├── backend/core/config.py          JourneySettings (.env keys above)
├── backend/models/journey_models.py  19 tables
├── backend/services/
│   ├── events.py        event bus          ├── handlers.py   lane wiring
│   ├── packages.py      templates + seed   ├── cycles.py     spine (create · publish · trigger · schedule · outcome)
│   ├── lab_tasks.py     to-do generation   ├── witness.py    scanning · matching · write-back
│   ├── labels.py        QR label PDFs      ├── observation.py D0–D7 writes + workspace read model
│   ├── consents.py      e-sign + PDF       ├── report.py     cycle report PDF
│   ├── cryo.py          storage terms ↔ invoices ↔ reminders
│   ├── notifications.py LINE/SMS/e-mail/WhatsApp + templates
│   ├── calendar_sync.py Google Calendar    ├── kpi.py        Vienna/Maribor indicators
│   ├── portal_auth.py   LINE Login / OTP   ├── promptpay.py  EMVCo QR
│   └── crm_hooks.py     Module 6 → journey
├── backend/api/journey_routes.py   staff API
├── backend/api/portal_routes.py    patient API
├── frontend/pages/*.html           React (in-browser Babel, vendored libs, offline-capable) + journey.css
├── frontend/vendor/jsQR.js         camera QR decoding (fallback when BarcodeDetector is absent)
└── migrations/j1_001_journey_layer.py
```
