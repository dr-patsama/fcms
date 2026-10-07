# FCMS — Fertility Clinic Management System

Comprehensive clinic management platform for the Thai healthcare market.

## Tech Stack
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: Next.js + Tailwind CSS + Cloud Font
- **Desktop**: Electron wrapper
- **Auth**: JWT + MFA + Role-based (15 roles)

## Design System
- **Font**: Cloud (Thai/English)
- **Colors**: Sapphire `#0F52BA` · Emerald `#009473` · Ruby `#E0115F`

## Modules

| # | Module | Status |
|---|--------|--------|
| 1 | EMR (Auth, RBAC, Patients, Visits, SOAP, ICD-10) | ✅ Done |
| 2 | Lab Management (General / Embryology / Andrology) | ✅ Done |
| 3 | Ultrasound (GE Voluson Swift / DICOM) | ✅ Done |
| 4 | Pharmacy | ✅ Done |
| 5 | Medical Supplies | ✅ Done |
| 6 | CRM + Virtual Consultation + Booking | ✅ Done |
| 7 | Accounting | ✅ Done |
| 8 | Social Media Center | ⬜ Planned |
| 9 | Webmaster | ⬜ Planned |
| 10 | Reproductive Calculators + Treatment Timeline | ✅ Timeline (v1) · calculators planned |
| — | **Journey layer** — packages · cycle spine · lab to-do + QR labels · electronic witnessing · Day0–D7 · consents e-sign · outcome report · cryo ↔ billing · patient app (LINE/PWA) · notifications · Google Calendar · KPIs | ✅ Done (v1) — see `journey/README.md` |
| 11 | Login Hierarchy & RBAC | ✅ Done |
| 12 | Operating Room Management | ⬜ Planned |

## Compliance
PDPA · HL7/FHIR · DICOM · Bilingual EN/TH

## License
Private — Internal use only.
