"""
FCMS Module 5 — Medical Supply Bilingual Translations / คำแปลเวชภัณฑ์สองภาษา
Shared translation dictionary for frontend and backend.
"""

SUPPLY_TRANSLATIONS = {
    # ── Navigation / Tabs ──────────────────────────────────
    "dashboard":          {"en": "Dashboard",           "th": "แดชบอร์ด"},
    "supplyCatalogue":    {"en": "Supply Catalogue",    "th": "รายการเวชภัณฑ์"},
    "stock":              {"en": "Stock",               "th": "สต็อก"},
    "requisitions":       {"en": "Requisitions",        "th": "ใบเบิก"},
    "suppliers":          {"en": "Suppliers",           "th": "ผู้จำหน่าย"},
    "usageLog":           {"en": "Usage Log",           "th": "บันทึกการใช้"},
    "alerts":             {"en": "Alerts",              "th": "แจ้งเตือน"},
    "reports":            {"en": "Reports",             "th": "รายงาน"},

    # ── Common Fields ──────────────────────────────────────
    "search":             {"en": "Search",              "th": "ค้นหา"},
    "addItem":            {"en": "Add Item",            "th": "เพิ่มรายการ"},
    "addSupplier":        {"en": "Add Supplier",        "th": "เพิ่มผู้จำหน่าย"},
    "name":               {"en": "Name",                "th": "ชื่อ"},
    "category":           {"en": "Category",            "th": "หมวดหมู่"},
    "subcategory":        {"en": "Subcategory",         "th": "หมวดหมู่ย่อย"},
    "department":         {"en": "Department",          "th": "แผนก"},
    "unit":               {"en": "Unit",                "th": "หน่วย"},
    "currentStock":       {"en": "Current Stock",       "th": "คงคลัง"},
    "status":             {"en": "Status",              "th": "สถานะ"},
    "actions":            {"en": "Actions",             "th": "การดำเนินการ"},
    "sku":                {"en": "SKU",                 "th": "รหัสสินค้า"},
    "catalogNumber":      {"en": "Catalog #",           "th": "เลขแค็ตตาล็อก"},
    "manufacturer":       {"en": "Manufacturer",        "th": "ผู้ผลิต"},
    "supplier":           {"en": "Supplier",            "th": "ผู้จำหน่าย"},
    "unitCost":           {"en": "Unit Cost",           "th": "ราคาต่อหน่วย"},
    "packSize":           {"en": "Pack Size",           "th": "ขนาดบรรจุ"},
    "reorderLevel":       {"en": "Reorder Level",       "th": "ระดับสั่งซื้อ"},

    # ── Stock Status ───────────────────────────────────────
    "ok":                 {"en": "In Stock",            "th": "มีสต็อก"},
    "lowStock":           {"en": "Low Stock",           "th": "สต็อกต่ำ"},
    "outOfStock":         {"en": "Out of Stock",        "th": "หมดสต็อก"},
    "expiring30d":        {"en": "Expiring ≤30d",      "th": "หมดอายุ ≤30 วัน"},
    "expired":            {"en": "Expired",             "th": "หมดอายุแล้ว"},

    # ── Requisition Status ─────────────────────────────────
    "pending":            {"en": "Pending",             "th": "รอดำเนินการ"},
    "approved":           {"en": "Approved",            "th": "อนุมัติแล้ว"},
    "issued":             {"en": "Issued",              "th": "จ่ายแล้ว"},
    "partiallyIssued":    {"en": "Partially Issued",    "th": "จ่ายบางส่วน"},
    "rejected":           {"en": "Rejected",            "th": "ปฏิเสธ"},
    "cancelled":          {"en": "Cancelled",           "th": "ยกเลิก"},

    # ── Dashboard Cards ────────────────────────────────────
    "totalItems":         {"en": "Total Items",         "th": "รายการทั้งหมด"},
    "totalSuppliers":     {"en": "Total Suppliers",     "th": "ผู้จำหน่ายทั้งหมด"},
    "stockValue":         {"en": "Stock Value",         "th": "มูลค่าสต็อก"},
    "pendingReqs":        {"en": "Pending Reqs",        "th": "ใบเบิกรอ"},

    # ── Stock Operations ───────────────────────────────────
    "receiveStock":       {"en": "Receive Stock",       "th": "รับสต็อกเข้า"},
    "adjustStock":        {"en": "Adjust Stock",        "th": "ปรับสต็อก"},
    "lotNumber":          {"en": "Lot",                 "th": "เลขล็อต"},
    "expiryDate":         {"en": "Expiry",              "th": "วันหมดอายุ"},
    "quantity":           {"en": "Qty",                 "th": "จำนวน"},
    "daysLeft":           {"en": "Days Left",           "th": "เหลือ (วัน)"},
    "valueAtRisk":        {"en": "Value at Risk",       "th": "มูลค่าเสี่ยง"},
    "grnNumber":          {"en": "GRN #",               "th": "เลขรับของ"},

    # ── Requisition ────────────────────────────────────────
    "createRequisition":  {"en": "Create Requisition",  "th": "สร้างใบเบิก"},
    "reqNumber":          {"en": "Req #",               "th": "เลขใบเบิก"},
    "requestedQty":       {"en": "Requested",           "th": "เบิก"},
    "issuedQty":          {"en": "Issued",              "th": "จ่ายแล้ว"},
    "approve":            {"en": "Approve",             "th": "อนุมัติ"},
    "reject":             {"en": "Reject",              "th": "ปฏิเสธ"},
    "issue":              {"en": "Issue",               "th": "จ่าย"},

    # ── Usage ──────────────────────────────────────────────
    "recordUsage":        {"en": "Record Usage",        "th": "บันทึกการใช้"},
    "procedureType":      {"en": "Procedure",           "th": "หัตถการ"},
    "usedBy":             {"en": "Used By",             "th": "ใช้โดย"},

    # ── Buttons ────────────────────────────────────────────
    "save":               {"en": "Save",                "th": "บันทึก"},
    "cancel":             {"en": "Cancel",              "th": "ยกเลิก"},
    "edit":               {"en": "Edit",                "th": "แก้ไข"},
    "delete":             {"en": "Delete",              "th": "ลบ"},
    "view":               {"en": "View",                "th": "ดู"},
    "close":              {"en": "Close",               "th": "ปิด"},
    "print":              {"en": "Print",               "th": "พิมพ์"},
    "export":             {"en": "Export",              "th": "ส่งออก"},

    # ── Storage Conditions ─────────────────────────────────
    "roomTemp":           {"en": "Room temperature",    "th": "อุณหภูมิห้อง"},
    "refrigerated":       {"en": "Refrigerated",        "th": "แช่เย็น"},
    "frozen":             {"en": "Frozen",              "th": "แช่แข็ง"},
    "sterile":            {"en": "Sterile",             "th": "ปลอดเชื้อ"},
}
