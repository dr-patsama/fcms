# FCMS Module 3 — Ultrasound Interface / อัลตราซาวด์

## Overview

DICOM integration with **GE VOLUSON Swift** ultrasound machine via Orthanc PACS server.
Provides structured fertility-specific measurements, follicle tracking, and report generation.

## Architecture

```
GE VOLUSON Swift ──DICOM C-STORE──→ Orthanc Server ──REST API──→ FCMS Backend ──→ Frontend
     (LAN)              Port 4242        Port 8042       Port 8000        Port 3000
```

## Features

### DICOM Integration
- Orthanc PACS server receives images from VOLUSON via C-STORE
- Auto-detection of new studies
- Patient matching (VOLUSON Patient ID → FCMS HN number)
- DICOMweb viewer for image display in browser

### Fertility Measurements
- **Endometrium**: thickness, pattern (trilaminar/echogenic/homogeneous), echogenicity
- **Ovaries**: dimensions (L×W×H), volume, antral follicle count (AFC)
- **Individual follicles**: diameter tracking per follicle, per side
- **Uterus**: dimensions, position (anteverted/retroverted/axial)
- **Free fluid**: none / minimal / moderate / significant
- **Auto-computed**: total AFC, follicles ≥10mm / ≥14mm / ≥17mm, lead follicle

### Report Templates
| Template | Use Case |
|----------|----------|
| Baseline Scan | Initial assessment before treatment |
| Follicle Tracking | Monitoring during stimulation |
| Trigger Day | Assessment before trigger shot |
| Luteal Phase | Post-ovulation check |
| Early Pregnancy | Viability scan 6-8 weeks |
| SIS | Saline infusion sonography |

### Follicle Growth Tracking
- Visual chart showing follicle size progression across visits
- Color-coded by size: <10mm, 10-13mm, 14-16mm, ≥17mm (trigger-ready)
- Endometrial thickness overlay per visit
- Linked to treatment cycle timeline

## Files

```
module3/
├── backend/
│   └── api/
│       └── ultrasound_routes.py    ← API endpoints (studies, measurements, reports)
├── frontend/
│   └── pages/
│       └── UltrasoundDashboard.jsx ← Full UI (studies, tracking, measurement form, setup guide)
├── config/
│   └── orthanc.json                ← Orthanc DICOM server configuration
├── migrations/
│   └── m3_001_ultrasound.py        ← Database tables
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ultrasound/orthanc/status` | Orthanc connection check |
| GET | `/api/v1/ultrasound/studies` | List DICOM studies (paginated, filterable) |
| GET | `/api/v1/ultrasound/studies/{id}` | Study detail with series |
| GET | `/api/v1/ultrasound/studies/{id}/preview/{instance}` | Instance image preview |
| POST | `/api/v1/ultrasound/measurements` | Save structured measurements |
| GET | `/api/v1/ultrasound/measurements/patient/{id}` | Patient measurement history |
| GET | `/api/v1/ultrasound/report-templates` | List report templates |
| POST | `/api/v1/ultrasound/reports` | Create report |
| POST | `/api/v1/ultrasound/reports/{id}/sign` | Physician signs report |
| GET | `/api/v1/ultrasound/setup-guide` | VOLUSON DICOM setup instructions |

## VOLUSON Swift DICOM Setup

### On the Orthanc Server:
1. Install: `brew install orthanc` (macOS) or `apt install orthanc orthanc-dicomweb` (Ubuntu)
2. Copy `config/orthanc.json` → `/etc/orthanc/orthanc.json`
3. Update the VOLUSON IP address in the config
4. Start: `orthanc /etc/orthanc/orthanc.json`
5. Verify: `curl http://localhost:8042/system -u orthanc:orthanc`

### On the GE VOLUSON Swift:
1. Utilities → System Setup → Connectivity → Device Setup → DICOM Configuration
2. Click **Add** and enter:
   - Alias: `FCMS-Archive`
   - AE Title: `FCMS_ORTHANC`
   - IP Address: `<Orthanc server IP>`
   - Port: `4242`
   - Services: `STORE`
3. Set transfer syntax to **Explicit VR Little Endian**
4. Configure P-button or End Exam to auto-send to FCMS-Archive
5. Press **Verify** — should show "Verified OK"

## Database Tables

- `dicom_studies` — DICOM study metadata linked to patients
- `dicom_series` — Series within studies
- `ultrasound_measurements` — Structured fertility measurements
- `ultrasound_follicles` — Individual follicle size records
- `ultrasound_reports` — Generated reports with physician sign-off

## Access Control

| Role | Access |
|------|--------|
| Physician | Full (view, measure, report, sign) |
| Sonographer | View, measure, create report draft |
| Nurse | View studies and measurements |
| Embryologist | View (for cycle correlation) |
| Admin / IT Admin | Full + DICOM setup |
