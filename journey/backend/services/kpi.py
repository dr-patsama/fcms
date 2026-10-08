"""
KPIs — Module 15 Insight.

Laboratory indicators follow the ESHRE/Alpha **Vienna consensus** (2017); clinical indicators follow the
ESHRE **Maribor consensus** (Hum Reprod Open 2021, hoab022). Competence = minimum expected value,
benchmark = aspirational (best-practice) value, as published. Where a paper gives a single limit or no
value, that is stated instead of inventing one. All rates are percentages.

Sources
  Vienna: https://www.eshre.eu/-/media/sitecore-files/SIGs/Safety-and-quality/The-Vienna-consenus_Lab-KPI.pdf
  Maribor: https://doi.org/10.1093/hropen/hoab022 (one-page summary:
           https://www.eshre.eu/-/media/sitecore-files/Guidelines/ART_PIs/Performance-indicators-PIs-for-clinical-practice1page-summary.pdf)
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .common import today

VIENNA = "Vienna consensus 2017 (ESHRE/Alpha)"
MARIBOR = "Maribor consensus 2021 (ESHRE)"

# direction: "higher" = higher is better (competence is a floor); "lower" = lower is better (competence is a ceiling)
BENCHMARKS: dict[str, dict] = {
    # ── Vienna — reference indicators (expected ranges, not competence/benchmark pairs) ──
    "oocyte_yield_per_follicle_pct":      {"competence": 80, "benchmark": 95, "direction": "higher", "kind": "reference", "source": VIENNA,
                                           "note": "Expected range 80–95% (oocytes retrieved / follicles measured on the day of trigger)."},
    "mii_rate_pct":                        {"competence": 75, "benchmark": 90, "direction": "higher", "kind": "reference", "source": VIENNA + " · " + MARIBOR,
                                           "note": "Vienna expected range 75–90% of COCs; Maribor competence 74%, benchmark 75–90%."},
    # ── Vienna — performance indicators ──
    "sperm_progressive_motility_post_prep_pct": {"competence": 90, "benchmark": 95, "direction": "higher", "kind": "PI", "source": VIENNA},
    "ivf_polyspermy_rate_pct":             {"competence": 6, "benchmark": None, "direction": "lower", "kind": "PI", "source": VIENNA, "note": "Consensus limit < 6%; no separate benchmark."},
    "one_pn_rate_ivf_pct":                 {"competence": 5, "benchmark": None, "direction": "lower", "kind": "PI", "source": VIENNA, "note": "Consensus limit < 5% of COCs inseminated."},
    "one_pn_rate_icsi_pct":                {"competence": 3, "benchmark": None, "direction": "lower", "kind": "PI", "source": VIENNA, "note": "Consensus limit < 3% of MII injected."},
    "good_blastocyst_rate_pct":            {"competence": 30, "benchmark": 40, "direction": "higher", "kind": "PI", "source": VIENNA},
    # ── Vienna — key performance indicators ──
    "icsi_damage_rate_pct":                {"competence": 10, "benchmark": 5, "direction": "lower", "kind": "KPI", "source": VIENNA},
    "icsi_normal_fertilisation_rate_pct":  {"competence": 65, "benchmark": 80, "direction": "higher", "kind": "KPI", "source": VIENNA},
    "ivf_normal_fertilisation_rate_pct":   {"competence": 60, "benchmark": 75, "direction": "higher", "kind": "KPI", "source": VIENNA},
    "failed_fertilisation_rate_pct":       {"competence": 5, "benchmark": None, "direction": "lower", "kind": "KPI", "source": VIENNA, "note": "< 5% of stimulated IVF cycles."},
    "cleavage_rate_pct":                   {"competence": 95, "benchmark": 99, "direction": "higher", "kind": "KPI", "source": VIENNA},
    "day2_development_rate_pct":           {"competence": 50, "benchmark": 80, "direction": "higher", "kind": "KPI", "source": VIENNA, "note": "4-cell embryos on Day 2 / normally fertilised oocytes."},
    "day3_development_rate_pct":           {"competence": 45, "benchmark": 70, "direction": "higher", "kind": "KPI", "source": VIENNA, "note": "8-cell embryos on Day 3 / normally fertilised oocytes."},
    "blastocyst_development_rate_pct":     {"competence": 40, "benchmark": 60, "direction": "higher", "kind": "KPI", "source": VIENNA},
    "successful_biopsy_rate_pct":          {"competence": 90, "benchmark": 95, "direction": "higher", "kind": "KPI", "source": VIENNA, "note": "Biopsies with a result / biopsies performed."},
    "blastocyst_cryosurvival_rate_pct":    {"competence": 90, "benchmark": 99, "direction": "higher", "kind": "KPI", "source": VIENNA},
    "implantation_rate_cleavage_pct":      {"competence": 25, "benchmark": 35, "direction": "higher", "kind": "KPI", "source": VIENNA, "note": "Gestational sacs / cleavage-stage embryos transferred."},
    "implantation_rate_blastocyst_pct":    {"competence": 35, "benchmark": 60, "direction": "higher", "kind": "KPI", "source": VIENNA, "note": "Gestational sacs / blastocysts transferred."},
    # ── Maribor — clinical performance indicators (reference population: women < 40, own fresh oocytes, no PGT) ──
    "cancellation_before_opu_rate_pct":    {"competence": 6, "benchmark": 3.5, "direction": "lower", "kind": "PI", "source": MARIBOR,
                                           "note": "Reference population. Poor responders 40/20, normal 20/7, high 3/1.5."},
    "ohss_moderate_severe_rate_pct":       {"competence": 1.5, "benchmark": 0.5, "direction": "lower", "kind": "PI", "source": MARIBOR,
                                           "note": "Antagonist protocol, reference population (agonist: 2.5 / 1)."},
    "opu_complication_rate_pct":           {"competence": 0.5, "benchmark": 0.1, "direction": "lower", "kind": "PI", "source": MARIBOR,
                                           "note": "Complications needing additional intervention or admission, excluding OHSS."},
    "clinical_pregnancy_rate_per_et_pct":  {"competence": None, "benchmark": None, "direction": "higher", "kind": "PI", "source": MARIBOR,
                                           "note": "No consensus value — to be set locally (CNR means 32.2% / 35.5%)."},
    "multiple_pregnancy_rate_pct":         {"competence": 13, "benchmark": 7.5, "direction": "lower", "kind": "PI", "source": MARIBOR},
    # ── FCMS indicators without a published consensus target ──
    "hcg_positive_rate_per_et_pct":        {"competence": None, "benchmark": None, "direction": "higher", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "miscarriage_rate_pct":                {"competence": None, "benchmark": None, "direction": "lower", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "ectopic_rate_pct":                    {"competence": None, "benchmark": None, "direction": "lower", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "ongoing_pregnancy_rate_per_et_pct":   {"competence": None, "benchmark": None, "direction": "higher", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "live_birth_rate_per_et_pct":          {"competence": None, "benchmark": None, "direction": "higher", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "live_birth_rate_per_started_cycle_pct": {"competence": None, "benchmark": None, "direction": "higher", "kind": "local", "source": "FCMS", "note": "No published target — set locally."},
    "steps_electronically_witnessed_pct":  {"competence": 95, "benchmark": 100, "direction": "higher", "kind": "local", "source": "FCMS", "note": "Clinic target (not a consensus value)."},
    "medication_adherence_pct":            {"competence": None, "benchmark": None, "direction": "higher", "kind": "local", "source": "FCMS", "note": "No published target."},
}

LABELS = {
    "oocyte_yield_per_follicle_pct": "Oocyte yield per follicle", "mii_rate_pct": "MII rate at ICSI",
    "sperm_progressive_motility_post_prep_pct": "Sperm progressive motility post-prep", "ivf_polyspermy_rate_pct": "IVF polyspermy rate",
    "one_pn_rate_ivf_pct": "1PN rate (IVF)", "one_pn_rate_icsi_pct": "1PN rate (ICSI)", "good_blastocyst_rate_pct": "Good blastocyst development rate",
    "icsi_damage_rate_pct": "ICSI damage rate", "icsi_normal_fertilisation_rate_pct": "ICSI normal fertilisation rate",
    "ivf_normal_fertilisation_rate_pct": "IVF normal fertilisation rate", "failed_fertilisation_rate_pct": "Failed fertilisation rate (IVF)",
    "cleavage_rate_pct": "Cleavage rate", "day2_development_rate_pct": "Day-2 development rate (4-cell)", "day3_development_rate_pct": "Day-3 development rate (8-cell)",
    "blastocyst_development_rate_pct": "Blastocyst development rate", "successful_biopsy_rate_pct": "Successful biopsy rate",
    "blastocyst_cryosurvival_rate_pct": "Blastocyst cryosurvival rate", "implantation_rate_cleavage_pct": "Implantation rate (cleavage stage)",
    "implantation_rate_blastocyst_pct": "Implantation rate (blastocyst)",
    "cycles_started": "Cycles started", "cancellation_before_opu_rate_pct": "Cycle cancellation before OPU", "ohss_moderate_severe_rate_pct": "Moderate/severe OHSS",
    "opu_complication_rate_pct": "Complications after OPU", "hcg_positive_rate_per_et_pct": "hCG positive per ET", "clinical_pregnancy_rate_per_et_pct": "Clinical pregnancy rate per ET",
    "multiple_pregnancy_rate_pct": "Multiple pregnancy rate", "miscarriage_rate_pct": "Miscarriage rate", "ectopic_rate_pct": "Ectopic pregnancy rate",
    "ongoing_pregnancy_rate_per_et_pct": "Ongoing pregnancy per ET", "live_birth_rate_per_et_pct": "Live birth per ET", "live_birth_rate_per_started_cycle_pct": "Live birth per started cycle",
    "steps_electronically_witnessed_pct": "Steps electronically witnessed", "manual_witness_count": "Manual double-witness (count)", "witness_mismatches": "Witness mismatches (count)",
    "consents_signed_in_app": "Consents signed in app (count)", "medication_adherence_pct": "Medication adherence (ticked doses)",
}


def _one(db: Session, sql: str, **p):
    r = db.execute(text(sql), p).first()
    return dict(r._mapping) if r else {}


def _pct(n, d):
    if not d:
        return None
    return round(100.0 * float(n) / float(d), 1)


def status_of(key: str, value) -> str | None:
    """below_competence | competent | benchmark | none (no target) — respects direction."""
    b = BENCHMARKS.get(key)
    if value is None or not b or b.get("competence") is None:
        return None
    comp, bench, higher = b["competence"], b.get("benchmark"), b["direction"] == "higher"
    if higher:
        if bench is not None and value >= bench:
            return "benchmark"
        return "competent" if value >= comp else "below_competence"
    if bench is not None and value <= bench:
        return "benchmark"
    return "competent" if value <= comp else "below_competence"


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
               count(*) FILTER (WHERE f.status='ABNORMAL_1PN' AND o.insemination_method='IVF') AS pn1_ivf,
               count(*) FILTER (WHERE f.status='ABNORMAL_1PN' AND o.insemination_method='ICSI') AS pn1_icsi,
               count(*) FILTER (WHERE f.status='NORMAL_2PN') AS all_2pn,
               count(DISTINCT r.cycle_id) FILTER (WHERE o.insemination_method='IVF') AS ivf_cycles,
               count(DISTINCT r.cycle_id) FILTER (WHERE o.insemination_method='IVF' AND f.status='NORMAL_2PN') AS ivf_cycles_fertilised
        FROM oocytes o JOIN oocyte_retrievals r ON r.id=o.retrieval_id
        LEFT JOIN fertilization_records f ON f.oocyte_id=o.id
        WHERE r.procedure_date BETWEEN :start AND :end AND o.is_inseminated
    """, **P)

    dev = _one(db, """
        WITH e AS (
          -- embryo cohort anchored on the OPU date, the same anchor as the fertilisation denominators
          SELECT e.id FROM embryos e
          LEFT JOIN fertilization_records f ON f.id = e.fertilization_record_id
          LEFT JOIN oocytes o ON o.id = f.oocyte_id
          LEFT JOIN oocyte_retrievals r ON r.id = o.retrieval_id
          LEFT JOIN treatment_cycles c ON c.id = e.cycle_id
          WHERE coalesce(r.procedure_date, c.d0_date, c.start_date) BETWEEN :start AND :end
        )
        SELECT (SELECT count(*) FROM e) AS embryos,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=2) AS d2_assessed,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=2 AND a.cell_count>=2) AS d2_cleaved,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=2 AND a.cell_count=4) AS d2_4cell,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=3 AND a.cell_count=8) AS d3_8cell,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=3) AS d3_assessed,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=5 AND a.expansion IS NOT NULL) AS blastocysts_d5,
               (SELECT count(DISTINCT a.embryo_id) FROM embryo_assessments a JOIN e ON e.id=a.embryo_id WHERE a.assessment_day=5 AND a.expansion IN ('FULL','EXPANDED','HATCHING','HATCHED') AND a.icm_grade IN ('A','B') AND a.te_grade IN ('A','B')) AS good_blastocysts_d5,
               (SELECT count(*) FROM embryos x JOIN e ON e.id=x.id WHERE x.is_pgta_tested) AS biopsied,
               (SELECT count(*) FROM embryos x JOIN e ON e.id=x.id WHERE x.is_pgta_tested AND x.pgta_result IS NOT NULL AND x.pgta_result NOT IN ('no result','no_result','')) AS biopsy_with_result,
               (SELECT count(*) FROM embryo_cryopreservations cp JOIN e ON e.id=cp.embryo_id) AS frozen
    """, **P)

    sperm = _one(db, """
        SELECT count(*) AS preps, avg(post_progressive_pct) AS mean_post_progressive
        FROM sperm_preparations WHERE prepared_at::date BETWEEN :start AND :end AND post_progressive_pct IS NOT NULL
    """, **P)

    warm = _one(db, """
        SELECT count(*) AS warmed, count(*) FILTER (WHERE status='SURVIVED') AS survived
        FROM embryo_warmings WHERE warming_date BETWEEN :start AND :end
    """, **P)

    et = _one(db, """
        WITH tr AS (
          SELECT t.cycle_id, t.embryo_id,
                 EXISTS (SELECT 1 FROM embryo_assessments a WHERE a.embryo_id=t.embryo_id AND a.assessment_day>=5 AND a.expansion IS NOT NULL) AS is_blast
          FROM embryo_transfers t WHERE t.transfer_date BETWEEN :start AND :end
        ), per_cycle AS (
          SELECT cycle_id, count(*) AS n, bool_or(is_blast) AS blast_cycle FROM tr GROUP BY cycle_id
        )
        SELECT count(*) AS et_cycles, coalesce(sum(n),0) AS embryos_transferred,
               coalesce(sum(n) FILTER (WHERE blast_cycle),0) AS blasts_transferred,
               coalesce(sum(n) FILTER (WHERE NOT blast_cycle),0) AS cleavage_transferred,
               coalesce(sum(o.gestational_sacs) FILTER (WHERE blast_cycle),0) AS sacs_blast,
               coalesce(sum(o.gestational_sacs) FILTER (WHERE NOT blast_cycle),0) AS sacs_cleavage,
               count(*) FILTER (WHERE o.hcg_positive) AS hcg_positive,
               count(*) FILTER (WHERE o.clinical_pregnancy) AS clinical_pregnancies,
               count(*) FILTER (WHERE o.gestational_sacs >= 2) AS multiple,
               count(*) FILTER (WHERE o.miscarriage) AS miscarriages,
               count(*) FILTER (WHERE o.ectopic) AS ectopic,
               count(*) FILTER (WHERE o.ongoing_pregnancy) AS ongoing,
               count(*) FILTER (WHERE o.live_birth) AS live_births
        FROM per_cycle p LEFT JOIN cycle_outcomes o ON o.cycle_id=p.cycle_id
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
        "sperm_progressive_motility_post_prep_pct": round(float(sperm["mean_post_progressive"]), 1) if sperm.get("mean_post_progressive") is not None else None,
        "icsi_normal_fertilisation_rate_pct": _pct(fert.get("icsi_2pn"), fert.get("icsi_inseminated")),
        "icsi_damage_rate_pct": _pct(fert.get("icsi_degenerated"), fert.get("icsi_inseminated")),
        "ivf_normal_fertilisation_rate_pct": _pct(fert.get("ivf_2pn"), fert.get("ivf_inseminated")),
        "ivf_polyspermy_rate_pct": _pct(fert.get("ivf_3pn"), fert.get("ivf_inseminated")),
        "one_pn_rate_ivf_pct": _pct(fert.get("pn1_ivf"), fert.get("ivf_inseminated")),
        "one_pn_rate_icsi_pct": _pct(fert.get("pn1_icsi"), fert.get("icsi_inseminated")),
        "failed_fertilisation_rate_pct": _pct((fert.get("ivf_cycles") or 0) - (fert.get("ivf_cycles_fertilised") or 0), fert.get("ivf_cycles")),
        "cleavage_rate_pct": _pct(dev.get("d2_cleaved"), fert.get("all_2pn")) if dev.get("d2_assessed") else None,
        "day2_development_rate_pct": _pct(dev.get("d2_4cell"), fert.get("all_2pn")) if dev.get("d2_assessed") else None,
        "day3_development_rate_pct": _pct(dev.get("d3_8cell"), fert.get("all_2pn")) if dev.get("d3_assessed") else None,
        "blastocyst_development_rate_pct": _pct(dev.get("blastocysts_d5"), fert.get("all_2pn")),
        "good_blastocyst_rate_pct": _pct(dev.get("good_blastocysts_d5"), fert.get("all_2pn")),
        "successful_biopsy_rate_pct": _pct(dev.get("biopsy_with_result"), dev.get("biopsied")),
        "blastocyst_cryosurvival_rate_pct": _pct(warm.get("survived"), warm.get("warmed")),
        "implantation_rate_cleavage_pct": _pct(et.get("sacs_cleavage"), et.get("cleavage_transferred")),
        "implantation_rate_blastocyst_pct": _pct(et.get("sacs_blast"), et.get("blasts_transferred")),
        "counts": {**opu, **fert, **dev, **warm, "sperm_preps": sperm.get("preps")},
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
    status = {k: status_of(k, v) for sect in (lab, clinical, operational) for k, v in sect.items() if k != "counts"}
    return {"period": {"start": str(start), "end": str(end)}, "laboratory": lab, "clinical": clinical,
            "operational": operational, "benchmarks": BENCHMARKS, "labels": LABELS, "status": status,
            "references": [VIENNA, MARIBOR]}


def monthly_series(db: Session, months: int = 12) -> list[dict]:
    """One row per month with every indicator (flat) — feeds the Insight charts."""
    out = []
    t = today()
    m_start, m_end = t.replace(day=1), t          # current month to date is the last point
    for i in range(months):
        if i:
            m_end = m_start - timedelta(days=1)
            m_start = m_end.replace(day=1)
        k = compute(db, m_start, m_end)
        flat = {"month": m_start.strftime("%Y-%m")}
        for sect in ("laboratory", "clinical", "operational"):
            for key, val in k[sect].items():
                if key != "counts":
                    flat[key] = val
        flat["opus"] = k["laboratory"]["counts"].get("opus")
        flat["et_cycles"] = k["clinical"]["counts"].get("et_cycles")
        out.append(flat)
    return list(reversed(out))
