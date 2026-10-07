"""
Treatment packages — default templates and seeding.

A package is the one template that drives all four lanes (Binflux "Package", e.g. IVF-D5ET):
  medication_template → stimulation chart + pharmacy + patient daily reminders
  lab_events          → lab to-do list, witness points, EMR write-back
  consents            → consent gating of lab tasks
  notifications       → patient push text (overrides of the defaults in notifications.py)
  billing_items       → Module 7 invoice lines (amounts are set by the clinic; 0 = not priced yet)

Everything here is an editable default. Doses and drug names in the medication templates
are starting points for the physician to adjust per patient — they are not prescriptions.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.journey_models import TreatmentPackage, ConsentTemplate

# ── Lab event vocabulary ─────────────────────────────────────────────────────
# key → (title_en, title_th, default items, default write-back)
# items vocabulary: wristband | opu_tube | oocyte_dish | culture_dish | sperm_tube | prep_tube |
#                   cryo_device | warming_dish | biopsy_tube | et_dish | iui_catheter
LAB_EVENT_TYPES = {
    "opu":              ("Oocyte retrieval (OPU)",        "เก็บไข่ (OPU)",                 ["wristband", "opu_tube"],          "opu.start_time"),
    "sperm_collection": ("Sperm collection",              "เก็บน้ำเชื้อ",                   ["wristband", "sperm_tube"],        "semen.collected_at"),
    "sperm_prep":       ("Sperm preparation",             "เตรียมน้ำเชื้อ",                  ["sperm_tube", "prep_tube"],        "sperm_prep.prepared_at"),
    "denudation":       ("Denudation",                    "ลอกเซลล์คิวมูลัส",                ["oocyte_dish"],                     None),
    "insemination":     ("Insemination (IVF)",            "ผสมเชื้อ (IVF)",                 ["oocyte_dish", "prep_tube"],       "oocyte.insemination_time"),
    "icsi":             ("ICSI",                          "ICSI",                           ["oocyte_dish", "prep_tube"],       "oocyte.insemination_time"),
    "fert_check":       ("Fertilisation check",           "ตรวจการปฏิสนธิ",                 ["culture_dish"],                    "fertilization.check_time"),
    "cleavage_check":   ("Cleavage check",                "ตรวจการแบ่งตัว",                  ["culture_dish"],                    "assessment.time"),
    "blast_check":      ("Blastocyst check",              "ตรวจบลาสโตซิสต์",                 ["culture_dish"],                    "assessment.time"),
    "biopsy":           ("Trophectoderm biopsy (PGT)",    "ตัดชิ้นเนื้อตัวอ่อน (PGT)",        ["culture_dish", "biopsy_tube"],    "biopsy.time"),
    "vitrification":    ("Vitrification",                 "แช่แข็ง (vitrification)",         ["culture_dish", "cryo_device"],    "cryo.freeze_date"),
    "oocyte_vitrification": ("Oocyte vitrification",     "แช่แข็งไข่",                      ["oocyte_dish", "cryo_device"],     "cryo.freeze_date"),
    "sperm_freeze":     ("Sperm cryopreservation",        "แช่แข็งน้ำเชื้อ",                 ["prep_tube", "cryo_device"],       "sperm_cryo.freeze_date"),
    "warming":          ("Embryo warming",                "ละลายตัวอ่อน",                    ["cryo_device", "warming_dish"],    "warming.warming_date"),
    "et":               ("Embryo transfer",               "ย้ายตัวอ่อน",                     ["wristband", "et_dish"],           "transfer.transfer_date"),
    "iui":              ("Intrauterine insemination",     "ฉีดเชื้อเข้าโพรงมดลูก (IUI)",     ["wristband", "prep_tube"],         "iui.time"),
    "semen_analysis":   ("Semen analysis",                "ตรวจวิเคราะห์น้ำเชื้อ",            ["sperm_tube"],                      "semen.analyzed_at"),
    "procedure":        ("Procedure",                     "หัตถการ",                         ["wristband"],                       "procedure.time"),
}


def ev(key, day, time, *, title_en=None, title_th=None, items=None, witness=True, consents=None,
       write_back="default", lane="lab", optional=False):
    t_en, t_th, d_items, d_wb = LAB_EVENT_TYPES[key]
    return {
        "key": key, "type": key, "day": day, "time": time,
        "title_en": title_en or t_en, "title_th": title_th or t_th,
        "items": items if items is not None else d_items,
        "requires_witness": witness,
        "consents": consents or [],
        "write_back": d_wb if write_back == "default" else write_back,
        "lane": lane, "optional": optional,
    }


# ── Medication templates (editable defaults, day_index 1 = first medication day) ─────────
MED_ANTAGONIST = [
    {"drug_en": "Recombinant FSH", "drug_th": "ฮอร์โมน FSH (rFSH)", "dose": 225, "unit": "IU", "route": "SC", "slot": "PM", "start": 1, "end": 10, "drug_code": "RFSH"},
    {"drug_en": "GnRH antagonist", "drug_th": "ยากดการตกไข่ (GnRH antagonist)", "dose": 0.25, "unit": "mg", "route": "SC", "slot": "AM", "start": 5, "end": 10, "drug_code": "GNRH_ANT"},
    {"drug_en": "Trigger injection", "drug_th": "ยากระตุ้นไข่สุก (trigger)", "dose": 1, "unit": "dose", "route": "SC", "slot": "21:00", "start": 11, "end": 11, "drug_code": "TRIGGER"},
]
MED_FET_HRT = [
    {"drug_en": "Estradiol valerate", "drug_th": "เอสโตรเจน (estradiol valerate)", "dose": 6, "unit": "mg", "route": "PO", "slot": "AM", "start": 1, "end": 28, "drug_code": "E2V"},
    {"drug_en": "Progesterone (vaginal)", "drug_th": "โปรเจสเตอโรนทางช่องคลอด", "dose": 400, "unit": "mg", "route": "PV", "slot": "AM", "start": 15, "end": 28, "drug_code": "P4_PV"},
    {"drug_en": "Progesterone (vaginal)", "drug_th": "โปรเจสเตอโรนทางช่องคลอด", "dose": 400, "unit": "mg", "route": "PV", "slot": "PM", "start": 15, "end": 28, "drug_code": "P4_PV"},
]
MED_LUTEAL = [
    {"drug_en": "Progesterone (vaginal)", "drug_th": "โปรเจสเตอโรนทางช่องคลอด", "dose": 400, "unit": "mg", "route": "PV", "slot": "AM", "start": 1, "end": 14, "drug_code": "P4_PV"},
    {"drug_en": "Progesterone (vaginal)", "drug_th": "โปรเจสเตอโรนทางช่องคลอด", "dose": 400, "unit": "mg", "route": "PV", "slot": "PM", "start": 1, "end": 14, "drug_code": "P4_PV"},
]
MED_IUI = [
    {"drug_en": "Letrozole", "drug_th": "เลโทรโซล", "dose": 5, "unit": "mg", "route": "PO", "slot": "PM", "start": 1, "end": 5, "drug_code": "LETRO"},
    {"drug_en": "Trigger injection", "drug_th": "ยากระตุ้นไข่สุก (trigger)", "dose": 1, "unit": "dose", "route": "SC", "slot": "21:00", "start": 11, "end": 11, "drug_code": "TRIGGER"},
]

# ── Lab event sets ───────────────────────────────────────────────────────────
D0_IVF = [
    ev("opu", 0, "08:00", consents=["ivf_treatment", "anaesthesia", "lab_procedures"]),
    ev("sperm_collection", 0, "08:30", consents=["ivf_treatment"]),
    ev("sperm_prep", 0, "09:30"),
    ev("denudation", 0, "11:00", witness=False),
    ev("icsi", 0, "12:00", consents=["lab_procedures"]),
]
CULTURE = [
    ev("fert_check", 1, "08:00", witness=False),
    ev("cleavage_check", 3, "08:00", witness=False),
    ev("blast_check", 5, "08:00", witness=False),
    ev("blast_check", 6, "08:00", witness=False, optional=True),
]

PKG_IVF_FRESH_D5 = {
    "code": "IVF_ICSI_FRESH_D5", "name_en": "IVF/ICSI — fresh Day-5 transfer", "name_th": "IVF/ICSI — ย้ายตัวอ่อนสด วันที่ 5",
    "cycle_type": "ivf_icsi_fresh", "anchor": "opu", "default_et_day": 5,
    "medication_template": MED_ANTAGONIST,
    "lab_events": D0_IVF + CULTURE + [
        ev("et", 5, "10:00", consents=["embryo_transfer"]),
        ev("vitrification", 5, "13:00", consents=["cryo_storage"], optional=True),
        ev("vitrification", 6, "13:00", consents=["cryo_storage"], optional=True),
    ],
    "consents": ["pdpa", "ivf_treatment", "anaesthesia", "lab_procedures", "embryo_transfer", "cryo_storage"],
    "billing_items": [
        {"code": "IVF_PKG", "description_en": "IVF/ICSI package (fresh transfer)", "description_th": "แพ็กเกจ IVF/ICSI (ย้ายสด)", "amount": 0, "when": "on_create"},
        {"code": "CRYO_YEAR", "description_en": "Embryo storage — 12 months", "description_th": "ฝากแช่แข็งตัวอ่อน 12 เดือน", "amount": 0, "when": "storage_year"},
    ],
    "sort_order": 10,
}

PKG_IVF_FREEZE_ALL = {
    "code": "IVF_ICSI_FREEZE_ALL", "name_en": "IVF/ICSI — freeze-all", "name_th": "IVF/ICSI — แช่แข็งทั้งหมด",
    "cycle_type": "ivf_icsi_freeze_all", "anchor": "opu", "default_et_day": None, "freeze_all": True,
    "medication_template": MED_ANTAGONIST,
    "lab_events": D0_IVF + CULTURE + [
        ev("vitrification", 5, "13:00", consents=["cryo_storage"]),
        ev("vitrification", 6, "13:00", consents=["cryo_storage"], optional=True),
        ev("vitrification", 7, "13:00", consents=["cryo_storage"], optional=True),
    ],
    "consents": ["pdpa", "ivf_treatment", "anaesthesia", "lab_procedures", "cryo_storage"],
    "billing_items": [
        {"code": "IVF_PKG_FA", "description_en": "IVF/ICSI package (freeze-all)", "description_th": "แพ็กเกจ IVF/ICSI (แช่แข็งทั้งหมด)", "amount": 0, "when": "on_create"},
        {"code": "CRYO_YEAR", "description_en": "Embryo storage — 12 months", "description_th": "ฝากแช่แข็งตัวอ่อน 12 เดือน", "amount": 0, "when": "storage_year"},
    ],
    "sort_order": 20,
}

PKG_IVF_PGT = {
    **PKG_IVF_FREEZE_ALL,
    "code": "IVF_ICSI_PGT_A", "name_en": "IVF/ICSI — freeze-all with PGT-A", "name_th": "IVF/ICSI — แช่แข็งทั้งหมด พร้อมตรวจโครโมโซม (PGT-A)",
    "pgt": True,
    "lab_events": D0_IVF + CULTURE + [
        ev("biopsy", 5, "11:00", consents=["pgt"]),
        ev("vitrification", 5, "13:00", consents=["cryo_storage"]),
        ev("biopsy", 6, "11:00", consents=["pgt"], optional=True),
        ev("vitrification", 6, "13:00", consents=["cryo_storage"], optional=True),
        ev("biopsy", 7, "11:00", consents=["pgt"], optional=True),
        ev("vitrification", 7, "13:00", consents=["cryo_storage"], optional=True),
    ],
    "consents": ["pdpa", "ivf_treatment", "anaesthesia", "lab_procedures", "pgt", "cryo_storage"],
    "billing_items": [
        {"code": "IVF_PKG_PGT", "description_en": "IVF/ICSI package with PGT-A", "description_th": "แพ็กเกจ IVF/ICSI พร้อม PGT-A", "amount": 0, "when": "on_create"},
        {"code": "CRYO_YEAR", "description_en": "Embryo storage — 12 months", "description_th": "ฝากแช่แข็งตัวอ่อน 12 เดือน", "amount": 0, "when": "storage_year"},
    ],
    "sort_order": 30,
}

FET_EVENTS = [
    ev("warming", 0, "07:30", consents=["fet_treatment", "cryo_storage"]),
    ev("et", 0, "10:00", consents=["embryo_transfer"]),
]
PKG_FET_HRT = {
    "code": "FET_HRT", "name_en": "Frozen embryo transfer — HRT cycle", "name_th": "ย้ายตัวอ่อนแช่แข็ง — รอบใช้ฮอร์โมน (HRT)",
    "cycle_type": "fet_hrt", "anchor": "et", "default_et_day": 0,
    "medication_template": MED_FET_HRT, "lab_events": FET_EVENTS,
    "consents": ["pdpa", "fet_treatment", "embryo_transfer"],
    "billing_items": [{"code": "FET", "description_en": "Frozen embryo transfer", "description_th": "ย้ายตัวอ่อนแช่แข็ง", "amount": 0, "when": "on_create"}],
    "sort_order": 40,
}
PKG_FET_NATURAL = {**PKG_FET_HRT, "code": "FET_NATURAL", "name_en": "Frozen embryo transfer — natural cycle", "name_th": "ย้ายตัวอ่อนแช่แข็ง — รอบธรรมชาติ",
                   "cycle_type": "fet_natural", "medication_template": MED_LUTEAL, "sort_order": 41}
PKG_FET_STIM = {**PKG_FET_HRT, "code": "FET_STIMULATED", "name_en": "Frozen embryo transfer — stimulated cycle", "name_th": "ย้ายตัวอ่อนแช่แข็ง — รอบกระตุ้นไข่",
                "cycle_type": "fet_stimulated", "medication_template": MED_IUI[:1] + MED_LUTEAL, "sort_order": 42}

PKG_IUI = {
    "code": "IUI", "name_en": "Intrauterine insemination", "name_th": "ฉีดเชื้อเข้าโพรงมดลูก (IUI)",
    "cycle_type": "iui", "anchor": "iui", "default_et_day": None,
    "medication_template": MED_IUI,
    "lab_events": [ev("sperm_collection", 0, "08:00", consents=["iui"]), ev("sperm_prep", 0, "08:30"), ev("iui", 0, "10:30", consents=["iui"])],
    "consents": ["pdpa", "iui"],
    "billing_items": [{"code": "IUI", "description_en": "IUI cycle", "description_th": "รอบ IUI", "amount": 0, "when": "on_create"}],
    "sort_order": 50,
}

PKG_OOCYTE_CRYO = {
    "code": "OOCYTE_CRYO", "name_en": "Oocyte cryopreservation (egg freezing)", "name_th": "แช่แข็งไข่",
    "cycle_type": "oocyte_cryo", "anchor": "opu", "default_et_day": None, "freeze_all": True,
    "medication_template": MED_ANTAGONIST,
    "lab_events": [ev("opu", 0, "08:00", consents=["oocyte_cryo", "anaesthesia"]), ev("denudation", 0, "10:00", witness=False),
                   ev("oocyte_vitrification", 0, "12:00", consents=["cryo_storage"])],
    "consents": ["pdpa", "oocyte_cryo", "anaesthesia", "cryo_storage"],
    "billing_items": [{"code": "OC_PKG", "description_en": "Egg freezing package", "description_th": "แพ็กเกจแช่แข็งไข่", "amount": 0, "when": "on_create"},
                      {"code": "CRYO_YEAR", "description_en": "Oocyte storage — 12 months", "description_th": "ฝากแช่แข็งไข่ 12 เดือน", "amount": 0, "when": "storage_year"}],
    "sort_order": 60,
}

PKG_SPERM_CRYO = {
    "code": "SPERM_CRYO", "name_en": "Sperm cryopreservation", "name_th": "แช่แข็งน้ำเชื้อ",
    "cycle_type": "sperm_cryo", "anchor": "collection", "default_et_day": None, "is_episode": True,
    "medication_template": [],
    "lab_events": [ev("sperm_collection", 0, "09:00", consents=["sperm_cryo"]), ev("semen_analysis", 0, "09:30", witness=False),
                   ev("sperm_freeze", 0, "11:00", consents=["cryo_storage"])],
    "consents": ["pdpa", "sperm_cryo", "cryo_storage"],
    "billing_items": [{"code": "SC", "description_en": "Sperm freezing", "description_th": "แช่แข็งน้ำเชื้อ", "amount": 0, "when": "on_create"},
                      {"code": "CRYO_YEAR", "description_en": "Sperm storage — 12 months", "description_th": "ฝากแช่แข็งน้ำเชื้อ 12 เดือน", "amount": 0, "when": "storage_year"}],
    "sort_order": 70,
}


def episode(code, name_en, name_th, consent, hours="10:00", sort=80):
    return {
        "code": code, "name_en": name_en, "name_th": name_th, "cycle_type": f"episode_{code.lower()}",
        "anchor": "procedure", "is_episode": True, "medication_template": [],
        "lab_events": [ev("procedure", 0, hours, title_en=name_en, title_th=name_th, consents=[consent], witness=True, items=["wristband"])],
        "consents": ["pdpa", consent],
        "billing_items": [{"code": code, "description_en": name_en, "description_th": name_th, "amount": 0, "when": "on_create"}],
        "sort_order": sort,
    }


PKG_EPISODES = [
    episode("OVARIAN_PRP", "Ovarian PRP", "ฉีด PRP รังไข่", "prp", sort=80),
    episode("ENDOMETRIAL_PRP", "Endometrial PRP", "ฉีด PRP เยื่อบุโพรงมดลูก", "prp", sort=81),
    episode("HYSTEROSCOPY", "Office hysteroscopy", "ส่องกล้องโพรงมดลูก", "hysteroscopy", sort=82),
    {
        "code": "SEMEN_ANALYSIS", "name_en": "Semen analysis", "name_th": "ตรวจวิเคราะห์น้ำเชื้อ", "cycle_type": "episode_semen_analysis",
        "anchor": "collection", "is_episode": True, "medication_template": [],
        "lab_events": [ev("sperm_collection", 0, "09:00", witness=True), ev("semen_analysis", 0, "09:30", witness=False)],
        "consents": ["pdpa"],
        "billing_items": [{"code": "SA", "description_en": "Semen analysis", "description_th": "ตรวจวิเคราะห์น้ำเชื้อ", "amount": 0, "when": "on_create"}],
        "sort_order": 83,
    },
]

DEFAULT_PACKAGES = [PKG_IVF_FRESH_D5, PKG_IVF_FREEZE_ALL, PKG_IVF_PGT, PKG_FET_HRT, PKG_FET_NATURAL, PKG_FET_STIM,
                    PKG_IUI, PKG_OOCYTE_CRYO, PKG_SPERM_CRYO] + PKG_EPISODES


# ── Consent templates (titles and short bodies; the clinic finalises the legal wording) ──
CONSENT_TEMPLATES = [
    ("pdpa", "Personal data processing consent (PDPA)", "หนังสือยินยอมให้ประมวลผลข้อมูลส่วนบุคคล (PDPA)", "patient"),
    ("ivf_treatment", "Consent to IVF/ICSI treatment", "หนังสือยินยอมรับการรักษาด้วยเด็กหลอดแก้ว (IVF/ICSI)", "both"),
    ("anaesthesia", "Consent to sedation / anaesthesia", "หนังสือยินยอมรับยาระงับความรู้สึก", "patient"),
    ("lab_procedures", "Consent to laboratory procedures (ICSI, culture, assisted hatching)", "หนังสือยินยอมหัตถการทางห้องปฏิบัติการ", "both"),
    ("embryo_transfer", "Consent to embryo transfer", "หนังสือยินยอมย้ายตัวอ่อน", "both"),
    ("cryo_storage", "Cryopreservation and storage agreement", "หนังสือยินยอมแช่แข็งและฝากเก็บ", "both"),
    ("pgt", "Consent to preimplantation genetic testing (PGT)", "หนังสือยินยอมตรวจพันธุกรรมตัวอ่อน (PGT)", "both"),
    ("fet_treatment", "Consent to frozen embryo transfer cycle", "หนังสือยินยอมรอบย้ายตัวอ่อนแช่แข็ง", "both"),
    ("iui", "Consent to intrauterine insemination", "หนังสือยินยอมฉีดเชื้อเข้าโพรงมดลูก", "both"),
    ("oocyte_cryo", "Consent to oocyte cryopreservation", "หนังสือยินยอมแช่แข็งไข่", "patient"),
    ("sperm_cryo", "Consent to sperm cryopreservation", "หนังสือยินยอมแช่แข็งน้ำเชื้อ", "patient"),
    ("prp", "Consent to PRP procedure", "หนังสือยินยอมหัตถการ PRP", "patient"),
    ("hysteroscopy", "Consent to office hysteroscopy", "หนังสือยินยอมส่องกล้องโพรงมดลูก", "patient"),
    ("disposal", "Consent to disposal of stored material", "หนังสือยินยอมยุติการเก็บรักษา", "both"),
]

CONSENT_BODY_EN = ("I have received an explanation of the nature, purpose, benefits, risks and alternatives of this "
                   "procedure in a language I understand, and my questions have been answered. I consent voluntarily. "
                   "(Clinic to finalise the legal wording of this template.)")
CONSENT_BODY_TH = ("ข้าพเจ้าได้รับคำอธิบายถึงลักษณะ วัตถุประสงค์ ประโยชน์ ความเสี่ยง และทางเลือกของหัตถการนี้ "
                   "ในภาษาที่ข้าพเจ้าเข้าใจ และได้รับคำตอบต่อข้อสงสัยแล้ว ข้าพเจ้ายินยอมโดยสมัครใจ "
                   "(คลินิกจะปรับถ้อยคำทางกฎหมายของแบบฟอร์มนี้ให้สมบูรณ์)")


def seed_defaults(db: Session) -> dict:
    """Idempotent: inserts any missing default package / consent template. Never overwrites edits."""
    added = {"packages": [], "consents": []}
    existing = {p.code for p in db.query(TreatmentPackage.code).all()}
    for p in DEFAULT_PACKAGES:
        if p["code"] in existing:
            continue
        db.add(TreatmentPackage(**{k: v for k, v in p.items()}))
        added["packages"].append(p["code"])
    existing_c = {c.code for c in db.query(ConsentTemplate.code).all()}
    for code, en, th, signer in CONSENT_TEMPLATES:
        if code in existing_c:
            continue
        db.add(ConsentTemplate(code=code, title_en=en, title_th=th, body_en=CONSENT_BODY_EN, body_th=CONSENT_BODY_TH,
                               version="1.0", signer=signer))
        added["consents"].append(code)
    db.commit()
    return added
