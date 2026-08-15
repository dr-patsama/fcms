"""
FCMS — Bilingual Translation Dictionary / พจนานุกรมสองภาษา
Shared across all modules. Keys are English, values include Thai translations.
Usage: from i18n.translations import t
       t("pharmacy.drug_catalogue")  →  "Drug Catalogue / รายการยา"
"""


_TRANSLATIONS = {
    # ── System-wide / ระบบทั่วไป ─────────────────────────
    "app.title":                    ("FCMS", "FCMS"),
    "app.subtitle":                 ("Fertility Clinic Management System", "ระบบจัดการคลินิกเจริญพันธุ์"),
    "app.clinic_name":              ("Life by Dr. Pat", "คลินิก ไลฟ์ บาย ดร.แพท"),

    # Common UI
    "common.save":                  ("Save", "บันทึก"),
    "common.cancel":                ("Cancel", "ยกเลิก"),
    "common.search":                ("Search", "ค้นหา"),
    "common.filter":                ("Filter", "ตัวกรอง"),
    "common.add":                   ("Add", "เพิ่ม"),
    "common.edit":                  ("Edit", "แก้ไข"),
    "common.delete":                ("Delete", "ลบ"),
    "common.print":                 ("Print", "พิมพ์"),
    "common.export":                ("Export", "ส่งออก"),
    "common.back":                  ("Back", "กลับ"),
    "common.confirm":               ("Confirm", "ยืนยัน"),
    "common.close":                 ("Close", "ปิด"),
    "common.loading":               ("Loading...", "กำลังโหลด..."),
    "common.no_data":               ("No data found", "ไม่พบข้อมูล"),
    "common.actions":               ("Actions", "การดำเนินการ"),
    "common.status":                ("Status", "สถานะ"),
    "common.date":                  ("Date", "วันที่"),
    "common.name":                  ("Name", "ชื่อ"),
    "common.notes":                 ("Notes", "หมายเหตุ"),
    "common.total":                 ("Total", "รวม"),
    "common.page":                  ("Page", "หน้า"),
    "common.of":                    ("of", "จาก"),
    "common.yes":                   ("Yes", "ใช่"),
    "common.no":                    ("No", "ไม่"),
    "common.active":                ("Active", "ใช้งาน"),
    "common.inactive":              ("Inactive", "ไม่ใช้งาน"),
    "common.all":                   ("All", "ทั้งหมด"),
    "common.details":               ("Details", "รายละเอียด"),
    "common.created_at":            ("Created At", "สร้างเมื่อ"),
    "common.updated_at":            ("Updated At", "แก้ไขเมื่อ"),

    # ── Navigation / Sidebar ─────────────────────────────
    "nav.emr":                      ("EMR", "เวชระเบียน"),
    "nav.lab":                      ("Lab Management", "ห้องปฏิบัติการ"),
    "nav.lab_general":              ("General Lab", "ห้องแลปทั่วไป"),
    "nav.lab_embryology":           ("Embryology Lab", "ห้องแลปตัวอ่อน"),
    "nav.lab_andrology":            ("Andrology Lab", "ห้องแลปอสุจิ"),
    "nav.ultrasound":               ("Ultrasound", "อัลตราซาวด์"),
    "nav.pharmacy":                 ("Pharmacy", "เภสัชกรรม"),
    "nav.supply":                   ("Medical Supply", "วัสดุทางการแพทย์"),
    "nav.crm":                      ("CRM", "ลูกค้าสัมพันธ์"),
    "nav.accounting":               ("Accounting", "การบัญชี"),
    "nav.social_media":             ("Social Media", "โซเชียลมีเดีย"),
    "nav.webmaster":                ("Webmaster", "เว็บมาสเตอร์"),
    "nav.tools":                    ("Reproductive Tools", "เครื่องมือเจริญพันธุ์"),
    "nav.operating_room":           ("Operating Room", "ห้องผ่าตัด"),
    "nav.user_management":          ("User Management", "จัดการผู้ใช้"),
    "nav.settings":                 ("Settings", "ตั้งค่า"),
    "nav.sign_out":                 ("Sign Out", "ออกจากระบบ"),

    # ── Module 4: Pharmacy / เภสัชกรรม ──────────────────
    "pharmacy.title":               ("Pharmacy", "เภสัชกรรม"),
    "pharmacy.dashboard":           ("Pharmacy Dashboard", "แดชบอร์ดเภสัชกรรม"),
    "pharmacy.drug_catalogue":      ("Drug Catalogue", "รายการยา"),
    "pharmacy.add_drug":            ("Add Drug", "เพิ่มยา"),
    "pharmacy.edit_drug":           ("Edit Drug", "แก้ไขยา"),
    "pharmacy.generic_name":        ("Generic Name", "ชื่อสามัญ"),
    "pharmacy.brand_name":          ("Brand Name", "ชื่อการค้า"),
    "pharmacy.category":            ("Category", "หมวดหมู่"),
    "pharmacy.form":                ("Form", "รูปแบบยา"),
    "pharmacy.strength":            ("Strength", "ความแรง"),
    "pharmacy.unit":                ("Unit", "หน่วย"),
    "pharmacy.manufacturer":        ("Manufacturer", "ผู้ผลิต"),
    "pharmacy.supplier":            ("Supplier", "ผู้จำหน่าย"),
    "pharmacy.unit_cost":           ("Unit Cost", "ราคาทุน"),
    "pharmacy.selling_price":       ("Selling Price", "ราคาขาย"),
    "pharmacy.current_stock":       ("Current Stock", "คงคลัง"),
    "pharmacy.reorder_level":       ("Reorder Level", "จุดสั่งซื้อ"),
    "pharmacy.reorder_qty":         ("Reorder Quantity", "จำนวนสั่งซื้อ"),

    # Stock
    "pharmacy.stock":               ("Stock Management", "จัดการสต็อก"),
    "pharmacy.receive_stock":       ("Receive Stock", "รับสต็อกเข้า"),
    "pharmacy.adjust_stock":        ("Adjust Stock", "ปรับสต็อก"),
    "pharmacy.stock_levels":        ("Stock Levels", "ระดับสต็อก"),
    "pharmacy.lot_number":          ("Lot Number", "เลขล็อต"),
    "pharmacy.expiry_date":         ("Expiry Date", "วันหมดอายุ"),
    "pharmacy.quantity":            ("Quantity", "จำนวน"),
    "pharmacy.low_stock":           ("Low Stock", "สต็อกต่ำ"),
    "pharmacy.out_of_stock":        ("Out of Stock", "หมดสต็อก"),
    "pharmacy.expiring_soon":       ("Expiring Soon", "ใกล้หมดอายุ"),
    "pharmacy.expired":             ("Expired", "หมดอายุแล้ว"),

    # Prescriptions
    "pharmacy.prescriptions":       ("Prescriptions", "ใบสั่งยา"),
    "pharmacy.new_prescription":    ("New Prescription", "สั่งยาใหม่"),
    "pharmacy.pending":             ("Pending", "รอดำเนินการ"),
    "pharmacy.verified":            ("Verified", "ตรวจสอบแล้ว"),
    "pharmacy.dispensed":           ("Dispensed", "จ่ายแล้ว"),
    "pharmacy.cancelled":           ("Cancelled", "ยกเลิก"),
    "pharmacy.verify_rx":           ("Verify Prescription", "ตรวจสอบใบสั่งยา"),
    "pharmacy.dispense":            ("Dispense", "จ่ายยา"),
    "pharmacy.prescriber":          ("Prescriber", "แพทย์ผู้สั่ง"),

    # Dispensing
    "pharmacy.dispensing":          ("Dispensing", "การจ่ายยา"),
    "pharmacy.dosage":              ("Dosage", "ขนาดยา"),
    "pharmacy.frequency":           ("Frequency", "ความถี่"),
    "pharmacy.route":               ("Route", "วิธีใช้ยา"),
    "pharmacy.duration":            ("Duration (days)", "ระยะเวลา (วัน)"),
    "pharmacy.instructions":        ("Instructions", "คำแนะนำ"),
    "pharmacy.warnings":            ("Warnings", "คำเตือน"),

    # Labels
    "pharmacy.labels":              ("Labels", "ฉลากยา"),
    "pharmacy.print_label":         ("Print Label", "พิมพ์ฉลากยา"),
    "pharmacy.batch_labels":        ("Print All Labels", "พิมพ์ฉลากทั้งหมด"),
    "pharmacy.label_preview":       ("Label Preview", "ดูตัวอย่างฉลาก"),

    # Alerts
    "pharmacy.alerts":              ("Alerts", "แจ้งเตือน"),
    "pharmacy.expiry_alert":        ("Expiry Alert", "แจ้งเตือนหมดอายุ"),
    "pharmacy.low_stock_alert":     ("Low Stock Alert", "แจ้งเตือนสต็อกต่ำ"),

    # Reports
    "pharmacy.reports":             ("Reports", "รายงาน"),
    "pharmacy.consumption_report":  ("Consumption Report", "รายงานการใช้ยา"),
    "pharmacy.stock_report":        ("Stock Report", "รายงานสต็อก"),

    # Storage
    "pharmacy.storage_condition":   ("Storage Condition", "สภาพการจัดเก็บ"),
    "pharmacy.refrigeration":       ("Requires Refrigeration", "ต้องเก็บในตู้เย็น"),
    "pharmacy.controlled":          ("Controlled Substance", "วัตถุออกฤทธิ์"),

    # Prescription Writer / เครื่องมือสร้างใบสั่งยา
    "pharmacy.rx_writer":           ("Prescription Writer", "สร้างใบสั่งยา"),
    "pharmacy.rx_fill_from_doc":    ("Fill from a document", "ดึงข้อมูลจากเอกสาร"),
    "pharmacy.rx_extracting":       ("Reading the document...", "กำลังอ่านเอกสาร..."),
    "pharmacy.rx_pack_size":        ("Pack size", "จำนวนต่อกล่อง"),
    "pharmacy.rx_per_dose":         ("Per dose", "ครั้งละ"),
    "pharmacy.rx_times_per_day":    ("Times per day", "ครั้งต่อวัน"),
    "pharmacy.rx_duration_days":    ("Duration (days)", "จำนวนวัน"),
    "pharmacy.rx_sig":              ("Directions (Sig)", "วิธีใช้ยา"),
    "pharmacy.rx_quantity":         ("Quantity", "จำนวนจ่าย"),
    "pharmacy.rx_diagnosis":        ("Diagnosis", "การวินิจฉัย"),
    "pharmacy.rx_note":             ("Note on prescription", "หมายเหตุบนใบสั่งยา"),
    "pharmacy.rx_save":             ("Save prescription", "บันทึกใบสั่งยา"),
    "pharmacy.rx_save_print":       ("Save & print", "บันทึกและพิมพ์"),
    "pharmacy.rx_signature":        ("Prescriber's Signature", "ลายมือชื่อผู้สั่งยา"),
    "pharmacy.rx_license_no":       ("Medical License No.", "ใบอนุญาตประกอบวิชาชีพเวชกรรมเลขที่"),
    "pharmacy.rx_validity":         ("This prescription is valid only when signed by the prescriber.",
                                     "ใบสั่งยานี้มีผลเมื่อลงนามโดยผู้สั่งยาเท่านั้น"),

    # ── Patient / ผู้ป่วย ────────────────────────────────
    "patient.hn":                   ("HN", "เลข HN"),
    "patient.name_en":              ("Name (English)", "ชื่อ (อังกฤษ)"),
    "patient.name_th":              ("Name (Thai)", "ชื่อ (ไทย)"),
    "patient.dob":                  ("Date of Birth", "วันเกิด"),
    "patient.age":                  ("Age", "อายุ"),
    "patient.gender":               ("Gender", "เพศ"),
    "patient.phone":                ("Phone", "โทรศัพท์"),
    "patient.allergies":            ("Allergies", "ประวัติแพ้ยา"),

    # ── Label-specific / ฉลากยา ──────────────────────────
    "label.clinic_name":            ("Life by Dr. Pat", "คลินิก ไลฟ์ บาย ดร.แพท"),
    "label.patient":                ("Patient", "ผู้ป่วย"),
    "label.medication":             ("Medication", "ยา"),
    "label.dose":                   ("Dose", "ขนาดยา"),
    "label.usage":                  ("Usage", "วิธีใช้"),
    "label.warning":                ("Warning", "คำเตือน"),
    "label.date":                   ("Date", "วันที่"),
    "label.pharmacist":             ("Pharmacist", "เภสัชกร"),
    "label.prescriber":             ("Prescriber", "แพทย์ผู้สั่ง"),
    "label.qty":                    ("Qty", "จำนวน"),
    "label.expiry":                 ("Exp.", "วันหมดอายุ"),
}


def t(key: str, lang: str = "both") -> str:
    """
    Get translation for a key.
    lang: "en" | "th" | "both"
    "both" returns "English / ไทย" format.
    """
    pair = _TRANSLATIONS.get(key)
    if not pair:
        return key
    en, th = pair
    if lang == "en":
        return en
    if lang == "th":
        return th
    return f"{en} / {th}"


def t_en(key: str) -> str:
    return t(key, "en")

def t_th(key: str) -> str:
    return t(key, "th")

def t_pair(key: str) -> tuple:
    """Return (en, th) tuple."""
    return _TRANSLATIONS.get(key, (key, key))


def get_module_translations(prefix: str, lang: str = "both") -> dict:
    """Get all translations for a module prefix.
    e.g. get_module_translations("pharmacy") returns all pharmacy.* keys
    """
    result = {}
    for k, v in _TRANSLATIONS.items():
        if k.startswith(prefix + "."):
            short_key = k[len(prefix) + 1:]
            en, th = v
            if lang == "en":
                result[short_key] = en
            elif lang == "th":
                result[short_key] = th
            else:
                result[short_key] = {"en": en, "th": th}
    return result
