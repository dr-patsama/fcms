# FCMS Module 6 — CRM / ระบบบริหารลูกค้าสัมพันธ์

## Overview / ภาพรวม
Complete CRM module for fertility clinic operations: appointment booking, virtual
consultations (video), multi-channel reminders (SMS/LINE/Email/WhatsApp),
communication logging, provider scheduling, and patient contact preferences.
Bilingual (EN/TH) throughout. No AI chatbot per clinic preference.

## Features / คุณสมบัติ

- **Appointment Booking / นัดหมาย**: Full lifecycle (schedule → confirm → check-in → complete), 14 fertility-specific appointment types, reschedule with history, walk-in/online/phone/LINE/WhatsApp booking sources
- **Virtual Consultation / ปรึกษาทางไกล**: Video session management, multi-platform (internal, Zoom, Google Meet, LINE Video), consultation notes, follow-up plans, quality tracking
- **Reminders / แจ้งเตือน**: Multi-channel (SMS, LINE, Email, WhatsApp), configurable offsets (1h/24h/48h/7d), bulk scheduling, delivery tracking, template system
- **Communication Log / บันทึกการสื่อสาร**: Full outbound/inbound message history per patient, channel analytics
- **Patient Contact Preferences / ช่องทางติดต่อ**: Preferred channel, language, time, per-channel consent (PDPA compliant)
- **Provider Scheduling / ตารางแพทย์**: Weekly schedule slots, appointment type restrictions, day-off/holiday exceptions, real-time available slot finder
- **Dashboard / แดชบอร์ด**: Today's appointments, check-ins, waiting VC, pending reminders, no-shows, booking source analytics

## API Endpoints

### Appointments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/crm/appointments` | List appointments (filter by date, status, type, provider) |
| POST | `/api/v1/crm/appointments` | Create appointment |
| GET | `/api/v1/crm/appointments/{id}` | Appointment detail + reminders + VC |
| PATCH | `/api/v1/crm/appointments/{id}` | Update appointment |
| POST | `/api/v1/crm/appointments/{id}/check-in` | Patient check-in |
| POST | `/api/v1/crm/appointments/{id}/cancel` | Cancel with reason |
| POST | `/api/v1/crm/appointments/{id}/reschedule` | Reschedule (creates linked new appointment) |

### Virtual Consultations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/crm/consultations` | Create VC session |
| GET | `/api/v1/crm/consultations` | List VCs |
| PATCH | `/api/v1/crm/consultations/{id}` | Update VC (notes, status, quality) |

### Reminders
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/crm/reminders` | Schedule single reminder |
| POST | `/api/v1/crm/reminders/bulk` | Bulk reminders (multi-channel + multi-offset) |
| GET | `/api/v1/crm/reminders/pending` | Pending reminders (due within N hours) |
| POST | `/api/v1/crm/reminders/{id}/mark-sent` | Mark as sent/delivered/failed |

### Communications
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/crm/communications/send` | Send message to patient |
| GET | `/api/v1/crm/communications` | Communication history |

### Patient Contact Preferences
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/crm/patients/{id}/contact-preferences` | Get preferences |
| PUT | `/api/v1/crm/patients/{id}/contact-preferences` | Create/update preferences |

### Provider Scheduling
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/crm/schedule/{provider_id}` | Weekly schedule + exceptions |
| POST | `/api/v1/crm/schedule` | Create schedule slot |
| POST | `/api/v1/crm/schedule/exception` | Block off date |
| GET | `/api/v1/crm/schedule/available-slots` | Available slots for date/provider |

### Dashboard & Translations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/crm/dashboard` | Dashboard statistics |
| GET | `/api/v1/crm/translations` | i18n translation data |

## Integration Notes
- **SMS**: Ready for Thai SMS gateway (DTAC/AIS API or Twilio) — plug into `/reminders/{id}/mark-sent`
- **LINE**: Ready for LINE Official Account Messaging API — template-based rich cards
- **WhatsApp**: Ready for WhatsApp Business API integration
- **Email**: Ready for SMTP/SendGrid/SES integration
- **Video**: Room URL generation supports internal, Zoom, Google Meet, LINE Video

## Access Control
| Role | Access |
|------|--------|
| Admin / ผู้ดูแลระบบ | Full access |
| IT Admin | Full access |
| Physician / แพทย์ | Appointments, consultations, schedule management |
| Nurse / พยาบาล | Appointments, check-in, reminders, communications |
| Receptionist / พนักงานต้อนรับ | Appointments, check-in, reminders |
| CRM Staff | Full CRM access |

## File Structure
```
module6/
├── README.md
├── backend/
│   ├── api/crm_routes.py           # All API endpoints
│   ├── models/crm_models.py        # SQLAlchemy ORM models (7 tables)
│   └── schemas/crm_schemas.py      # Pydantic + bilingual presets
├── frontend/
│   └── pages/CRMDashboard.jsx      # Full dashboard (6 tabs)
├── i18n/
│   └── translations.py             # Shared bilingual translations
└── migrations/
    └── m6_001_crm.py               # DB migration
```
