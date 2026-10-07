"""
KPIs — Module 15 Insight, first set. Indicators follow the ESHRE/Alpha Vienna consensus (laboratory)
and the ESHRE Maribor consensus (clinical) by name; definitions here are the standard ratios over the
data FCMS records. Benchmark/competence values are intentionally NOT hard-coded — load them from the
papers into `BENCHMARKS` when the clinic adopts them. Reported as percentages (not proportions).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .common import today

BENCHMARKS: dict[str, dict] = {}   # e.g. {"icsi_normal_fertilisation_rate": {"competence": 65, "benchmark": 80}}


def _one(db: Session, sql: str, **p):
    r = db.execute(text(sql), p).first()
    return dict(r._mapping) if r else {}


def _pct(n, d):
    if not d:
        return None
    return round(100.0 * float(n) / float(d), 1)


def compute(db: Session, start: date | None = None, end: date | None = None) -> dict:
    end = end or today()
    start = start or (end - timedelta(days=365))
    P = {"start": start, "end": end}

    cycles = _one(db, """
        SELECT count(*) AS started,
               count(*) FILTER (WHERE o.cancelled_before_opu) AS cancelled_before_opu,
               count(*) FILTER (WHERE c.cycle_type LIKE 'ivf%%' OR c.cycle_type = 'oocyte_cryo') AS stim_cycles,
               count(*) FILTER (WHERE o.ohss_grade IN ('moderate','severe')) AS ohss_mod_severe,
               count(*) FILTER (WHERE o.opu_complication IS NOT NULL AND o.opu_complication <> '') AS opu_complications
        FROM treatment_cycles c LEFT JOIN cycle_outcomes o ON o.cycle_id = c.id
        WHERE c.start_date BETWEEN :start AND :end
    """, **P)

    opu = _one(db, """
        SELECT count(*) AS opus, coalesce(sum(total_follicles_aspirated),0) AS follicles, coalesce(sum(total_oocytes_retrieved),0) AS oocytes,
               coalesce(sum(mii_count),0) AS mii
        FROM oocyte_retrievals WHERE procedure_date BETWEEN :start AND :end
    """, **P)

    fert = _one(db, """
        SELECT count(*) FILTER (WHERE o.insemination_method='ICSI') AS icsi_inseminated,
               count(*) FILTER (WHERE o.insemination_method='IVF') AS ivf_inseminated,
               count(*) FILTER (WHERE o.insemination_method='ICSI' AND f.status='NORMAL_2PN') AS icsi_2pn,
               count(*) FILTER (WHERE o.insemination_method='IVF'  AND f.status='NORMAL_2PN') AS ivf_2pn,
               count(*) FILTER (WHERE o.insemination_method='ICSI' AND f.status='DEGENERATED') AS icsi_degenerated,
               count(*) FILTER (WHERE f.status='ABNORMAL_3PN' AND o.insemination_method='IVF') AS ivf_3pn,
               count(*) FILTER (WHERE f.status='ABNORMAL_1PN') AS pn1,
               count(*) FILTER (WHERE f.status='NORMAL_2PN') AS all_2pn
        FROM oocytes o JOIN oocyte_retrievals r ON r.id=o.retrieval_id
        LEFT JOIN fertilization_records f ON f.oocyte_id=o.id
        WHERE r.procedure_date BETWEEN :start AND :end AND o.is_inseminated
    """, **P)

    dev = _one(db, """
        WITH e AS (
          SELECT e.id FROM embryos e JOIN treatment_cycles c ON c.id=e.cycle_id WHERE c.start_date BETWEEN :start AND :end
        )
        SELECT (SELECT count(*) FROM e) AS embryos,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=3 AND a.cell_count>=6) AS d3_good,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=3) AS d3_assessed,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day IN (5,6) AND a.expansion IS NOT NULL) AS blastocysts,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day IN (5,6) AND a.expansion IN ('FULL','EXPANDED','HATCHING','HATCHED') AND a.icm_grade IN ('A','B') AND a.te_grade IN ('A','B')) AS good_blastocysts,
               (SELECT count(*) FROM embryos x JOIN e ON e.id=x.id WHERE x.is_pgta_tested) AS biopsied,
               (SELECT count(*) FROM embryo_cryopreservations cp JOIN e ON e.id=cp.embryo_id) AS frozen
    """, **P)

    warm = _one(db, """
        SELECT count(*) AS warmed, count(*) FILTER (WHERE status='SURVIVED') AS survived
        FROM embryo_warmings WHERE warming_date BETWEEN :start AND :end
    """, **P)

    et = _one(db, """
        WITH t AS (SELECT cycle_id, count(*) AS n FROM embryo_transfers WHERE transfer_date BETWEEN :start AND :end GROUP BY cycle_id)
        SELECT count(*) AS et_cycles, coalesce(sum(n),0) AS embryos_transferred,
               count(*) FILTER (WHERE o.hcg_positive) AS hcg_positive,
               count(*) FILTER (WHERE o.clinical_pregnancy) AS clinical_pregnancies,
               coalesce(sum(o.fetal_hearts),0) AS fetal_hearts,
               count(*) FILTER (WHERE o.gestational_sacs >= 2) AS multiple,
               count(*) FILTER (WHERE o.miscarriage) AS miscarriages,
               count(*) FILTER (WHERE o.ectopic) AS ectopic,
               count(*) FILTER (WHERE o.ongoing_pregnancy) AS ongoing,
               count(*) FILTER (WHERE o.live_birth) AS live_births
        FROM t LEFT JOIN cycle_outcomes o ON o.cycle_id=t.cycle_id
    """, **P)

    ops = _one(db, """
        SELECT count(*) FILTER (WHERE requires_witness AND status='done') AS witnessed_steps,
               count(*) FILTER (WHERE requires_witness AND status='done' AND witness_session_id IS NOT NULL) AS e_witnessed,
               (SELECT count(*) FROM witness_sessions WHERE result='manual' AND started_at::date BETWEEN :start AND :end) AS manual_witness,
               (SELECT count(*) FROM witness_incidents WHERE created_at::date BETWEEN :start AND :end) AS mismatches,
               (SELECT count(*) FROM cycle_consents WHERE status='signed' AND signed_channel='patient_app' AND signed_at::date BETWEEN :start AND :end) AS consents_in_app,
               (SELECT count(*) FROM cycle_medication_doses WHERE calendar_date BETWEEN :start AND :end AND calendar_date < :end) AS doses_due,
               (SELECT count(*) FROM cycle_medication_doses WHERE calendar_date BETWEEN :start AND :end AND calendar_date < :end AND taken_at IS NOT NULL) AS doses_taken
        FROM lab_tasks WHERE scheduled_date BETWEEN :start AND :end
    """, **P)

    lab = {
        "oocyte_yield_per_follicle_pct": _pct(opu.get("oocytes"), opu.get("follicles")),
        "mii_rate_pct": _pct(opu.get("mii"), opu.get("oocytes")),
        "icsi_normal_fertilisation_rate_pct": _pct(fert.get("icsi_2pn"), fert.get("icsi_inseminated")),
        "icsi_damage_rate_pct": _pct(fert.get("icsi_degenerated"), fert.get("icsi_inseminated")),
        "ivf_normal_fertilisation_rate_pct": _pct(fert.get("ivf_2pn"), fert.get("ivf_inseminated")),
        "ivf_polyspermy_rate_pct": _pct(fert.get("ivf_3pn"), fert.get("ivf_inseminated")),
        "one_pn_rate_pct": _pct(fert.get("pn1"), (fert.get("icsi_inseminated") or 0) + (fert.get("ivf_inseminated") or 0)),
        "day3_development_rate_pct": _pct(dev.get("d3_good"), fert.get("all_2pn")),
        "blastocyst_development_rate_pct": _pct(dev.get("blastocysts"), fert.get("all_2pn")),
        "good_blastocyst_rate_pct": _pct(dev.get("good_blastocysts"), fert.get("all_2pn")),
        "blastocyst_cryosurvival_rate_pct": _pct(warm.get("survived"), warm.get("warmed")),
        "implantation_rate_pct": _pct(et.get("fetal_hearts"), et.get("embryos_transferred")),
        "counts": {**opu, **fert, **dev, **warm},
    }
    clinical = {
        "cycles_started": cycles.get("started"),
        "cancellation_before_opu_rate_pct": _pct(cycles.get("cancelled_before_opu"), cycles.get("stim_cycles")),
        "ohss_moderate_severe_rate_pct": _pct(cycles.get("ohss_mod_severe"), cycles.get("stim_cycles")),
        "opu_complication_rate_pct": _pct(cycles.get("opu_complications"), opu.get("opus")),
        "hcg_positive_rate_per_et_pct": _pct(et.get("hcg_positive"), et.get("et_cycles")),
        "clinical_pregnancy_rate_per_et_pct": _pct(et.get("clinical_pregnancies"), et.get("et_cycles")),
        "multiple_pregnancy_rate_pct": _pct(et.get("multiple"), et.get("clinical_pregnancies")),
        "miscarriage_rate_pct": _pct(et.get("miscarriages"), et.get("clinical_pregnancies")),
        "ectopic_rate_pct": _pct(et.get("ectopic"), et.get("clinical_pregnancies")),
        "ongoing_pregnancy_rate_per_et_pct": _pct(et.get("ongoing"), et.get("et_cycles")),
        "live_birth_rate_per_et_pct": _pct(et.get("live_births"), et.get("et_cycles")),
        "live_birth_rate_per_started_cycle_pct": _pct(et.get("live_births"), cycles.get("started")),
        "counts": {**cycles, **et},
    }
    operational = {
        "steps_electronically_witnessed_pct": _pct(ops.get("e_witnessed"), ops.get("witnessed_steps")),
        "manual_witness_count": ops.get("manual_witness"),
        "witness_mismatches": ops.get("mismatches"),
        "consents_signed_in_app": ops.get("consents_in_app"),
        "medication_adherence_pct": _pct(ops.get("doses_taken"), ops.get("doses_due")),
        "counts": ops,
    }
    return {"period": {"start": str(start), "end": str(end)}, "laboratory": lab, "clinical": clinical,
            "operational": operational, "benchmarks": BENCHMARKS,
            "references": ["ESHRE/Alpha Vienna consensus (2017) — laboratory KPIs", "ESHRE Maribor consensus (2021) — clinical PIs"]}


def monthly_series(db: Session, months: int = 12) -> list[dict]:
    out = []
    end = today().replace(day=1)
    for i in range(months):
        m_end = end - timedelta(days=1)
        m_start = m_end.replace(day=1)
        k = compute(db, m_start, m_end)
        out.append({"month": m_start.strftime("%Y-%m"),
                    "cycles_started": k["clinical"]["cycles_started"],
                    "opus": k["laboratory"]["counts"].get("opus"),
                    "et_cycles": k["clinical"]["counts"].get("et_cycles"),
                    "clinical_pregnancy_rate_per_et_pct": k["clinical"]["clinical_pregnancy_rate_per_et_pct"],
                    "icsi_normal_fertilisation_rate_pct": k["laboratory"]["icsi_normal_fertilisation_rate_pct"],
                    "blastocyst_development_rate_pct": k["laboratory"]["blastocyst_development_rate_pct"]})
        end = m_start
    return list(reversed(out))
