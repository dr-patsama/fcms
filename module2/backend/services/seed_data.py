"""
FCMS Module 2 - Lab Test Panel Seed Data
Common fertility, endocrine, and screening tests
Includes Thai names and WHO reference ranges
"""

FERTILITY_TEST_PANELS = [
    # Hormone Profile
    {"code": "FSH",   "name_en": "Follicle-Stimulating Hormone", "name_th": "ฮอร์โมนกระตุ้นรังไข่ (FSH)", "unit": "mIU/mL", "f_min": 3.5, "f_max": 12.5, "m_min": 1.5, "m_max": 12.4, "tat": 4},
    {"code": "LH",    "name_en": "Luteinizing Hormone",         "name_th": "ฮอร์โมนลูทีไนซิง (LH)",     "unit": "mIU/mL", "f_min": 2.4, "f_max": 12.6, "m_min": 1.7, "m_max": 8.6, "tat": 4},
    {"code": "E2",    "name_en": "Estradiol",                    "name_th": "เอสตราไดออล (E2)",            "unit": "pg/mL",  "f_min": 12.4, "f_max": 233, "m_min": None, "m_max": None, "tat": 4},
    {"code": "PRG",   "name_en": "Progesterone",                 "name_th": "โปรเจสเตอโรน",               "unit": "ng/mL",  "f_min": 0.2, "f_max": 1.5, "m_min": None, "m_max": None, "tat": 4},
    {"code": "AMH",   "name_en": "Anti-Müllerian Hormone",       "name_th": "แอนตี้มูลเลอเรียนฮอร์โมน (AMH)", "unit": "ng/mL", "f_min": 1.0, "f_max": 3.5, "m_min": None, "m_max": None, "tat": 24},
    {"code": "PRL",   "name_en": "Prolactin",                    "name_th": "โปรแลคติน",                  "unit": "ng/mL",  "f_min": 4.8, "f_max": 23.3, "m_min": 4.0, "m_max": 15.2, "tat": 4},
    {"code": "TESTO", "name_en": "Testosterone",                 "name_th": "เทสโทสเทอโรน",               "unit": "ng/dL",  "f_min": 15, "f_max": 70, "m_min": 264, "m_max": 916, "tat": 4},
    {"code": "DHEAS", "name_en": "DHEA-Sulfate",                 "name_th": "ดีเอชอีเอ-ซัลเฟต",           "unit": "µg/dL",  "f_min": 35, "f_max": 430, "m_min": 80, "m_max": 560, "tat": 24},
    {"code": "BHCG",  "name_en": "Beta-hCG",                     "name_th": "เบต้า-เอชซีจี",              "unit": "mIU/mL", "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 2},
    
    # Thyroid
    {"code": "TSH",   "name_en": "Thyroid-Stimulating Hormone",  "name_th": "ฮอร์โมนกระตุ้นไทรอยด์ (TSH)", "unit": "mIU/L",  "f_min": 0.27, "f_max": 4.2, "m_min": 0.27, "m_max": 4.2, "tat": 4},
    {"code": "FT4",   "name_en": "Free Thyroxine",               "name_th": "ฟรีไทรอกซิน (FT4)",          "unit": "ng/dL",  "f_min": 0.93, "f_max": 1.7, "m_min": 0.93, "m_max": 1.7, "tat": 4},
    {"code": "FT3",   "name_en": "Free Triiodothyronine",        "name_th": "ฟรีไตรไอโอโดไทรโอนีน (FT3)", "unit": "pg/mL",  "f_min": 2.0, "f_max": 4.4, "m_min": 2.0, "m_max": 4.4, "tat": 4},
    
    # Hematology
    {"code": "CBC",   "name_en": "Complete Blood Count",          "name_th": "ความสมบูรณ์ของเม็ดเลือด (CBC)", "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 2},
    {"code": "BG",    "name_en": "Blood Group & Rh",              "name_th": "หมู่เลือดและอาร์เอช",        "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 2},
    
    # Screening
    {"code": "HBSAG",    "name_en": "Hepatitis B Surface Antigen",  "name_th": "แอนติเจนไวรัสตับอักเสบบี", "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 4},
    {"code": "ANTIHCV",  "name_en": "Anti-HCV",                     "name_th": "แอนติบอดีไวรัสตับอักเสบซี", "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 4},
    {"code": "HIV",      "name_en": "HIV Antibody",                  "name_th": "แอนติบอดีเอชไอวี",        "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 4},
    {"code": "VDRL",     "name_en": "Syphilis Screen (VDRL)",        "name_th": "ตรวจซิฟิลิส",            "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 4},
    {"code": "RUBELLA",  "name_en": "Rubella IgG",                   "name_th": "แอนติบอดีหัดเยอรมัน",     "unit": "IU/mL", "f_min": 10, "f_max": None, "m_min": None, "m_max": None, "tat": 24},

    # Urine
    {"code": "UA",       "name_en": "Urinalysis",                    "name_th": "ตรวจปัสสาวะ",             "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 2},
    
    # Coagulation
    {"code": "PT",       "name_en": "Prothrombin Time",               "name_th": "เวลาโปรทรอมบิน",         "unit": "sec", "f_min": 11, "f_max": 13.5, "m_min": 11, "m_max": 13.5, "tat": 4},
    {"code": "APTT",     "name_en": "Activated Partial Thromboplastin Time", "name_th": "เวลาเอพีทีที", "unit": "sec", "f_min": 25, "f_max": 35, "m_min": 25, "m_max": 35, "tat": 4},
    
    # Metabolic
    {"code": "FBS",      "name_en": "Fasting Blood Sugar",            "name_th": "น้ำตาลในเลือด (อดอาหาร)", "unit": "mg/dL", "f_min": 70, "f_max": 100, "m_min": 70, "m_max": 100, "tat": 2},
    {"code": "HBA1C",    "name_en": "Hemoglobin A1c",                 "name_th": "ฮีโมโกลบินเอวันซี",       "unit": "%", "f_min": None, "f_max": 5.7, "m_min": None, "m_max": 5.7, "tat": 24},
    
    # Andrology
    {"code": "SA",       "name_en": "Semen Analysis (WHO 2021)",      "name_th": "วิเคราะห์น้ำอสุจิ",       "unit": None, "f_min": None, "f_max": None, "m_min": None, "m_max": None, "tat": 4},
    {"code": "DFI",      "name_en": "Sperm DNA Fragmentation Index",  "name_th": "ดัชนีดีเอ็นเอสเปิร์มแตกหัก", "unit": "%", "f_min": None, "f_max": None, "m_min": None, "m_max": 25, "tat": 48},
]

# WHO 2021 Semen Analysis Reference Values (5th percentile lower limits)
WHO_2021_SEMEN_REFERENCE = {
    "volume_ml": 1.4,
    "concentration_M_per_ml": 16,
    "total_count_M": 39,
    "total_motility_pct": 42,
    "progressive_motility_pct": 30,
    "normal_morphology_pct": 4,
    "vitality_pct": 54,
    "ph_min": 7.2,
}

# Embryo grading reference
BLASTOCYST_GRADES = {
    "expansion": {
        "1": "Early blastocyst — cavity < half embryo volume",
        "2": "Blastocyst — cavity ≥ half embryo volume",
        "3": "Full blastocyst — cavity fills embryo",
        "4": "Expanded — cavity larger than early embryo, thinning zona",
        "5": "Hatching — herniating out of zona",
        "6": "Hatched — completely out of zona",
    },
    "icm": {
        "A": "Tightly packed, many cells",
        "B": "Loosely grouped, several cells",
        "C": "Very few cells",
    },
    "te": {
        "A": "Many cells forming cohesive layer",
        "B": "Few cells forming loose epithelium",
        "C": "Very few large cells",
    }
}
