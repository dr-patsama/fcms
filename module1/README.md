# FCMS Module 1 — EMR (Electronic Medical Records)

## Overview
Foundation module providing authentication, RBAC, patient management, and clinical documentation.

## Features

### Authentication & RBAC
- JWT-based authentication with refresh tokens
- 15 user roles with module-level access control
- MFA (TOTP) mandatory for clinical roles
- Account lockout after failed attempts
- Full audit logging (PDPA compliant)

### Patient Management
- HN auto-generation (HN-YYYY-NNNNN)
- Thai ID / Passport support
- Bilingual names (EN/TH)
- Search by name, HN, phone, ID number
- Medical history (chronic diseases, surgeries, medications, allergies)
- Fertility-specific history (gravida/para, cycle info, previous treatments)

### Clinical Documentation
- Visit management (scheduled → checked_in → in_progress → completed)
- SOAP notes with physician signing
- ICD-10 diagnosis coding
- Consent form tracking

### 15 User Roles
| Role | Level | Modules |
|------|-------|---------|
| admin | 100 | All |
| it_admin | 95 | All |
| physician | 90 | EMR, Lab, US, Pharmacy, OR, CRM |
| embryologist | 85 | EMR, Lab, US, OR |
| lab_supervisor | 80 | Lab |
| nurse | 70 | EMR, Lab, US, Pharmacy, OR, CRM |
| lab_technician | 70 | Lab |
| sonographer | 65 | Ultrasound |
| pharmacist | 65 | Pharmacy |
| supply_manager | 60 | Supplies |
| pharmacy_staff | 55 | Pharmacy, Supplies |
| receptionist | 50 | EMR, CRM |
| billing_staff | 50 | Accounting |
| marketing_staff | 40 | Social Media, CRM |
| patient | 10 | Patient Portal |

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/login | Login (email + password + optional MFA) |
| POST | /api/v1/auth/register | Create user (admin only) |
| POST | /api/v1/auth/mfa/setup | Enable MFA for current user |
| GET | /api/v1/auth/me | Get current user profile |

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/patients/ | Create patient |
| GET | /api/v1/patients/ | List/search patients |
| GET | /api/v1/patients/{id} | Get patient details |
| PATCH | /api/v1/patients/{id} | Update patient |
| PUT | /api/v1/patients/{id}/medical-history | Update medical history |
| PUT | /api/v1/patients/{id}/fertility-history | Update fertility history |

### Visits
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/visits/ | Create visit |
| GET | /api/v1/visits/patient/{id} | List patient visits |
| PATCH | /api/v1/visits/{id}/status | Update visit status |
| POST | /api/v1/visits/soap-notes | Create SOAP note |
| PATCH | /api/v1/visits/soap-notes/{id}/sign | Sign SOAP note |
| POST | /api/v1/visits/diagnoses | Add ICD-10 diagnosis |

## Database Tables (10 tables)
users, user_sessions, audit_logs, patients, medical_histories,
fertility_histories, visits, soap_notes, visit_diagnoses, consent_forms

## Default Admin
- Email: admin@fcms.clinic
- Password: FCMSadmin2026!
