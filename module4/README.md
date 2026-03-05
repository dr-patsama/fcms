# FCMS Module 4 — Pharmacy / เภสัชกรรม

## Features

- **Drug Master Catalogue**: Generic + brand names (EN/TH), category, form, strength, supplier, pricing
- **Stock Management**: Receive stock with lot/expiry tracking, manual adjustments with mandatory reason, FIFO dispensing
- **Prescription Flow**: EMR → Pharmacist verify → Dispense → Record (full audit trail)
- **Label Printing**: Bilingual medication labels (patient name TH/EN, drug, dose, frequency, instructions, clinic info)
- **Expiry Alerts**: Configurable 30/60/90 day warnings with near-expiry dashboard
- **Low-Stock Alerts**: Suggested reorder quantities based on reorder level
- **Dispensing Log**: Full audit with pharmacist ID, timestamp, lot number

## Drug Categories
| Category | Thai | Use |
|----------|------|-----|
| Hormonal | ฮอร์โมน | Progesterone, Estradiol, etc. |
| IVF Protocol | โปรโตคอล IVF | Gonal-F, Cetrotide, Ovidrel, Letrozole |
| Antibiotic | ยาปฏิชีวนะ | Doxycycline, Azithromycin |
| Analgesic | ยาแก้ปวด | Paracetamol, NSAIDs |
| Vitamin | วิตามิน | Folic Acid, supplements |
| Anesthetic | ยาชา | Lidocaine (procedures) |
| Anticoagulant | ยาต้านการแข็งตัว | Enoxaparin (Clexane) |

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pharmacy/drugs` | List drugs (search, filter, paginate) |
| POST | `/api/v1/pharmacy/drugs` | Add new drug |
| PATCH | `/api/v1/pharmacy/drugs/{id}` | Update drug |
| POST | `/api/v1/pharmacy/stock/receive` | Receive stock (GRN) |
| POST | `/api/v1/pharmacy/stock/adjust` | Manual stock adjustment |
| GET | `/api/v1/pharmacy/stock/levels` | Current stock levels |
| GET | `/api/v1/pharmacy/alerts` | Expiry + low-stock alerts |
| GET/POST | `/api/v1/pharmacy/prescriptions` | List/create prescriptions |
| POST | `/api/v1/pharmacy/prescriptions/{id}/verify` | Pharmacist verification |
| POST | `/api/v1/pharmacy/dispense` | Dispense medication |
| GET | `/api/v1/pharmacy/dispensing-log` | Dispensing audit log |
| POST | `/api/v1/pharmacy/labels/generate` | Generate medication label |
| GET | `/api/v1/pharmacy/stats` | Dashboard statistics |

## Access Control
| Role | Access |
|------|--------|
| Pharmacist | Full access (all operations) |
| Pharmacy Staff | Dispense, stock receive, labels |
| Physician | Create prescriptions, view stock |
| Nurse | View prescriptions, view stock |
| Admin | Full access |
