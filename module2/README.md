# FCMS Module 2 — Lab Management

## Overview

Complete lab management for fertility clinics covering three sub-labs:

### 🔬 General Lab
- Lab order lifecycle: Pending → Collected → Processing → Resulted → Verified
- Auto-flagging: Results automatically flagged against reference ranges (N/L/H/LL/HH)
- Specimen tracking with barcode generation
- 20+ pre-seeded fertility-specific test panels (FSH, LH, AMH, E2, etc.)
- Bilingual test names (English / Thai)

### 🧬 Embryology Lab
- Treatment cycle management (IVF / ICSI / IUI / FET)
- Oocyte retrieval with individual oocyte tracking
- Day 1 fertilization check (2PN/1PN/3PN/0PN/DG)
- Auto embryo creation from 2PN fertilization
- Daily embryo assessment (Day 2-6):
  - Cleavage: cell count, fragmentation, symmetry
  - Blastocyst: expansion (1-6), ICM grade (A-C), TE grade (A-C)
- Cryopreservation with tank/canister/goblet/position tracking
- Embryo warming with survival status
- Embryo transfer with outcome tracking
- PGT-A result recording

### 🔬 Andrology Lab
- Semen analysis per WHO 2021 reference values
- Auto-diagnosis: normozoospermia, oligozoospermia, asthenozoospermia, teratozoospermia, OAT
- WHO reference check (auto-compare all parameters)
- Sperm preparation tracking (swim-up, density gradient, wash)
- Sperm cryopreservation with consent tracking

## Data Import

### Excel/CSV Import Endpoints
- `POST /api/v1/lab/import/inventory` — Import pharmacy/supply inventory
- `POST /api/v1/lab/import/patients` — Import patient/client history
- `GET /api/v1/lab/import/template/{type}` — Download blank template

### Supported Formats
- `.xlsx` (Excel)
- `.xls` (Legacy Excel)
- `.csv` (Comma-separated)
- `.tsv` (Tab-separated)

### Import Features
- Flexible column matching (supports Thai and English column headers)
- Upsert logic: existing records updated, new records created
- Auto-generate HN numbers for patients without one
- Validation with detailed error reporting per row

## API Endpoints

### General Lab
| Method | Endpoint | Role |
|--------|----------|------|
| POST | /api/v1/lab/orders | physician, nurse, lab_tech |
| GET | /api/v1/lab/orders | physician, nurse, lab_tech |
| GET | /api/v1/lab/orders/{id} | any authenticated |
| PATCH | /api/v1/lab/orders/{id}/status | lab_tech, embryologist |
| POST | /api/v1/lab/specimens | lab_tech, nurse |
| POST | /api/v1/lab/results | lab_tech |
| PATCH | /api/v1/lab/results/{id}/verify | physician, lab_supervisor |
| GET | /api/v1/lab/patients/{id}/results | any authenticated |

### Embryology
| Method | Endpoint | Role |
|--------|----------|------|
| POST | /api/v1/lab/cycles | physician, embryologist |
| GET | /api/v1/lab/cycles/{id} | any authenticated |
| POST | /api/v1/lab/retrievals | embryologist |
| POST | /api/v1/lab/fertilization | embryologist |
| POST | /api/v1/lab/embryos/{id}/assessments | embryologist |
| POST | /api/v1/lab/embryos/{id}/freeze | embryologist |
| POST | /api/v1/lab/embryos/{id}/warm | embryologist |
| POST | /api/v1/lab/embryos/{id}/transfer | embryologist, physician |
| GET | /api/v1/lab/patients/{id}/embryos | any authenticated |

### Andrology
| Method | Endpoint | Role |
|--------|----------|------|
| POST | /api/v1/lab/semen/analyses | lab_tech, embryologist |
| GET | /api/v1/lab/semen/patients/{id} | any authenticated |
| POST | /api/v1/lab/sperm/preparation | embryologist |

## Database Tables (19 tables)

### General Lab
- `lab_test_panels` — Master test catalogue
- `lab_orders` — Orders from EMR
- `lab_order_items` — Individual tests per order
- `lab_specimens` — Specimen tracking
- `lab_results` — Test results

### Embryology
- `treatment_cycles` — IVF/ICSI/IUI cycles
- `oocyte_retrievals` — Egg collection
- `oocytes` — Individual oocyte records
- `fertilization_records` — Day 1 checks
- `embryos` — Core embryo tracking
- `embryo_assessments` — Daily grading
- `embryo_cryopreservations` — Freezing
- `embryo_warmings` — Thawing
- `embryo_transfers` — Transfer procedures

### Andrology
- `semen_analyses` — SA results
- `sperm_preparations` — Prep for IUI/IVF/ICSI
- `sperm_cryopreservations` — Sperm banking

### Import Support
- `inventory_items` — Imported inventory
- `patient_import_history` — Imported clinical notes

## Design System

- **Font**: Cloud (Thin / Light / Regular / SemiBold / Bold + italics)
- **Colors**: Sapphire Blue `#0F52BA` / Emerald `#009473` / Ruby Red `#E0115F`
- **Sidebar**: Sapphire Deep `#151667`
- See `/design-system/DESIGN_SYSTEM.md` for full reference
