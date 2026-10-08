"""
Demo-only: seed 12 months of synthetic embryology history so /insight has monthly KPI series to chart.

    PYTHONPATH=. python scripts/seed_kpi_demo.py            # add (skips if already seeded)
    PYTHONPATH=. python scripts/seed_kpi_demo.py --reset    # remove the demo rows first
    PYTHONPATH=. python scripts/seed_kpi_demo.py --months 18 --per-month 8

Everything it creates is tagged (HN-KPI-*, CYC-KPI-*, EMB-KPI-*) so it can be removed again.
Never run against a production database — the figures are invented for demonstration only.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from module1.backend.core.database import SessionLocal, engine
from module1.backend.models.emr_models import Patient

# Module 2 models use uuid.UUID ids while the driver returns strings — batched INSERT … RETURNING cannot match them, so insert row by row.
engine.dialect.use_insertmanyvalues = False
from module1.backend.models.user_models import User
from module2.backend.models.lab_models import (
    TreatmentCycle, OocyteRetrieval, Oocyte, FertilizationRecord, FertilizationStatus, Embryo, EmbryoAssessment,
    BlastocystExpansion, ICMGrade, TEGrade, EmbryoCryopreservation, EmbryoWarming, WarmingStatus, EmbryoTransfer,
    EmbryoDisposition, SpermPreparation,
)
from journey.backend.models.journey_models import CycleOutcome  # noqa: F401  (registers journey tables)

rng = random.Random(20261007)


def reset(db):
    db.execute(text("""
        WITH c AS (SELECT id FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%'),
             e AS (SELECT id FROM embryos WHERE cycle_id IN (SELECT id FROM c))
        , d1 AS (DELETE FROM embryo_assessments WHERE embryo_id IN (SELECT id FROM e))
        , d2 AS (DELETE FROM embryo_cryopreservations WHERE embryo_id IN (SELECT id FROM e))
        , d3 AS (DELETE FROM embryo_warmings WHERE embryo_id IN (SELECT id FROM e))
        , d4 AS (DELETE FROM embryo_transfers WHERE embryo_id IN (SELECT id FROM e))
        , d5 AS (DELETE FROM cycle_outcomes WHERE cycle_id IN (SELECT id FROM c))
        , d6 AS (DELETE FROM sperm_preparations WHERE cycle_id IN (SELECT id FROM c))
        SELECT 1
    """))
    db.execute(text("DELETE FROM embryos WHERE cycle_id IN (SELECT id FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%')"))
    db.execute(text("""
        DELETE FROM fertilization_records WHERE oocyte_id IN (
          SELECT o.id FROM oocytes o JOIN oocyte_retrievals r ON r.id=o.retrieval_id
          WHERE r.cycle_id IN (SELECT id FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%'))
    """))
    db.execute(text("DELETE FROM oocytes WHERE retrieval_id IN (SELECT id FROM oocyte_retrievals WHERE cycle_id IN (SELECT id FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%'))"))
    db.execute(text("DELETE FROM oocyte_retrievals WHERE cycle_id IN (SELECT id FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%')"))
    db.execute(text("DELETE FROM treatment_cycles WHERE cycle_number LIKE 'CYC-KPI-%'"))
    db.execute(text("DELETE FROM patients WHERE hn_number LIKE 'HN-KPI-%'"))
    db.commit()


def month_profile(i: int, n: int) -> dict:
    """Slow drift + noise so bars cross the competence / benchmark lines over the year."""
    t = i / max(1, n - 1)
    return {
        "fert": 0.62 + 0.20 * t + rng.uniform(-0.05, 0.05),      # ICSI 2PN rate 62% → 82%
        "damage": 0.11 - 0.07 * t + rng.uniform(-0.02, 0.02),    # ICSI damage 11% → 4%
        "pn1": 0.03 + rng.uniform(-0.015, 0.015),
        "d2_4cell": 0.55 + 0.25 * t + rng.uniform(-0.06, 0.06),
        "d3_8cell": 0.50 + 0.22 * t + rng.uniform(-0.06, 0.06),
        "blast": 0.42 + 0.20 * t + rng.uniform(-0.06, 0.06),
        "good_blast": 0.55 + rng.uniform(-0.1, 0.1),
        "yield": 0.82 + 0.10 * t + rng.uniform(-0.04, 0.04),
        "mii": 0.76 + 0.10 * t + rng.uniform(-0.04, 0.04),
        "cpr": 0.30 + 0.15 * t + rng.uniform(-0.08, 0.08),
    }


def seed(db, months: int, per_month: int):
    phys = db.query(User).filter(User.role == "physician").first() or db.query(User).first()
    emb = db.query(User).filter(User.role == "embryologist").first() or phys
    today = date.today()
    first_of_month = today.replace(day=1)
    month_starts = []
    m = first_of_month
    for _ in range(months):
        month_starts.append(m)
        m = (m - timedelta(days=1)).replace(day=1)
    month_starts.reverse()

    seq = 0
    frozen_pool: list[tuple[Embryo, Patient]] = []
    for mi, ms in enumerate(month_starts):
        prof = month_profile(mi, months)
        n_cycles = per_month if ms != first_of_month else max(1, per_month // 3)   # current month to date
        for ci in range(n_cycles):
            seq += 1
            hn = f"HN-KPI-{seq:04d}"
            p = Patient(hn_number=hn, first_name_en=f"Demo{seq}", last_name_en="KPI", first_name_th=f"สาธิต{seq}", last_name_th="เคพีไอ",
                        gender="female", date_of_birth=date(1988 + rng.randint(0, 8), rng.randint(1, 12), rng.randint(1, 28)), preferred_language="th")
            db.add(p); db.flush()
            start = ms + timedelta(days=rng.randint(0, 6))
            d0 = start + timedelta(days=rng.randint(11, 14))
            if d0 > today:
                d0 = today - timedelta(days=1); start = d0 - timedelta(days=12)
            pgt = rng.random() < 0.3
            freeze_all = pgt or rng.random() < 0.35
            cyc = TreatmentCycle(cycle_number=f"CYC-KPI-{ms:%Y%m}-{ci + 1:02d}", patient_id=p.id, cycle_type="ivf_icsi", start_date=start,
                                 status="closed", d0_date=d0, medication_start_date=start, planned_et_day=None if freeze_all else 5,
                                 pgt=pgt, freeze_all=freeze_all, physician_id=phys.id, embryologist_id=emb.id, outcome="completed")
            db.add(cyc); db.flush()
            out = CycleOutcome(cycle_id=cyc.id, patient_id=p.id, ohss_grade="none")
            # ~4 % cancelled before OPU
            if rng.random() < 0.04:
                out.cancelled_before_opu = True; out.cancel_reason = "poor response"
                cyc.status = "cancelled"
                db.add(out); db.flush()
                continue
            if rng.random() < 0.012:
                out.ohss_grade = "moderate"
            follicles = rng.randint(8, 18)
            oocytes = max(1, round(follicles * min(0.98, prof["yield"])))
            mii = max(1, round(oocytes * min(0.95, prof["mii"])))
            ret = OocyteRetrieval(patient_id=p.id, cycle_id=cyc.id, procedure_date=d0, physician_id=phys.id, embryologist_id=emb.id,
                                  total_follicles_aspirated=follicles, total_oocytes_retrieved=oocytes, mii_count=mii,
                                  mi_count=max(0, oocytes - mii - 1), gv_count=1 if oocytes > mii else 0,
                                  complications="vaginal bleeding requiring observation" if rng.random() < 0.004 else None)
            db.add(ret); db.flush()
            if ret.complications:
                out.opu_complication = ret.complications
            db.add(SpermPreparation(cycle_id=cyc.id, patient_id=p.id, preparation_method="density gradient", used_for="ICSI",
                                    prepared_at=datetime.combine(d0, datetime.min.time(), tzinfo=timezone.utc), embryologist_id=emb.id,
                                    post_progressive_pct=round(rng.uniform(86, 98), 1)))
            two_pn: list[FertilizationRecord] = []
            for k in range(oocytes):
                is_mii = k < mii
                oo = Oocyte(retrieval_id=ret.id, oocyte_number=k + 1, maturity_stage="MII" if is_mii else ("MI" if k < oocytes - 1 else "GV"),
                            is_inseminated=is_mii, insemination_method="ICSI" if is_mii else None,
                            insemination_time=datetime.combine(d0, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=4) if is_mii else None)
                db.add(oo); db.flush()
                if not is_mii:
                    continue
                r = rng.random()
                if r < prof["fert"]:
                    st = FertilizationStatus.NORMAL_2PN
                elif r < prof["fert"] + prof["damage"]:
                    st = FertilizationStatus.DEGENERATED
                elif r < prof["fert"] + prof["damage"] + prof["pn1"]:
                    st = FertilizationStatus.ABNORMAL_1PN
                elif r < prof["fert"] + prof["damage"] + prof["pn1"] + 0.02:
                    st = FertilizationStatus.ABNORMAL_3PN
                else:
                    st = FertilizationStatus.UNFERTILIZED
                fr = FertilizationRecord(oocyte_id=oo.id, patient_id=p.id, status=st, embryologist_id=emb.id,
                                         check_time=datetime.combine(d0 + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1),
                                         pronuclei_count={"NORMAL_2PN": 2, "ABNORMAL_1PN": 1, "ABNORMAL_3PN": 3}.get(st.name, 0))
                db.add(fr); db.flush()
                if st == FertilizationStatus.NORMAL_2PN:
                    two_pn.append(fr)
            embryos: list[Embryo] = []
            blasts: list[Embryo] = []
            for j, fr in enumerate(two_pn):
                e = Embryo(embryo_code=f"EMB-KPI-{seq:04d}-{j + 1:02d}", patient_id=p.id, cycle_id=cyc.id, fertilization_record_id=fr.id, current_day=5)
                db.add(e); db.flush()
                embryos.append(e)
                d2_cells = 4 if rng.random() < prof["d2_4cell"] else rng.choice([2, 3, 5, 6])
                db.add(EmbryoAssessment(embryo_id=e.id, assessment_day=2, cell_count=d2_cells, fragmentation_pct=rng.choice([5, 10, 15, 20]), embryologist_id=emb.id,
                                        assessment_time=datetime.combine(d0 + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=2)))
                d3_cells = 8 if rng.random() < prof["d3_8cell"] else rng.choice([5, 6, 7, 9, 10])
                db.add(EmbryoAssessment(embryo_id=e.id, assessment_day=3, cell_count=d3_cells, fragmentation_pct=rng.choice([5, 10, 15, 20]), embryologist_id=emb.id,
                                        assessment_time=datetime.combine(d0 + timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=2)))
                if rng.random() < prof["blast"]:
                    good = rng.random() < prof["good_blast"]
                    db.add(EmbryoAssessment(embryo_id=e.id, assessment_day=5, embryologist_id=emb.id,
                                            expansion=rng.choice([BlastocystExpansion.FULL, BlastocystExpansion.EXPANDED, BlastocystExpansion.HATCHING]) if good else rng.choice([BlastocystExpansion.EARLY, BlastocystExpansion.CAVITATING, BlastocystExpansion.FULL]),
                                            icm_grade=rng.choice([ICMGrade.A, ICMGrade.B]) if good else ICMGrade.C, te_grade=rng.choice([TEGrade.A, TEGrade.B]) if good else rng.choice([TEGrade.B, TEGrade.C]),
                                            is_suitable_transfer=good, is_suitable_freeze=good,
                                            assessment_time=datetime.combine(d0 + timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=2)))
                    blasts.append(e)
                    if pgt:
                        e.is_pgta_tested = True
                        e.pgta_result = rng.choice(["euploid", "euploid", "aneuploid", "mosaic"]) if rng.random() < 0.96 else "no result"
                db.flush()
            et_date = d0 + timedelta(days=5)
            transferred: Embryo | None = None
            if not freeze_all and blasts and et_date <= today:
                transferred = blasts[0]
                transferred.disposition = EmbryoDisposition.FRESH_TRANSFER
                db.add(EmbryoTransfer(embryo_id=transferred.id, patient_id=p.id, cycle_id=cyc.id, physician_id=phys.id, embryologist_id=emb.id, transfer_type="fresh",
                                      transfer_date=datetime.combine(et_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=3),
                                      endometrial_thickness=round(rng.uniform(8, 12), 1), ultrasound_guided=True))
                _outcome(out, prof, et_date, today)
            for e in blasts:
                if e is transferred:
                    continue
                e.disposition = EmbryoDisposition.FROZEN
                db.add(EmbryoCryopreservation(embryo_id=e.id, embryologist_id=emb.id, method="vitrification", device="cryotop",
                                              freeze_date=datetime.combine(d0 + timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8),
                                              device_label=f"{p.hn_number} {e.embryo_code}"))
                frozen_pool.append((e, p))
            db.flush()
            db.add(out); db.flush()
        # FET cycles this month from the frozen pool (warming → survival → ET → outcome)
        for fi in range(max(1, per_month // 3)):
            if not frozen_pool:
                break
            e, p = frozen_pool.pop(0)
            fet_start = ms + timedelta(days=rng.randint(0, 10))
            w_date = fet_start + timedelta(days=16)
            if w_date > today:
                break
            seq += 1
            fet = TreatmentCycle(cycle_number=f"CYC-KPI-{ms:%Y%m}-F{fi + 1:02d}", patient_id=p.id, cycle_type="fet_hrt", start_date=fet_start, status="closed",
                                 d0_date=w_date, medication_start_date=fet_start, planned_et_day=0, physician_id=phys.id, embryologist_id=emb.id, outcome="completed")
            db.add(fet); db.flush()
            out = CycleOutcome(cycle_id=fet.id, patient_id=p.id, ohss_grade="none")
            survived = rng.random() < 0.96
            db.add(EmbryoWarming(embryo_id=e.id, embryologist_id=emb.id, status=WarmingStatus.SURVIVED if survived else WarmingStatus.DEGENERATED,
                                 warming_date=datetime.combine(w_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)))
            e.disposition = EmbryoDisposition.THAWED
            if survived:
                db.add(EmbryoTransfer(embryo_id=e.id, patient_id=p.id, cycle_id=fet.id, physician_id=phys.id, embryologist_id=emb.id, transfer_type="frozen",
                                      transfer_date=datetime.combine(w_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=4),
                                      endometrial_thickness=round(rng.uniform(8, 12), 1), ultrasound_guided=True))
                _outcome(out, prof, w_date, today)
            db.add(out); db.flush()
    db.commit()
    return seq


def _outcome(out: CycleOutcome, prof: dict, et_date: date, today: date):
    """Fill pregnancy outcome fields only as far as time has allowed them to be known."""
    days = (today - et_date).days
    if days < 12:
        return
    out.hcg_date = et_date + timedelta(days=12)
    hcg = rng.random() < prof["cpr"] + 0.10
    out.hcg_positive = hcg
    out.hcg_value = round(rng.uniform(80, 900), 1) if hcg else round(rng.uniform(0, 4), 1)
    if not hcg:
        return
    if days < 35:
        return
    cp = rng.random() < 0.85
    out.clinical_pregnancy = cp
    out.biochemical_only = not cp
    if not cp:
        return
    out.gestational_sacs = 2 if rng.random() < 0.08 else 1
    out.fetal_hearts = out.gestational_sacs
    if days < 84:
        return
    if rng.random() < 0.12:
        out.miscarriage = True
        return
    if rng.random() < 0.015:
        out.ectopic = True
        return
    out.ongoing_pregnancy = True
    if days >= 270:
        out.live_birth = True
        out.delivery_date = et_date + timedelta(days=266 - 5)
        out.babies = out.gestational_sacs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--per-month", type=int, default=6)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    db = SessionLocal()
    try:
        if a.reset:
            reset(db)
            print("removed previous KPI demo rows")
        if db.query(TreatmentCycle).filter(TreatmentCycle.cycle_number.like("CYC-KPI-%")).first():
            print("KPI demo data already present — use --reset to regenerate")
            return
        n = seed(db, a.months, a.per_month)
        print(f"seeded {n} demo cycles over {a.months} months")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
