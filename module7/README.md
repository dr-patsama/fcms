# FCMS Module 7 — Accounting / ระบบบัญชี

## Overview / ภาพรวม
Financial management module for clinic operations: service price list, patient
invoicing, payment/receipt processing, expense tracking with Thai withholding tax,
daily cash closing, and financial reports (P&L, AR aging, revenue by category).
Bilingual (EN/TH) throughout. Printable receipts use the Buddhist calendar (พ.ศ.)
and embed the clinic gold logo.

## Thai Tax Handling / ภาษีไทย
- **Medical services are VAT-exempt** → default `vat_rate = 0`. Retail items
  (supplements, products) can carry 7% VAT per line item.
- **Tax invoice (ใบกำกับภาษี)** issued on request: tax invoice number (TIV-),
  buyer Tax ID, billing name/address.
- **Withholding tax (ภาษีหัก ณ ที่จ่าย)** on expenses: 0/1/2/3/5% with automatic
  net-paid calculation.

## Features / คุณสมบัติ

- **Price List / รายการค่าบริการ**: Service catalog with categories (consultation,
  laboratory, ultrasound, procedure, IVF package, medication, retail), per-item VAT,
  package definitions, flexible CSV import (EN/TH headers)
- **Invoices / ใบแจ้งหนี้**: Line-item invoices (INV-YYYY-NNNNN), discounts, VAT,
  draft → issued → partially_paid → paid lifecycle, void with reason (blocked if
  payments exist), optional tax invoice issue
- **Payments / การรับชำระ**: Partial payments, receipt numbers (RC-YYYY-NNNNN),
  7 methods (cash, credit/debit card, bank transfer, PromptPay, insurance, other),
  auto invoice status recalc, void (blocked after day closing), printable Thai
  receipt with Buddhist year
- **Expenses / ค่าใช้จ่าย**: 14 categories, vendor + tax ID, input VAT, withholding
  tax auto-calc, approval status
- **Daily Closing / ปิดยอดประจำวัน**: Cash reconciliation (expected vs counted,
  variance), per-method totals, locks payment voiding for the closed day
- **Reports / รายงาน**: Dashboard KPIs, daily payment report, monthly P&L
  (cash-basis revenue + billed-by-category + expenses-by-category), AR aging
  (0-30/31-60/61-90/90+), revenue by category

## API Endpoints

### Service Catalog
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounting/services` | List/search price list |
| POST | `/api/v1/accounting/services` | Create service |
| PATCH | `/api/v1/accounting/services/{id}` | Update service |
| POST | `/api/v1/accounting/services/import-csv` | Flexible CSV import (EN/TH headers) |

### Invoices
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounting/invoices` | List (filter: status, patient, dates) |
| GET | `/api/v1/accounting/invoices/{id}` | Detail + items + payments |
| POST | `/api/v1/accounting/invoices` | Create with line items |
| POST | `/api/v1/accounting/invoices/{id}/issue` | Issue draft |
| POST | `/api/v1/accounting/invoices/{id}/void` | Void (requires no payments) |

### Payments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounting/payments` | List (filter: dates, method, patient) |
| POST | `/api/v1/accounting/payments` | Record payment → receipt |
| POST | `/api/v1/accounting/payments/{id}/void` | Void (blocked if day closed) |

### Expenses
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounting/expenses` | List (filter: dates, category, status) |
| POST | `/api/v1/accounting/expenses` | Record expense (WHT auto-calc) |
| PATCH | `/api/v1/accounting/expenses/{id}` | Update / approve |

### Closings & Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounting/closings` | List daily closings |
| POST | `/api/v1/accounting/closings` | Close day (cash reconciliation) |
| GET | `/api/v1/accounting/dashboard` | KPI dashboard |
| GET | `/api/v1/accounting/reports/daily` | Daily payment report |
| GET | `/api/v1/accounting/reports/monthly-pl` | Monthly P&L |
| GET | `/api/v1/accounting/reports/outstanding` | AR aging |
| GET | `/api/v1/accounting/reports/revenue-by-category` | Revenue by category |

## RBAC / สิทธิ์การใช้งาน
- View: any role with `accounting` module access
- Invoices & payments: admin, accountant, cashier, manager, front_desk
- Expenses, reports (P&L, revenue), closings, voids: admin, accountant, manager

## Document Numbers / เลขที่เอกสาร
`INV-YYYY-NNNNN` invoices · `TIV-YYYY-NNNNN` tax invoices · `RC-YYYY-NNNNN`
receipts · `EXP-YYYY-NNNNN` expenses · `SVC-…` services

## Database / ฐานข้อมูล
Migration `m7_001` (chains after `m6_001`):
`service_catalog`, `invoices`, `invoice_items`, `payments`, `expenses`,
`daily_closings`

## Files
```
module7/
├── backend/
│   ├── api/accounting_routes.py
│   ├── models/accounting_models.py
│   └── schemas/accounting_schemas.py
├── frontend/pages/AccountingDashboard.jsx
├── i18n/translations.py
├── migrations/m7_001_accounting.py
└── README.md
```
