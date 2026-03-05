# FCMS Module 4 — Pharmacy / เภสัชกรรม

## Overview / ภาพรวม
Complete pharmacy management module with bilingual (EN/TH) support throughout,
including drug catalogue, stock management with FIFO dispensing, prescription
workflow, bilingual medication label printing, and expiry/low-stock alerts.

## Features / คุณสมบัติ

- **Drug Catalogue / รายการยา**: Generic + brand names (EN/TH), category, form, strength, supplier, pricing
- **Stock Management / จัดการสต็อก**: Receive stock with lot/expiry tracking, manual adjustments with mandatory reason, FIFO dispensing
- **Prescription Workflow / ใบสั่งยา**: EMR → Pharmacist verify → Dispense → Record (full audit trail)
- **Label Printing / ฉลากยา**: Bilingual medication labels (70×35mm) with patient name TH/EN, drug, dose, frequency, instructions, clinic info, Buddhist year date
- **Expiry Alerts / แจ้งเตือนหมดอายุ**: Configurable 30/60/90 day warnings with value-at-risk calculation
- **Low-Stock Alerts / แจ้งเตือนสต็อกต่ำ**: Suggested reorder quantities based on reorder level
- **Dispensing Log / บันทึกการจ่ายยา**: Full audit with pharmacist ID, timestamp, lot number
- **i18n System / ระบบสองภาษา**: Shared translation dictionary for all modules

## Label Format / รูปแบบฉลากยา
Standard 70mm × 35mm pharmacy label:
- Clinic name (EN/TH): Life by Dr. Pat / คลินิก ไลฟ์ บาย ดร.แพท
- Patient name (EN/TH) + HN number
- Drug name (EN/TH) + strength + form
- Dosage, frequency, route (EN/TH)
- Instructions + warnings (EN/TH)
- Date in both Gregorian and Buddhist calendar (พ.ศ.)
- Barcode for tracking

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pharmacy/drugs` | List drugs (search, filter, paginate) |
| POST | `/api/v1/pharmacy/drugs` | Add new drug |
| GET | `/api/v1/pharmacy/drugs/{id}` | Drug detail + stock lots |
| PATCH | `/api/v1/pharmacy/drugs/{id}` | Update drug |
| POST | `/api/v1/pharmacy/stock/receive` | Receive stock (GRN) |
| POST | `/api/v1/pharmacy/stock/adjust` | Manual stock adjustment |
| GET | `/api/v1/pharmacy/stock/levels` | Current stock levels |
| GET | `/api/v1/pharmacy/expiry/alerts` | Expiry alerts |
| GET/POST | `/api/v1/pharmacy/prescriptions` | List/create prescriptions |
| POST | `/api/v1/pharmacy/prescriptions/{id}/verify` | Pharmacist verification |
| POST | `/api/v1/pharmacy/prescriptions/{id}/dispense` | Dispense (FIFO) |
| POST | `/api/v1/pharmacy/labels/generate` | Generate bilingual label |
| POST | `/api/v1/pharmacy/labels/batch` | Batch labels for Rx |
| GET | `/api/v1/pharmacy/dashboard` | Dashboard statistics |
| GET | `/api/v1/pharmacy/reports/consumption` | Consumption report |
| GET | `/api/v1/pharmacy/translations` | i18n translation data |

## Access Control
| Role | Access |
|------|--------|
| Pharmacist / เภสัชกร | Full access |
| Pharmacy Staff / เจ้าหน้าที่ | Dispense, stock receive, labels |
| Physician / แพทย์ | Create prescriptions, view stock |
| Nurse / พยาบาล | View prescriptions, view stock |
| Admin / ผู้ดูแลระบบ | Full access |

## File Structure
```
module4/
├── README.md
├── backend/
│   ├── api/pharmacy_routes.py      # All API endpoints (working)
│   ├── models/pharmacy_models.py   # SQLAlchemy ORM models
│   └── schemas/pharmacy_schemas.py # Pydantic + bilingual presets
├── frontend/
│   └── pages/PharmacyDashboard.jsx # Full dashboard (5 tabs)
├── i18n/
│   └── translations.py            # Shared bilingual translations
└── migrations/
    └── m4_001_pharmacy.py          # DB migration (v2 + TH fields)
```
