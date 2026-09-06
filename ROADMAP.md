# FCMS Roadmap — Seamless Patient Care (v2)

Life by Dr. Pat · updated 2026-09-06

Goal: one patient record flows uninterrupted from first contact → registration → EMR →
treatment plan → cycle plan → self-administered injections (patient app) → ultrasound /
blood test / embryology → stock → billing → follow-up → marketing insight.
Every new capability reuses an existing module; nothing is rebuilt.

## 0. Reference: what exists (reuse targets)

| Module | Reusable for v2 |
|---|---|
| 1 EMR | patient identity, visits, SOAP, ICD-10, RBAC, audit, PDPA |
| 2 Lab | order → result pipeline, embryo/oocyte/sperm entities, cryo inventory |
| 3 Ultrasound | DICOM studies, follicle measurements (feeds cycle monitoring) |
| 4 Pharmacy | drug catalog, FIFO lots, dispensing, prescription generator |
| 5 Medical Supply | per-procedure consumption logging |
| 6 CRM | appointments, provider slots, virtual consultation, SMS/LINE/Email/WhatsApp |
| 7 Accounting | service catalog, invoices, receipts, expenses, P&L |

## 1. Lessons taken from MCS Cloud (concept-only)

Adopt: LINE OA as the primary patient channel · deposit / outstanding-balance POS · queue
board with TV display · insurer e-Claim · PEAK API export · external-lab HL7 order/result ·
doctor-fee (DF) and staff commission rules · multi-branch readiness.

Reject: aesthetics-first data model, marketplace, AI chatbot, course/package-selling UX,
no notion of a treatment cycle.

## 2. New / extended modules

### M1-ext  Treatment Plan + Cycle Plan (core of the vision)
- **Done (v1):** the existing Timeline Generator is embedded as Module 10 at `/timeline`,
  DB-backed and linked to EMR patients by HN. Its protocol/visit logic is the seed for the
  `cycles` / `cycle_days` model below — reuse, don't rewrite.
- `treatment_plans`: diagnosis → protocol → phases (OI / IUI / IVF-ICSI / FET / PRP / ERA)
- `cycles`: LMP or D1 anchor, protocol template (antagonist, agonist, natural, mild,
  PPOS, HRT-FET, natural-FET), daily schedule generated from template
- `cycle_days`: date, planned meds (dose, route, time), planned monitoring
  (TVUS / E2 / LH / P4), planned procedure (trigger, OPU, IUI, ET, hysteroscopy, PRP)
- Auto-links: TVUS follicle data (M3) and hormone results (M2) land on the correct
  cycle day; pharmacy dispensing (M4) reconciles against planned doses; OR bookings
  (M12) and appointments (M6) are created from the schedule.
- Physician view: cycle timeline with follicle chart, E2 curve, trigger decision panel.

### M10  Reproductive Calculators + Questionnaires
- Ovulation, EDD, gestational age (from ET date / LMP / CRL), AMH-based response
  predictor, BMI, semen-analysis WHO-2021 flags, embryo-score to live-birth estimate.
- Self-assessment questionnaire builder (risk factors, FertiQoL, PHQ-2/GAD-2, family
  history) with scored outcome → pre-consult summary in EMR.
- Timeline planner UI = read-only front to M1-ext cycles.

### M12  Operating Room
- Rooms, sessions, procedure types (IUI, ovarian PRP, endometrial PRP, office
  hysteroscopy; extensible), pre-op checklist, WHO surgical safety checklist, anaesthesia
  record, implant/consumable capture (auto M5 usage log), op note template → EMR,
  post-op instructions to patient app.

### M13  Patient App (LINE Mini App + PWA; native later)
- Registration + PDPA consent, ID-card OCR, insurance card.
- Home = today's cycle day: injection card (drug, dose, site rotation, video), tap to
  confirm "injected" (timestamp, batch lot), missed-dose alert to nurse queue.
- Symptom diary (OHSS red flags), medication supply countdown → pharmacy pre-pack.
- Upcoming visits, queue position, lab results (physician-released), TVUS images,
  embryo report + photos, cryo inventory statement, invoices/deposits, online payment
  (PromptPay / card), virtual consultation join, secure messaging with human staff.
- Education feed (from M8 content library, brand-voice compliant).

### M14  Billing extension (on top of M7)
- Package/quotation (IVF package with inclusions), deposit, instalments, outstanding
  balance, cycle-linked charge capture (every M2/M3/M4/M5/M12 event posts a charge),
  DF and commission rules, insurer e-Claim, PEAK / Xero export, TV queue + POS screen.

### M8  Marketing Center (Social + Ads + SEO + Content)
- Content library: bilingual posts, videos, carousels; brand-voice checker (Section 5).
- Planning calendar → schedule to Facebook, Instagram, LINE OA, TikTok, YouTube.
- Ads console: Google Ads, Meta Ads, LINE Ads campaign creation, budget, UTM, spend →
  cost-per-lead → cost-per-cycle (joins M6 lead source with M7 revenue).
- SEO: keyword tracking, page audit for clinic site, GBP posts/reviews.
- Attribution: lead → booking → first visit → cycle start → outcome, by channel.

### M9  Webmaster (optional) — CMS pages, blog from M8 library, booking widget from M6.

### M11  Medical Certificate — templates (sick leave, fit-to-fly, treatment letter for
employer, embassy letter), Thai/EN, signed PDF, QR verify.

### M15  Insight & Recommendation (no chatbot)
- Rule + model engine: protocol suggestion from age/AMH/AFC/BMI/prior response,
  trigger-day suggestion from follicle cohort + E2, embryo transfer priority ranking,
  stock reorder forecast from upcoming cycles, no-show risk, churn/follow-up nudges.
- Every recommendation is advisory, shown with the inputs used, and logged (PDPA).
- Content generation for M8: draft post/ad copy from an approved topic, checked against
  BRAND_VOICE.md, always human-approved before publish.

## 3. Cross-cutting
- Event bus (Postgres LISTEN/NOTIFY → later Redis) so modules react without coupling
  (e.g. `lab.result.final` → cycle day update → patient-app push → billing charge).
- Notification service extracted from M6 for reuse by M13/M14/M12.
- HL7 v2 (external lab, GE Voluson worklist) + FHIR R4 read API for future partners.
- Multi-branch flag on all clinical tables from day one.

## 4. Build order (each = models → schemas → routes → frontend → migration → push)
1. M1-ext Treatment/Cycle Plan   (unlocks everything else)
2. M12 Operating Room
3. M13 Patient App (LINE Mini App first)
4. M14 Billing extension
5. M10 Calculators + Questionnaires
6. M11 Medical Certificate
7. M8 Marketing Center
8. M15 Insight & Recommendation
9. M9 Webmaster

## 5. Standing decisions (unchanged)
No AI chatbot · "virtual consultation" not "telemedicine" · bilingual EN/TH everywhere ·
PDPA audit on all access · labels 80×50 / 40×20 mm · Buddhist calendar · design tokens only.
