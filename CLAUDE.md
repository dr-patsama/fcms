# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FCMS** — Fertility Clinic Management System for the Thai healthcare market.
Clinic name: **Life by Dr. Pat** / **คลินิก ไลฟ์ บาย ดร.แพท**

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL (port 5432)
- **Frontend**: Next.js + Tailwind CSS (port 3000)
- **Desktop**: Electron wrapper
- **Auth**: JWT (HS256, 8-hour expiry) + TOTP MFA + 15-role RBAC
- **Migrations**: Alembic
- **PACS**: Orthanc server (port 8042, DICOM port 4242)

## Common Commands

```bash
# All modules, one process — run from repo root
export PYTHONPATH=.
alembic upgrade head                 # all 7 module migration dirs are chained
python seed_admin.py [--all]         # admin (+ one demo user per role with --all)
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/login  · /docs · /health lists loaded modules

# Production on Synology NAS (Docker): see deploy/synology/README.md
cd deploy/synology && cp .env.example .env && docker compose up -d --build

# Frontend
npm install && npm run dev
```

Default admin credentials (from `seed_admin.py`):
- Email: `admin@lifeclinic.com`
- Password: `LifeByDrPat2026!`

## Repository Structure

```
fcms/
├── design-system/          # Shared design tokens (fonts, colors, Tailwind config)
│   ├── DESIGN_SYSTEM.md    # Full color/typography reference
│   ├── tailwind.config.js  # Tailwind theme — import into each module's frontend
│   ├── tokens.css          # CSS custom properties (--sapphire, --ruby, etc.)
│   └── fonts/              # Cloud font family (TTF files)
├── module1/                # EMR: Auth, RBAC, Patients, Visits, SOAP, ICD-10
├── module2/                # Lab: General / Embryology / Andrology
├── module3/                # Ultrasound: DICOM + GE VOLUSON Swift integration
├── module4/                # Pharmacy: Stock, Prescriptions, Dispensing, Labels
├── module5/                # Medical Supply: Catalogue, Stock, Requisitions, Usage
├── module6/                # CRM: Appointments, Virtual Consultation, Reminders, Scheduling
└── seed_admin.py           # One-time admin seeding script
```

Each module follows this internal structure:
```
moduleN/
├── backend/
│   ├── api/           # FastAPI routers
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic (module2+)
│   └── core/          # Shared infra (module1 only: config, database, auth, security)
├── frontend/pages/    # React/Next.js pages
├── migrations/        # Alembic migration files
└── README.md          # Module-specific API reference
```

## Architecture

### Backend (FastAPI)

- All config via `module1/backend/core/config.py` (pydantic-settings, reads `.env`)
- Database session: `module1/backend/core/database.py` — `get_db()` dependency
- Auth dependencies in `module1/backend/core/auth.py`:
  - `get_current_user` — decode JWT, return user
  - `require_roles(["physician", ...])` — role whitelist
  - `require_module_access("pharmacy")` — module-level RBAC
- Modules 2–7 have `backend/core/*` and `backend/models/user_models.py` **shims** that re-export module1's core; routes keep `from ..core.auth import ...` and everything resolves to one shared DB/auth stack
- `app/main.py` mounts every module router; a broken module is reported in `/health.modules_failed` instead of taking the API down

### Database

- PostgreSQL with UUIDs as primary keys (`gen_random_uuid()`)
- All models have bilingual columns: `first_name_en`/`first_name_th`, `last_name_en`/`last_name_th`
- Module 1: 10 tables (users, patients, visits, SOAP notes, etc.)
- Module 2: 19 tables (lab orders, embryos, andrology)
- Module 3: 5 tables (DICOM studies, measurements, reports)
- Module 4: pharmacy tables with FIFO stock lots
- Module 5: 7 tables (suppliers, medical_supplies, supply_stock_lots, supply_transactions, supply_requisitions, requisition_items, supply_usage_logs)
- Module 6: 7 tables (appointments, virtual_consultations, appointment_reminders, communication_logs, patient_contact_preferences, provider_schedules, schedule_exceptions)
- `DATABASE_URL` default: `postgresql://fcms_user:fcms_pass@localhost:5432/fcms_db`

### Auth & RBAC

JWT claims include `sub` (user_id) and `role`. RBAC enforced at route level via dependency injection. MFA (TOTP) mandatory for: `physician`, `embryologist`, `lab_supervisor`, `admin`.

`require_roles(...)` accepts a list or varargs; `admin`/`it_admin` (level ≥ 95) pass every role check; `require_min_level(n)` is available for pure hierarchy checks. Aliases: accountant/cashier→billing_staff, front_desk→receptionist, manager→admin; module alias medical_supply→supplies.

Key role levels (higher = more access):
- `admin` (100), `it_admin` (95), `physician` (90), `embryologist` (85)
- `lab_supervisor` (80), `nurse`/`lab_technician` (70), `pharmacist`/`sonographer` (65)

### Frontend (Next.js)

- Tailwind config extends design-system colors: `sapphire`, `emerald`, `ruby` with variants
- Font family: Cloud (all weights; Thai/English bilingual)
- All pages must be bilingual EN/TH — module4 has a shared `i18n/translations.py` pattern to follow

## Design System

Always use design system tokens — never hardcode colors:

| Semantic Role | Token | Hex |
|---|---|---|
| Primary action | `sapphire` | `#0F52BA` |
| Sidebar bg | `sapphire-deep` | `#151667` |
| Success / active | `emerald` | `#009473` |
| Danger / critical | `ruby` | `#E0115F` |
| Warning | amber | `#F59E0B` |

Lab result flags: Normal=emerald, Low=sapphire, High=ruby, Critical (LL/HH)=ruby-dark + pulse animation.

Label printing: Pharmacy labels are **80×50mm**; lab tube labels are **40×20mm**. Labels include Buddhist calendar year (พ.ศ. = Gregorian + 543).

## Compliance Requirements

- **PDPA**: Full audit logging on all data access (`audit_logs` table)
- **Bilingual**: All patient-facing text must have EN + TH
- **Buddhist calendar**: Date display uses พ.ศ. alongside Gregorian
- **DICOM**: Module 3 integrates with Orthanc PACS — see `module3/config/orthanc.json`
- **HL7/FHIR**: Planned for future modules

## Module Status

| Module | Status |
|---|---|
| 1 — EMR (Auth, RBAC, Patients, Visits, SOAP, ICD-10) | ✅ Done |
| 2 — Lab (General / Embryology / Andrology) | ✅ Done |
| 3 — Ultrasound (GE VOLUSON Swift / DICOM) | ✅ Done |
| 4 — Pharmacy | ✅ Done |
| 5 — Medical Supply (Catalogue, Requisitions, Usage) | ✅ Done |
| 6 — CRM (Appointments, Virtual Consultation, Reminders) | ✅ Done |
| 7 — Accounting (invoices, receipts, expenses, WHT, P&L/AR) | ✅ Done |
| 10 — Cycle Plan / Timeline Generator (embedded upstream app, DB-backed, patient-linked) | ✅ Done (v1) |
| Live boards — OPD `/board/opd` · Embryology Lab `/board/embryo` (auto-update via SSE, EN/TH) | ✅ Done |
| 8, 9, 11–15 — see ROADMAP.md | ⬜ Planned |

## Live boards
`/board/opd` and `/board/embryo` open an EventSource on `/api/v1/dashboard/{board}/stream?token=<jwt>`.
The server re-queries every 3 s and pushes a `snapshot` event only when the data hash changes
(heartbeat every 20 s; browser falls back to 10 s polling if SSE drops). Queries live in
`app/dashboards/queries.py` — add a panel by adding a query there and a renderer in the HTML.
Role gate: OPD = clinical + reception; Embryo = clinical/lab only. Put a TV on it with
`/board/opd?token=<long-lived staff token>`.
