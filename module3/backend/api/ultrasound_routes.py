"""
FCMS Module 3 — Ultrasound Interface
Backend: DICOM study management, Orthanc integration, fertility-specific measurements & reporting.

Architecture:
  GE VOLUSON Swift → DICOM C-STORE → Orthanc Server (LAN) → FCMS API → Frontend Viewer

The Voluson Swift pushes studies via DICOM C-STORE to an Orthanc server running on the clinic LAN.
FCMS polls/webhooks Orthanc for new studies, matches them to patients, and stores structured
measurements + reports in PostgreSQL. The frontend uses Orthanc's built-in DICOMweb for image viewing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from datetime import datetime, timezone, date
from typing import Optional, List
import uuid
import httpx

from ..core.database import get_db
from ..core.auth import get_current_user, require_roles, require_module_access
from ..models.user_models import User, AuditLog

router = APIRouter(prefix="/api/v1/ultrasound", tags=["Ultrasound / DICOM"])


# ═══════════════════════════════════════════════════════════
# CONFIGURATION — Orthanc Server Connection
# ═══════════════════════════════════════════════════════════

ORTHANC_CONFIG = {
    "url": "http://localhost:8042",       # Orthanc REST API
    "username": "orthanc",
    "password": "orthanc",
    "dicom_web_root": "/dicom-web",
    "ae_title": "FCMS_ORTHANC",           # Our AE Title for VOLUSON to push to
    "voluson_ae_title": "VOLUSON_SWIFT",   # VOLUSON Swift AE Title
    "port": 4242,                          # DICOM port Orthanc listens on
}


# ═══════════════════════════════════════════════════════════
# IN-MEMORY STORE (replace with SQLAlchemy models in production)
# These match the migration schema below
# ═══════════════════════════════════════════════════════════

# Studies, series, measurements will be stored in PostgreSQL via SQLAlchemy
# For this module, we define the API routes that work with both
# the Orthanc REST API (for DICOM data) and our PostgreSQL (for measurements/reports)


# ── Helpers ────────────────────────────────────────────────

def _audit(db, user, action, resource_id=None, detail=None, request=None):
    log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user.id if user else None,
        action=action, module="ultrasound",
        resource_type="study", resource_id=resource_id,
        detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.add(log)


async def _orthanc_get(path: str):
    """GET request to Orthanc REST API."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{ORTHANC_CONFIG['url']}{path}",
            auth=(ORTHANC_CONFIG["username"], ORTHANC_CONFIG["password"]),
            timeout=10.0,
        )
        r.raise_for_status()
        return r.json()


async def _orthanc_get_bytes(path: str):
    """GET binary data from Orthanc (e.g. images)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{ORTHANC_CONFIG['url']}{path}",
            auth=(ORTHANC_CONFIG["username"], ORTHANC_CONFIG["password"]),
            timeout=30.0,
        )
        r.raise_for_status()
        return r.content


# ═══════════════════════════════════════════════════════════
# 1. ORTHANC CONNECTION & STATUS
# ═══════════════════════════════════════════════════════════

@router.get("/orthanc/status")
async def orthanc_status(
    current_user: User = Depends(require_module_access("ultrasound")),
):
    """Check Orthanc server connectivity and stats."""
    try:
        system = await _orthanc_get("/system")
        stats = await _orthanc_get("/statistics")
        return {
            "connected": True,
            "orthanc_version": system.get("Version"),
            "dicom_aet": system.get("DicomAet"),
            "dicom_port": system.get("DicomPort"),
            "total_patients": stats.get("CountPatients", 0),
            "total_studies": stats.get("CountStudies", 0),
            "total_series": stats.get("CountSeries", 0),
            "total_instances": stats.get("CountInstances", 0),
            "disk_size_mb": round(int(stats.get("TotalDiskSize", 0)) / 1024 / 1024, 1),
            "config": {
                "orthanc_url": ORTHANC_CONFIG["url"],
                "ae_title": ORTHANC_CONFIG["ae_title"],
                "dicom_port": ORTHANC_CONFIG["port"],
                "voluson_ae_title": ORTHANC_CONFIG["voluson_ae_title"],
            },
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "config": {
                "orthanc_url": ORTHANC_CONFIG["url"],
                "ae_title": ORTHANC_CONFIG["ae_title"],
                "dicom_port": ORTHANC_CONFIG["port"],
                "voluson_ae_title": ORTHANC_CONFIG["voluson_ae_title"],
            },
        }


# ═══════════════════════════════════════════════════════════
# 2. STUDY MANAGEMENT (from Orthanc)
# ═══════════════════════════════════════════════════════════

@router.get("/studies")
async def list_studies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_name: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(require_module_access("ultrasound")),
):
    """List DICOM studies from Orthanc with optional filters."""
    try:
        # Get all study IDs from Orthanc
        study_ids = await _orthanc_get("/studies")

        studies = []
        for sid in study_ids:
            try:
                study = await _orthanc_get(f"/studies/{sid}")
                main = study.get("MainDicomTags", {})
                patient_main = study.get("PatientMainDicomTags", {})

                # Apply filters
                p_name = patient_main.get("PatientName", "")
                p_id = patient_main.get("PatientID", "")
                study_date = main.get("StudyDate", "")

                if patient_name and patient_name.lower() not in p_name.lower():
                    continue
                if patient_id and patient_id not in p_id:
                    continue
                if date_from and study_date < date_from.replace("-", ""):
                    continue
                if date_to and study_date > date_to.replace("-", ""):
                    continue

                # Format date
                formatted_date = study_date
                if len(study_date) == 8:
                    formatted_date = f"{study_date[:4]}-{study_date[4:6]}-{study_date[6:8]}"

                studies.append({
                    "orthanc_id": sid,
                    "study_instance_uid": main.get("StudyInstanceUID"),
                    "study_date": formatted_date,
                    "study_time": main.get("StudyTime", ""),
                    "study_description": main.get("StudyDescription", ""),
                    "accession_number": main.get("AccessionNumber", ""),
                    "referring_physician": main.get("ReferringPhysicianName", ""),
                    "patient_name": p_name,
                    "patient_id": p_id,
                    "patient_birth_date": patient_main.get("PatientBirthDate", ""),
                    "patient_sex": patient_main.get("PatientSex", ""),
                    "num_series": len(study.get("Series", [])),
                    "modality": main.get("ModalitiesInStudy", "US"),
                })
            except Exception:
                continue

        # Sort by date descending
        studies.sort(key=lambda s: s["study_date"], reverse=True)

        # Paginate
        total = len(studies)
        offset = (page - 1) * per_page
        paginated = studies[offset:offset + per_page]

        return {
            "studies": paginated,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc error: {str(e)}")


@router.get("/studies/{orthanc_id}")
async def get_study_detail(
    orthanc_id: str,
    request: Request,
    current_user: User = Depends(require_module_access("ultrasound")),
    db: Session = Depends(get_db),
):
    """Get full study details including all series and instance counts."""
    try:
        study = await _orthanc_get(f"/studies/{orthanc_id}")
        main = study.get("MainDicomTags", {})
        patient = study.get("PatientMainDicomTags", {})

        # Get series details
        series_list = []
        for series_id in study.get("Series", []):
            try:
                series = await _orthanc_get(f"/series/{series_id}")
                s_main = series.get("MainDicomTags", {})
                series_list.append({
                    "orthanc_id": series_id,
                    "series_instance_uid": s_main.get("SeriesInstanceUID"),
                    "series_number": s_main.get("SeriesNumber"),
                    "series_description": s_main.get("SeriesDescription", ""),
                    "modality": s_main.get("Modality", "US"),
                    "num_instances": len(series.get("Instances", [])),
                    "instances": series.get("Instances", []),
                })
            except Exception:
                continue

        _audit(db, current_user, "READ", orthanc_id,
               f"Viewed study for {patient.get('PatientName', 'unknown')}", request)
        db.commit()

        study_date = main.get("StudyDate", "")
        if len(study_date) == 8:
            study_date = f"{study_date[:4]}-{study_date[4:6]}-{study_date[6:8]}"

        return {
            "orthanc_id": orthanc_id,
            "study_instance_uid": main.get("StudyInstanceUID"),
            "study_date": study_date,
            "study_time": main.get("StudyTime", ""),
            "study_description": main.get("StudyDescription", ""),
            "accession_number": main.get("AccessionNumber", ""),
            "referring_physician": main.get("ReferringPhysicianName", ""),
            "institution": main.get("InstitutionName", ""),
            "patient_name": patient.get("PatientName", ""),
            "patient_id": patient.get("PatientID", ""),
            "patient_birth_date": patient.get("PatientBirthDate", ""),
            "patient_sex": patient.get("PatientSex", ""),
            "series": series_list,
            "num_series": len(series_list),
        }
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=404, detail="Study not found in Orthanc")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orthanc error: {str(e)}")


@router.get("/studies/{orthanc_id}/preview/{instance_id}")
async def get_instance_preview(
    orthanc_id: str,
    instance_id: str,
    current_user: User = Depends(require_module_access("ultrasound")),
):
    """Get a rendered PNG preview of a DICOM instance."""
    from fastapi.responses import Response
    try:
        image_bytes = await _orthanc_get_bytes(f"/instances/{instance_id}/preview")
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot render preview: {str(e)}")


# ═══════════════════════════════════════════════════════════
# 3. FERTILITY-SPECIFIC MEASUREMENTS
# ═══════════════════════════════════════════════════════════

@router.post("/measurements")
async def save_measurements(
    request: Request,
    current_user: User = Depends(require_module_access("ultrasound")),
    db: Session = Depends(get_db),
):
    """Save structured fertility ultrasound measurements.

    Expected body:
    {
        "orthanc_study_id": "...",
        "patient_id": "...",            // FCMS patient UUID
        "cycle_id": "...",              // optional treatment cycle UUID
        "exam_type": "follicle_tracking" | "baseline" | "luteal_phase" | "pregnancy_dating" | "sis" | "general",
        "exam_date": "2026-03-05",
        "endometrium": {
            "thickness_mm": 8.5,
            "pattern": "trilaminar" | "echogenic" | "homogeneous" | "not_assessed",
            "echogenicity": "hyperechoic" | "isoechoic" | "hypoechoic"
        },
        "right_ovary": {
            "length_mm": 30, "width_mm": 20, "height_mm": 25,
            "volume_ml": 7.5,
            "afc": 8,
            "follicles": [
                {"diameter_mm": 18.5, "location": "right"},
                {"diameter_mm": 14.2, "location": "right"},
            ]
        },
        "left_ovary": {
            "length_mm": 28, "width_mm": 18, "height_mm": 22,
            "volume_ml": 5.5,
            "afc": 6,
            "follicles": [
                {"diameter_mm": 16.0, "location": "left"},
            ]
        },
        "uterus": {
            "length_mm": 75, "width_mm": 45, "ap_mm": 35,
            "position": "anteverted" | "retroverted" | "axial",
            "notes": "Normal myometrium"
        },
        "free_fluid": "none" | "minimal" | "moderate" | "significant",
        "adnexa_notes": "No adnexal masses",
        "impression": "Growing dominant follicle right ovary, adequate endometrium",
        "plan": "Continue stimulation, recheck in 2 days"
    }
    """
    body = await request.json()

    measurement_id = str(uuid.uuid4())

    # Compute total AFC
    right_afc = body.get("right_ovary", {}).get("afc", 0) or 0
    left_afc = body.get("left_ovary", {}).get("afc", 0) or 0
    total_afc = right_afc + left_afc

    # Count follicles >= 10mm (clinically significant)
    right_follicles = body.get("right_ovary", {}).get("follicles", [])
    left_follicles = body.get("left_ovary", {}).get("follicles", [])
    all_follicles = right_follicles + left_follicles
    follicles_gte_10 = [f for f in all_follicles if f.get("diameter_mm", 0) >= 10]
    follicles_gte_14 = [f for f in all_follicles if f.get("diameter_mm", 0) >= 14]
    follicles_gte_17 = [f for f in all_follicles if f.get("diameter_mm", 0) >= 17]
    lead_follicle = max((f.get("diameter_mm", 0) for f in all_follicles), default=0)

    measurement = {
        "id": measurement_id,
        "orthanc_study_id": body.get("orthanc_study_id"),
        "patient_id": body.get("patient_id"),
        "cycle_id": body.get("cycle_id"),
        "exam_type": body.get("exam_type", "general"),
        "exam_date": body.get("exam_date"),
        "measured_by": current_user.id,
        "measured_by_name": f"{current_user.first_name_en} {current_user.last_name_en}",

        # Endometrium
        "endometrial_thickness_mm": body.get("endometrium", {}).get("thickness_mm"),
        "endometrial_pattern": body.get("endometrium", {}).get("pattern"),
        "endometrial_echogenicity": body.get("endometrium", {}).get("echogenicity"),

        # Ovaries
        "right_ovary": body.get("right_ovary"),
        "left_ovary": body.get("left_ovary"),

        # Computed
        "total_afc": total_afc,
        "follicles_gte_10mm": len(follicles_gte_10),
        "follicles_gte_14mm": len(follicles_gte_14),
        "follicles_gte_17mm": len(follicles_gte_17),
        "lead_follicle_mm": lead_follicle,
        "all_follicles": all_follicles,

        # Uterus
        "uterus": body.get("uterus"),
        "free_fluid": body.get("free_fluid", "none"),
        "adnexa_notes": body.get("adnexa_notes"),

        # Clinical
        "impression": body.get("impression"),
        "plan": body.get("plan"),

        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _audit(db, current_user, "CREATE", measurement_id,
           f"Saved US measurements for patient {body.get('patient_id')}, exam: {body.get('exam_type')}", request)
    db.commit()

    return measurement


@router.get("/measurements/patient/{patient_id}")
async def get_patient_measurements(
    patient_id: str,
    exam_type: Optional[str] = Query(None),
    cycle_id: Optional[str] = Query(None),
    current_user: User = Depends(require_module_access("ultrasound")),
):
    """Get all ultrasound measurements for a patient (for follicle tracking charts etc.)."""
    # In production, this queries PostgreSQL
    # Returns measurement history for charting follicle growth, endometrial progression
    return {
        "patient_id": patient_id,
        "measurements": [],
        "note": "Connect to PostgreSQL for persistent measurement storage"
    }


# ═══════════════════════════════════════════════════════════
# 4. REPORT TEMPLATES
# ═══════════════════════════════════════════════════════════

REPORT_TEMPLATES = {
    "baseline": {
        "name_en": "Baseline Scan",
        "name_th": "สแกนพื้นฐาน",
        "sections": ["uterus", "endometrium", "right_ovary", "left_ovary", "afc", "adnexa", "impression"],
        "description": "Initial assessment before treatment cycle",
    },
    "follicle_tracking": {
        "name_en": "Follicle Tracking",
        "name_th": "ติดตามฟอลลิเคิล",
        "sections": ["endometrium", "right_follicles", "left_follicles", "lead_follicle", "e2_correlation", "impression", "plan"],
        "description": "Monitoring follicle growth during stimulation",
    },
    "trigger_day": {
        "name_en": "Trigger Day Assessment",
        "name_th": "ประเมินวันฉีดทริกเกอร์",
        "sections": ["endometrium", "follicle_count_by_size", "lead_follicles", "expected_oocytes", "impression", "trigger_plan"],
        "description": "Assessment before trigger shot / oocyte retrieval",
    },
    "luteal_phase": {
        "name_en": "Luteal Phase Scan",
        "name_th": "สแกนระยะลูเทียล",
        "sections": ["endometrium", "corpus_luteum", "free_fluid", "impression"],
        "description": "Post-ovulation endometrial and corpus luteum assessment",
    },
    "early_pregnancy": {
        "name_en": "Early Pregnancy Scan",
        "name_th": "สแกนตั้งครรภ์ระยะแรก",
        "sections": ["gestational_sac", "yolk_sac", "fetal_pole", "crown_rump_length", "fetal_heart", "impression"],
        "description": "Viability scan at 6-8 weeks",
    },
    "sis": {
        "name_en": "Saline Infusion Sonography",
        "name_th": "อัลตราซาวด์ฉีดน้ำเกลือ",
        "sections": ["uterine_cavity", "endometrium_pre", "endometrium_post", "focal_lesions", "tubal_patency", "impression"],
        "description": "SIS / Sonohysterography assessment",
    },
}


@router.get("/report-templates")
async def list_report_templates(
    current_user: User = Depends(require_module_access("ultrasound")),
):
    """List available ultrasound report templates."""
    return {"templates": REPORT_TEMPLATES}


@router.post("/reports")
async def create_report(
    request: Request,
    current_user: User = Depends(require_module_access("ultrasound")),
    db: Session = Depends(get_db),
):
    """Create a structured ultrasound report.

    Body:
    {
        "measurement_id": "...",
        "template": "follicle_tracking",
        "patient_id": "...",
        "cycle_id": "...",
        "findings": { ... },
        "impression": "...",
        "plan": "...",
        "images": ["instance_id_1", "instance_id_2"],  // key images
        "signed": false
    }
    """
    body = await request.json()
    report_id = str(uuid.uuid4())

    report = {
        "id": report_id,
        "measurement_id": body.get("measurement_id"),
        "template": body.get("template"),
        "patient_id": body.get("patient_id"),
        "cycle_id": body.get("cycle_id"),
        "findings": body.get("findings", {}),
        "impression": body.get("impression"),
        "plan": body.get("plan"),
        "key_images": body.get("images", []),
        "created_by": current_user.id,
        "created_by_name": f"{current_user.first_name_en} {current_user.last_name_en}",
        "signed": body.get("signed", False),
        "signed_at": datetime.now(timezone.utc).isoformat() if body.get("signed") else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _audit(db, current_user, "CREATE", report_id,
           f"Created US report ({body.get('template')}) for patient {body.get('patient_id')}", request)
    db.commit()

    return report


@router.post("/reports/{report_id}/sign")
async def sign_report(
    report_id: str,
    request: Request,
    current_user: User = Depends(require_roles(["physician", "admin"])),
    db: Session = Depends(get_db),
):
    """Physician signs/finalizes an ultrasound report."""
    _audit(db, current_user, "UPDATE", report_id,
           f"Report signed by {current_user.first_name_en} {current_user.last_name_en}", request)
    db.commit()

    return {
        "report_id": report_id,
        "signed": True,
        "signed_by": f"{current_user.first_name_en} {current_user.last_name_en}",
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# 5. VOLUSON SWIFT DICOM CONFIG GUIDE
# ═══════════════════════════════════════════════════════════

@router.get("/setup-guide")
async def voluson_setup_guide(
    current_user: User = Depends(require_roles(["admin", "it_admin"])),
):
    """Returns step-by-step DICOM configuration guide for GE VOLUSON Swift → Orthanc."""
    return {
        "title": "GE VOLUSON Swift → FCMS DICOM Setup Guide",
        "prerequisites": [
            "Orthanc DICOM server installed on clinic LAN (apt install orthanc / brew install orthanc)",
            "VOLUSON Swift and Orthanc server on same network subnet",
            "Orthanc configuration: DICOM port 4242, HTTP port 8042",
        ],
        "orthanc_config": {
            "file": "/etc/orthanc/orthanc.json",
            "settings": {
                "DicomAet": ORTHANC_CONFIG["ae_title"],
                "DicomPort": ORTHANC_CONFIG["port"],
                "HttpPort": 8042,
                "RemoteAccessAllowed": True,
                "AuthenticationEnabled": True,
                "RegisteredUsers": {ORTHANC_CONFIG["username"]: ORTHANC_CONFIG["password"]},
                "DicomModalities": {
                    "VOLUSON_SWIFT": [ORTHANC_CONFIG["voluson_ae_title"], "VOLUSON_IP_ADDRESS", 4242]
                },
                "StableAge": 10,
                "DicomCheckCalledAet": False,
            },
        },
        "voluson_steps": [
            {
                "step": 1,
                "title": "Open DICOM Configuration",
                "instruction": "On the VOLUSON Swift: Utilities → System Setup → Connectivity → Device Setup → DICOM Configuration"
            },
            {
                "step": 2,
                "title": "Add FCMS Archive Store",
                "instruction": "Click 'Add' button and enter:",
                "settings": {
                    "Alias": "FCMS-Archive",
                    "AE Title": ORTHANC_CONFIG["ae_title"],
                    "IP Address": "<Orthanc server IP on clinic LAN>",
                    "Port": str(ORTHANC_CONFIG["port"]),
                    "Services": "STORE",
                }
            },
            {
                "step": 3,
                "title": "Configure Compression",
                "instruction": "Set transfer syntax to Explicit VR Little Endian for maximum compatibility. Disable JPEG compression for diagnostic quality."
            },
            {
                "step": 4,
                "title": "Set Auto-Send",
                "instruction": "Configure P-button or End Exam to auto-send studies to FCMS-Archive store."
            },
            {
                "step": 5,
                "title": "Verify Connection",
                "instruction": "Press 'Verify' button next to the FCMS-Archive entry. Should show 'Verified OK'."
            },
            {
                "step": 6,
                "title": "Test with a scan",
                "instruction": "Perform a test scan, end exam. Study should appear in FCMS within seconds."
            },
        ],
        "troubleshooting": [
            {"issue": "Verify fails", "fix": "Check IP address, ensure Orthanc is running, check firewall allows port 4242"},
            {"issue": "Images don't appear", "fix": "Check Orthanc logs (/var/log/orthanc/), verify AE Title matches exactly"},
            {"issue": "Slow transfer", "fix": "Ensure both devices on same switch/VLAN, check network cable quality"},
            {"issue": "Wrong patient match", "fix": "Ensure Patient ID on VOLUSON matches FCMS patient HN number"},
        ],
    }
