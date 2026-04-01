# FCMS Module 5 — Medical Supply / เวชภัณฑ์

## Overview / ภาพรวม
Complete medical supply management module for fertility clinic operations.
Covers plasticware, lab media, test kits, cryostorage materials, consumables,
PPE, and cleaning supplies with bilingual (EN/TH) support throughout.

## Features / คุณสมบัติ

- **Supply Catalogue / รายการเวชภัณฑ์**: 8 categories with fertility-specific subcategories (culture dishes, ICSI needles, vitrification media, ET catheters, etc.)
- **Supplier Management / จัดการผู้จำหน่าย**: Vendor master with contacts, payment terms, tax ID
- **Stock Management / จัดการสต็อก**: Receive with lot/expiry/GRN tracking, manual adjustments with mandatory reason, FIFO issuing
- **Requisitions / ใบเบิก**: Department → Approve → Issue workflow (Embryology Lab, Andrology Lab, General Lab, Clinic, Operating Room)
- **Usage Logging / บันทึกการใช้**: Per-procedure supply tracking (OPU, ET, IUI, ICSI, hysteroscopy, PRP, vitrification, warming, semen analysis)
- **Expiry Alerts / แจ้งเตือนหมดอายุ**: Configurable 7/30/90 day warnings with value-at-risk
- **Low-Stock Alerts / แจ้งเตือนสต็อกต่ำ**: Suggested reorder quantities
- **Dashboard / แดชบอร์ด**: Stock value, category breakdown, pending requisitions, alert counts
- **Consumption Reports / รายงานการใช้**: By supply, category, department, procedure type, date range

## Supply Categories / หมวดหมู่เวชภัณฑ์

| Category | EN | TH | Examples |
|----------|----|----|----------|
| plasticware | Plasticware | พลาสติกแวร์ | Culture dishes, ICSI dishes, pipettes, cryovials, slides |
| lab_media | Lab Media | มีเดียแล็บ | Culture media, wash media, oil overlay, PVP, vitrification media |
| test_kit | Test Kit | ชุดตรวจ | Pregnancy test, hormone assay, semen analysis kit |
| cryostorage | Cryostorage | วัสดุแช่แข็ง | Cryo straws, goblets, canes, liquid nitrogen |
| consumable | Consumable | วัสดุสิ้นเปลือง | Syringes, needles, OPU needles, ET/IUI catheters, gloves |
| ppe | PPE | อุปกรณ์ป้องกัน | Masks, gowns, caps, shoe covers |
| cleaning | Cleaning | ทำความสะอาด | Disinfectant, alcohol, sterilization pouches |
| general | General | ทั่วไป | Labels, printer ribbons, paper |

## API Endpoints

### Suppliers
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/supplies/suppliers` | List suppliers (search, paginate) |
| POST | `/api/v1/supplies/suppliers` | Add new supplier |
| GET | `/api/v1/supplies/suppliers/{id}` | Supplier detail |
| PATCH | `/api/v1/supplies/suppliers/{id}` | Update supplier |

### Supply Catalogue
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/supplies/items` | List supplies (search, filter, paginate) |
| POST | `/api/v1/supplies/items` | Add new supply item |
| GET | `/api/v1/supplies/items/{id}` | Supply detail + stock lots + transactions |
| PATCH | `/api/v1/supplies/items/{id}` | Update supply item |

### Stock Management
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/supplies/stock/receive` | Receive stock (GRN + lot/expiry) |
| POST | `/api/v1/supplies/stock/adjust` | Manual stock adjustment |
| GET | `/api/v1/supplies/stock/levels` | Current stock levels by category/dept |

### Requisitions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/supplies/requisitions` | List requisitions |
| POST | `/api/v1/supplies/requisitions` | Create requisition |
| GET | `/api/v1/supplies/requisitions/{id}` | Requisition detail + items |
| POST | `/api/v1/supplies/requisitions/{id}/approve` | Approve requisition |
| POST | `/api/v1/supplies/requisitions/{id}/reject` | Reject requisition |
| POST | `/api/v1/supplies/requisitions/{id}/issue` | Issue (FIFO dispense) |

### Usage & Alerts
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/supplies/usage` | Log usage per procedure |
| GET | `/api/v1/supplies/usage` | List usage logs |
| GET | `/api/v1/supplies/alerts/expiry` | Expiry alerts (configurable days) |
| GET | `/api/v1/supplies/alerts/low-stock` | Low stock alerts |

### Dashboard & Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/supplies/dashboard` | Dashboard statistics |
| GET | `/api/v1/supplies/reports/consumption` | Consumption report |
| GET | `/api/v1/supplies/translations` | i18n translation data |

## Access Control
| Role | Access |
|------|--------|
| Admin / ผู้ดูแลระบบ | Full access |
| IT Admin | Full access |
| Lab Supervisor / หัวหน้าแล็บ | Full access + approve requisitions |
| Embryologist / นักวิทยาศาสตร์ตัวอ่อน | Catalogue, stock receive, usage, requisitions |
| Lab Technician / เจ้าหน้าที่แล็บ | Stock receive, issue, usage, requisitions |
| Pharmacist / เภสัชกร | Catalogue, stock receive, suppliers |
| Nurse / พยาบาล | View catalogue, usage, create requisitions |
| Physician / แพทย์ | View catalogue, usage |

## Departments / แผนก
- **Embryology Lab / ห้องปฏิบัติการตัวอ่อน** — culture dishes, media, ICSI supplies, vitrification
- **Andrology Lab / ห้องปฏิบัติการอสุจิ** — semen analysis kits, sperm prep media, specimen cups
- **General Lab / ห้องปฏิบัติการทั่วไป** — blood/urine test kits, centrifuge tubes
- **Clinic Room / ห้องตรวจ** — syringes, speculums, general consumables
- **Operating Room / ห้องผ่าตัด** — OPU needles, ET catheters, IUI catheters, drapes

## File Structure
```
module5/
├── README.md
├── backend/
│   ├── api/supply_routes.py        # All API endpoints
│   ├── models/supply_models.py     # SQLAlchemy ORM models (7 tables)
│   └── schemas/supply_schemas.py   # Pydantic + bilingual presets
├── frontend/
│   └── pages/SupplyDashboard.jsx   # Full dashboard (7 tabs)
├── i18n/
│   └── translations.py             # Shared bilingual translations
└── migrations/
    └── m5_001_medical_supply.py    # DB migration
```
