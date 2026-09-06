"""
Live dashboard snapshots — OPD and Embryology Lab.
Pure SQL over existing module tables (CRM appointments, EMR visits, Lab orders,
Embryology records, DICOM studies, Cycle timelines). Each function returns a
JSON-serialisable dict; the SSE stream diffs snapshots and pushes on change.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import text
from sqlalchemy.orm import Session

TZ = ZoneInfo("Asia/Bangkok")

PROCEDURE_TYPES = ("egg_collection", "embryo_transfer", "iui", "hysteroscopy", "prp", "procedure")


def _now():
    return datetime.now(TZ)


def _rows(db: Session, sql: str, **p):
    return [dict(r._mapping) for r in db.execute(text(sql), p)]


def _json(v):
    if isinstance(v, (datetime,)):
        return v.astimezone(TZ).isoformat() if v.tzinfo else v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "hex") and not isinstance(v, (str, bytes)):  # UUID
        return str(v)
    if hasattr(v, "value"):  # enum
        return v.value
    if hasattr(v, "quantize"):  # Decimal
        return float(v)
    return v


def _clean(rows):
    return [{k: _json(v) for k, v in r.items()} for r in rows]


PATIENT_COLS = """p.hn_number AS hn, p.first_name_en, p.last_name_en, p.first_name_th, p.last_name_th,
                  p.preferred_language"""


# ═══════════════════════════════════════════════════════════════════════════
# OPD
# ═══════════════════════════════════════════════════════════════════════════
def opd_snapshot(db: Session) -> dict:
    now = _now()
    today = now.date()

    appts = _rows(db, f"""
        SELECT a.id, a.booking_number, a.appointment_time, a.end_time, a.appointment_type, a.appointment_type_th,
               a.department, a.room, a.status, a.priority, a.booking_source, a.chief_complaint, a.updated_at, a.created_at,
               {PATIENT_COLS},
               u.first_name_en AS provider_first, u.last_name_en AS provider_last, u.first_name_th AS provider_first_th
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        LEFT JOIN users u ON u.id = a.provider_id
        WHERE a.appointment_date = :today
        ORDER BY a.appointment_time
    """, today=today)

    def wait_minutes(a):
        if a["status"] != "checked_in":
            return None
        ref = a["updated_at"] or a["created_at"]
        if not ref:
            return None
        ref = ref.astimezone(TZ) if ref.tzinfo else ref.replace(tzinfo=TZ)
        return max(0, int((now - ref).total_seconds() // 60))

    for a in appts:
        a["wait_minutes"] = wait_minutes(a)
        a["is_procedure"] = a["appointment_type"] in PROCEDURE_TYPES
        a["is_late"] = (a["status"] in ("scheduled", "confirmed") and a["appointment_time"] is not None
                        and datetime.combine(today, a["appointment_time"], TZ) < now - timedelta(minutes=15))

    by_status = {}
    for a in appts:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1

    waiting = [a for a in appts if a["status"] == "checked_in"]
    waiting.sort(key=lambda a: (a["priority"] != "urgent", a["appointment_time"]))
    in_progress = [a for a in appts if a["status"] == "in_progress"]
    upcoming = [a for a in appts if a["status"] in ("scheduled", "confirmed")]
    procedures = [a for a in appts if a["is_procedure"] and a["status"] not in ("cancelled", "no_show")]

    lab_pending = _rows(db, f"""
        SELECT o.order_number, o.lab_type, o.status, o.priority, o.ordered_at, o.collected_at, o.resulted_at,
               {PATIENT_COLS}
        FROM lab_orders o JOIN patients p ON p.id = o.patient_id
        WHERE o.status IN ('pending','collected','processing','resulted')
          AND o.ordered_at >= :since
        ORDER BY CASE o.priority WHEN 'stat' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END, o.ordered_at
        LIMIT 100
    """, since=now - timedelta(days=3))

    us_today = _rows(db, f"""
        SELECT s.study_time, s.study_description, s.status, s.num_instances, {PATIENT_COLS}
        FROM dicom_studies s LEFT JOIN patients p ON p.id = s.patient_id
        WHERE s.study_date = :today ORDER BY s.study_time
    """, today=today)

    virtual = _rows(db, f"""
        SELECT v.scheduled_start, v.scheduled_end, v.status, v.actual_start, {PATIENT_COLS}
        FROM virtual_consultations v JOIN appointments a ON a.id = v.appointment_id
        JOIN patients p ON p.id = a.patient_id
        WHERE (v.scheduled_start AT TIME ZONE 'Asia/Bangkok')::date = :today
        ORDER BY v.scheduled_start
    """, today=today) if _table_exists(db, "virtual_consultations") and _col_exists(db, "virtual_consultations", "appointment_id") else []

    kpis = {
        "total": len(appts),
        "waiting": len(waiting),
        "in_progress": len(in_progress),
        "completed": by_status.get("completed", 0),
        "upcoming": len(upcoming),
        "no_show": by_status.get("no_show", 0),
        "cancelled": by_status.get("cancelled", 0),
        "procedures": len(procedures),
        "lab_pending": len([l for l in lab_pending if l["status"] in ("pending", "collected", "processing")]),
        "lab_unverified": len([l for l in lab_pending if l["status"] == "resulted"]),
        "us_today": len(us_today),
        "avg_wait": (round(sum(a["wait_minutes"] for a in waiting) / len(waiting)) if waiting else 0),
        "max_wait": max([a["wait_minutes"] for a in waiting], default=0),
    }
    return {
        "board": "opd", "generated_at": now.isoformat(), "date": today.isoformat(),
        "kpis": kpis, "by_status": by_status,
        "waiting": _clean(waiting), "in_progress": _clean(in_progress),
        "upcoming": _clean(upcoming[:30]), "procedures": _clean(procedures),
        "lab": _clean(lab_pending[:30]), "ultrasound": _clean(us_today), "virtual": _clean(virtual),
    }


# ═══════════════════════════════════════════════════════════════════════════
# EMBRYOLOGY LAB
# ═══════════════════════════════════════════════════════════════════════════
def embryo_snapshot(db: Session) -> dict:
    now = _now()
    today = now.date()

    opu_today = _rows(db, f"""
        SELECT r.id, r.procedure_date, r.start_time, r.end_time, r.total_follicles_aspirated,
               r.total_oocytes_retrieved, r.mii_count, r.mi_count, r.gv_count, r.degenerated_count,
               c.cycle_number, c.cycle_type, {PATIENT_COLS},
               e.first_name_en AS embryologist_first, e.first_name_th AS embryologist_first_th,
               (SELECT count(*) FROM oocytes o WHERE o.retrieval_id = r.id) AS oocytes_logged,
               (SELECT count(*) FROM oocytes o WHERE o.retrieval_id = r.id AND o.is_inseminated) AS inseminated
        FROM oocyte_retrievals r JOIN patients p ON p.id = r.patient_id
        LEFT JOIN treatment_cycles c ON c.id = r.cycle_id
        LEFT JOIN users e ON e.id = r.embryologist_id
        WHERE r.procedure_date = :today ORDER BY r.start_time NULLS LAST
    """, today=today)

    # OPU scheduled (appointments) that don't yet have a retrieval record
    opu_scheduled = _rows(db, f"""
        SELECT a.appointment_time, a.status, a.room, {PATIENT_COLS}
        FROM appointments a JOIN patients p ON p.id = a.patient_id
        WHERE a.appointment_date = :today AND a.appointment_type = 'egg_collection'
          AND a.status NOT IN ('cancelled','no_show')
          AND NOT EXISTS (SELECT 1 FROM oocyte_retrievals r WHERE r.patient_id = a.patient_id AND r.procedure_date = :today)
        ORDER BY a.appointment_time
    """, today=today)

    # Fertilization checks due: inseminated 14–22 h ago, no fertilization record yet
    fert_due = _rows(db, f"""
        SELECT o.oocyte_number, o.insemination_method, o.insemination_time,
               o.insemination_time + interval '17 hours' AS check_due, {PATIENT_COLS}
        FROM oocytes o JOIN oocyte_retrievals r ON r.id = o.retrieval_id JOIN patients p ON p.id = r.patient_id
        WHERE o.is_inseminated AND o.insemination_time BETWEEN :lo AND :hi
          AND NOT EXISTS (SELECT 1 FROM fertilization_records f WHERE f.oocyte_id = o.id)
        ORDER BY o.insemination_time
    """, lo=now - timedelta(hours=22), hi=now - timedelta(hours=14))

    # Embryos in culture (not yet dispositioned), grouped by patient & day
    culture = _rows(db, f"""
        SELECT e.embryo_code, e.current_day, e.is_pgta_tested, e.pgta_result, e.created_at,
               c.cycle_number, {PATIENT_COLS},
               (SELECT overall_grade FROM embryo_assessments x WHERE x.embryo_id = e.id ORDER BY assessment_day DESC, assessment_time DESC LIMIT 1) AS last_grade,
               (SELECT max(assessment_day) FROM embryo_assessments x WHERE x.embryo_id = e.id) AS last_assessed_day
        FROM embryos e JOIN patients p ON p.id = e.patient_id LEFT JOIN treatment_cycles c ON c.id = e.cycle_id
        WHERE e.disposition IS NULL AND e.created_at >= :since
        ORDER BY p.hn_number, e.embryo_code
    """, since=now - timedelta(days=8))
    for e in culture:
        # computed culture day from creation date (day of fertilization check = day 1)
        created = e["created_at"]
        created = created.astimezone(TZ) if created and created.tzinfo else created
        e["culture_day"] = (today - created.date()).days + 1 if created else e["current_day"]
        e["assessment_due"] = e["culture_day"] in (1, 3, 5, 6) and (e["last_assessed_day"] or 0) < e["culture_day"]
        e["decision_due"] = e["culture_day"] >= 5

    # group culture by patient
    by_patient = {}
    for e in culture:
        key = e["hn"]
        g = by_patient.setdefault(key, {"hn": e["hn"], "first_name_en": e["first_name_en"], "last_name_en": e["last_name_en"],
                                        "first_name_th": e["first_name_th"], "last_name_th": e["last_name_th"],
                                        "cycle_number": e["cycle_number"], "culture_day": e["culture_day"],
                                        "embryos": [], "assessment_due": 0, "decision_due": 0})
        g["embryos"].append({k: _json(e[k]) for k in ("embryo_code", "last_grade", "last_assessed_day", "is_pgta_tested", "pgta_result", "culture_day")})
        g["assessment_due"] += int(e["assessment_due"])
        g["decision_due"] += int(e["decision_due"])

    transfers = _rows(db, f"""
        SELECT t.transfer_date, t.transfer_type, t.endometrial_thickness, t.difficulty, t.notes, e.embryo_code,
               {PATIENT_COLS}, u.first_name_en AS physician_first, u.first_name_th AS physician_first_th
        FROM embryo_transfers t JOIN patients p ON p.id = t.patient_id JOIN embryos e ON e.id = t.embryo_id
        LEFT JOIN users u ON u.id = t.physician_id
        WHERE (t.transfer_date AT TIME ZONE 'Asia/Bangkok')::date = :today ORDER BY t.transfer_date
    """, today=today)
    et_scheduled = _rows(db, f"""
        SELECT a.appointment_time, a.status, a.room, {PATIENT_COLS}
        FROM appointments a JOIN patients p ON p.id = a.patient_id
        WHERE a.appointment_date = :today AND a.appointment_type = 'embryo_transfer' AND a.status NOT IN ('cancelled','no_show')
        ORDER BY a.appointment_time
    """, today=today)

    warmings = _rows(db, f"""
        SELECT w.warming_date, w.status, w.post_warm_grade, e.embryo_code, {PATIENT_COLS}
        FROM embryo_warmings w JOIN embryos e ON e.id = w.embryo_id JOIN patients p ON p.id = e.patient_id
        WHERE (w.warming_date AT TIME ZONE 'Asia/Bangkok')::date = :today ORDER BY w.warming_date
    """, today=today)
    freezes = _rows(db, f"""
        SELECT f.freeze_date, f.method, f.device, f.tank_id, f.canister, f.goblet, f.position, e.embryo_code,
               f.verified_by_id IS NOT NULL AS verified, {PATIENT_COLS}
        FROM embryo_cryopreservations f JOIN embryos e ON e.id = f.embryo_id JOIN patients p ON p.id = e.patient_id
        WHERE (f.freeze_date AT TIME ZONE 'Asia/Bangkok')::date = :today ORDER BY f.freeze_date
    """, today=today)

    cryo = _rows(db, """
        SELECT f.tank_id, count(*) AS embryos
        FROM embryo_cryopreservations f JOIN embryos e ON e.id = f.embryo_id
        WHERE e.disposition = 'frozen' GROUP BY f.tank_id ORDER BY f.tank_id
    """)
    cryo_total = sum(c["embryos"] for c in cryo)

    andrology = _rows(db, f"""
        SELECT s.id, s.created_at, {PATIENT_COLS}
        FROM semen_analyses s JOIN patients p ON p.id = s.patient_id
        WHERE (s.created_at AT TIME ZONE 'Asia/Bangkok')::date = :today ORDER BY s.created_at
    """, today=today) if _table_exists(db, "semen_analyses") else []

    fert_today = _rows(db, """
        SELECT status, count(*) AS n FROM fertilization_records
        WHERE (check_time AT TIME ZONE 'Asia/Bangkok')::date = :today GROUP BY status
    """, today=today)
    fert_counts = {str(_json(r["status"])): r["n"] for r in fert_today}
    fert_total = sum(fert_counts.values())

    kpis = {
        "opu_done": len(opu_today), "opu_scheduled": len(opu_scheduled),
        "oocytes_today": sum((r["total_oocytes_retrieved"] or 0) for r in opu_today),
        "mii_today": sum((r["mii_count"] or 0) for r in opu_today),
        "fert_checks_due": len(fert_due),
        "fert_rate_today": (round(100 * fert_counts.get("2PN", 0) / fert_total) if fert_total else None),
        "in_culture": len(culture), "patients_in_culture": len(by_patient),
        "assessments_due": sum(int(e["assessment_due"]) for e in culture),
        "transfers_today": len(transfers) + len(et_scheduled),
        "warmings_today": len(warmings), "freezes_today": len(freezes),
        "freezes_unverified": len([f for f in freezes if not f["verified"]]),
        "cryo_total": cryo_total, "andrology_today": len(andrology),
    }
    return {
        "board": "embryo", "generated_at": now.isoformat(), "date": today.isoformat(), "kpis": kpis,
        "opu": _clean(opu_today), "opu_scheduled": _clean(opu_scheduled),
        "fert_due": _clean(fert_due), "fert_counts": fert_counts,
        "culture": list(by_patient.values()),
        "transfers": _clean(transfers), "et_scheduled": _clean(et_scheduled),
        "warmings": _clean(warmings), "freezes": _clean(freezes),
        "cryo": _clean(cryo), "andrology": _clean(andrology),
    }


# ─── tiny schema guards (so the boards survive partial deployments) ──────────
_cache = {}


def _table_exists(db, name):
    if name not in _cache:
        _cache[name] = db.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": name}).scalar()
    return _cache[name]


def _col_exists(db, table, col):
    k = f"{table}.{col}"
    if k not in _cache:
        _cache[k] = db.execute(text("""SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"""),
                               {"t": table, "c": col}).scalar() is not None
    return _cache[k]


SNAPSHOTS = {"opd": opd_snapshot, "embryo": embryo_snapshot}
