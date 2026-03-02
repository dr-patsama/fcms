"""
FCMS Module 2 - Import Service
Import inventory and patient history from Excel/CSV
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional
from io import BytesIO
import uuid
import re


class ImportService:
    def __init__(self, db: Session):
        self.db = db

    def _read_file(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext in ("xlsx", "xls"):
            return pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
        elif ext in ("csv", "tsv"):
            sep = "\t" if ext == "tsv" else ","
            return pd.read_csv(BytesIO(file_bytes), sep=sep, encoding="utf-8-sig")
        else:
            return pd.read_csv(BytesIO(file_bytes), encoding="utf-8-sig")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [
            re.sub(r"[^a-z0-9_]", "_", col.strip().lower().replace(" ", "_"))
            for col in df.columns
        ]
        return df

    def _map_columns(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        result_df = pd.DataFrame()
        for target, candidates in col_map.items():
            for c in candidates:
                if c in df.columns:
                    result_df[target] = df[c]
                    break
            if target not in result_df.columns:
                result_df[target] = None
        return result_df

    def _safe_float(self, val, default=0.0) -> Optional[float]:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _safe_str(self, val) -> Optional[str]:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return str(val).strip() or None

    def _safe_date(self, val) -> Optional[str]:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            if isinstance(val, datetime):
                return val.date().isoformat()
            parsed = pd.to_datetime(val, dayfirst=True)
            return parsed.date().isoformat()
        except Exception:
            return None

    # ─── INVENTORY IMPORT ───────────────────────────────────

    async def import_inventory(self, file_bytes: bytes, filename: str,
                                user_id: str) -> dict:
        df = self._read_file(file_bytes, filename)
        df = self._normalize_columns(df)

        col_map = {
            "item_code":        ["item_code", "code", "sku", "product_code"],
            "name_en":          ["name_en", "name", "item_name", "product_name", "description"],
            "name_th":          ["name_th", "thai_name"],
            "category":         ["category", "type", "group"],
            "unit":             ["unit", "uom", "unit_of_measure"],
            "quantity":         ["quantity", "qty", "stock", "on_hand"],
            "reorder_level":    ["reorder_level", "min_stock", "reorder", "minimum"],
            "unit_price":       ["unit_price", "price", "cost"],
            "supplier":         ["supplier", "vendor", "manufacturer"],
            "expiry_date":      ["expiry_date", "exp_date", "expiry"],
            "storage_location": ["storage_location", "location", "shelf"],
            "lot_number":       ["lot_number", "lot", "batch"],
        }

        mapped = self._map_columns(df, col_map)

        result = {
            "total_rows": len(mapped), "imported": 0, "skipped": 0,
            "errors": [], "warnings": [],
            "import_type": "inventory", "filename": filename,
            "imported_at": datetime.utcnow().isoformat(), "imported_by": user_id
        }

        for idx, row in mapped.iterrows():
            try:
                item_code = self._safe_str(row.get("item_code"))
                name = self._safe_str(row.get("name_en"))

                if not item_code and not name:
                    result["skipped"] += 1
                    continue
                if not item_code:
                    item_code = f"AUTO-{uuid.uuid4().hex[:8].upper()}"

                self.db.execute(text("""
                    INSERT INTO inventory_items
                        (id, item_code, name_en, name_th, category, unit,
                         quantity_on_hand, reorder_level, unit_price,
                         supplier, expiry_date, storage_location, lot_number,
                         created_at, created_by)
                    VALUES
                        (:id, :item_code, :name_en, :name_th, :category, :unit,
                         :qty, :reorder, :price,
                         :supplier, :expiry, :location, :lot,
                         NOW(), :user_id)
                    ON CONFLICT (item_code) DO UPDATE SET
                        quantity_on_hand = inventory_items.quantity_on_hand + EXCLUDED.quantity_on_hand,
                        unit_price = COALESCE(EXCLUDED.unit_price, inventory_items.unit_price),
                        updated_at = NOW()
                """), {
                    "id": str(uuid.uuid4()),
                    "item_code": item_code,
                    "name_en": name,
                    "name_th": self._safe_str(row.get("name_th")),
                    "category": self._safe_str(row.get("category")) or "uncategorized",
                    "unit": self._safe_str(row.get("unit")) or "pcs",
                    "qty": self._safe_float(row.get("quantity")),
                    "reorder": self._safe_float(row.get("reorder_level")),
                    "price": self._safe_float(row.get("unit_price"), default=None),
                    "supplier": self._safe_str(row.get("supplier")),
                    "expiry": self._safe_date(row.get("expiry_date")),
                    "location": self._safe_str(row.get("storage_location")),
                    "lot": self._safe_str(row.get("lot_number")),
                    "user_id": user_id,
                })
                result["imported"] += 1

            except Exception as e:
                result["errors"].append({
                    "row": idx + 2,
                    "item_code": str(row.get("item_code", "")),
                    "error": str(e)
                })
                result["skipped"] += 1

        self.db.commit()
        return result

    # ─── PATIENT / CLIENT HISTORY IMPORT ────────────────────

    async def import_patient_history(self, file_bytes: bytes, filename: str,
                                      user_id: str) -> dict:
        df = self._read_file(file_bytes, filename)
        df = self._normalize_columns(df)

        col_map = {
            "hn_number":       ["hn_number", "hn", "hospital_number", "patient_id", "mrn"],
            "first_name_en":   ["first_name_en", "first_name", "fname", "given_name"],
            "last_name_en":    ["last_name_en", "last_name", "lname", "surname", "family_name"],
            "first_name_th":   ["first_name_th", "thai_first_name"],
            "last_name_th":    ["last_name_th", "thai_last_name"],
            "date_of_birth":   ["date_of_birth", "dob", "birth_date", "birthday"],
            "gender":          ["gender", "sex"],
            "id_number":       ["id_number", "national_id", "thai_id", "passport", "citizen_id"],
            "phone":           ["phone", "tel", "mobile", "phone_number", "contact_number"],
            "email":           ["email", "e_mail", "email_address"],
            "blood_type":      ["blood_type", "blood_group"],
            "allergies":       ["allergies", "allergy", "drug_allergy"],
            "medical_history": ["medical_history", "past_medical_history", "pmh", "history"],
            "diagnosis":       ["diagnosis", "dx", "primary_diagnosis", "icd_code"],
            "treatment_notes": ["treatment_notes", "notes", "clinical_notes", "remarks"],
            "marital_status":  ["marital_status", "marital"],
            "occupation":      ["occupation", "job"],
            "address":         ["address", "home_address"],
            "emergency_contact": ["emergency_contact", "emergency_name"],
            "emergency_phone": ["emergency_phone", "emergency_tel"],
            "referring_doctor":["referring_doctor", "referred_by", "referral"],
            "insurance":       ["insurance", "insurance_provider"],
        }

        mapped = self._map_columns(df, col_map)

        result = {
            "total_rows": len(mapped), "imported": 0, "skipped": 0,
            "updated": 0, "errors": [], "warnings": [],
            "import_type": "patient_history", "filename": filename,
            "imported_at": datetime.utcnow().isoformat(), "imported_by": user_id
        }

        for idx, row in mapped.iterrows():
            try:
                first_name = self._safe_str(row.get("first_name_en"))
                last_name = self._safe_str(row.get("last_name_en"))

                if not first_name or not last_name:
                    result["skipped"] += 1
                    result["warnings"].append(f"Row {idx+2}: Missing name, skipped")
                    continue

                hn = self._safe_str(row.get("hn_number"))
                id_number = self._safe_str(row.get("id_number"))
                dob = self._safe_date(row.get("date_of_birth"))
                gender = self._safe_str(row.get("gender"))
                if gender:
                    gender = gender.lower()
                    if gender in ("f", "female", "หญิง"):
                        gender = "female"
                    elif gender in ("m", "male", "ชาย"):
                        gender = "male"

                # Check for existing patient by HN or ID number
                existing = None
                if hn:
                    existing = self.db.execute(text(
                        "SELECT id FROM patients WHERE hn_number = :hn"
                    ), {"hn": hn}).fetchone()
                if not existing and id_number:
                    existing = self.db.execute(text(
                        "SELECT id FROM patients WHERE id_number = :id_num"
                    ), {"id_num": id_number}).fetchone()

                if existing:
                    # Update existing patient
                    self.db.execute(text("""
                        UPDATE patients SET
                            first_name_th = COALESCE(:first_th, first_name_th),
                            last_name_th = COALESCE(:last_th, last_name_th),
                            phone = COALESCE(:phone, phone),
                            email = COALESCE(:email, email),
                            blood_type = COALESCE(:blood, blood_type),
                            allergies = COALESCE(:allergies, allergies),
                            medical_history = COALESCE(:med_hist, medical_history),
                            occupation = COALESCE(:occupation, occupation),
                            address = COALESCE(:address, address),
                            insurance_provider = COALESCE(:insurance, insurance_provider),
                            updated_at = NOW()
                        WHERE id = :pid
                    """), {
                        "pid": str(existing[0]),
                        "first_th": self._safe_str(row.get("first_name_th")),
                        "last_th": self._safe_str(row.get("last_name_th")),
                        "phone": self._safe_str(row.get("phone")),
                        "email": self._safe_str(row.get("email")),
                        "blood": self._safe_str(row.get("blood_type")),
                        "allergies": self._safe_str(row.get("allergies")),
                        "med_hist": self._safe_str(row.get("medical_history")),
                        "occupation": self._safe_str(row.get("occupation")),
                        "address": self._safe_str(row.get("address")),
                        "insurance": self._safe_str(row.get("insurance")),
                    })
                    result["updated"] += 1
                else:
                    # Generate HN if not provided
                    if not hn:
                        year = datetime.now().year
                        count_result = self.db.execute(text(
                            "SELECT COUNT(*) FROM patients WHERE hn_number LIKE :prefix"
                        ), {"prefix": f"HN-{year}-%"}).fetchone()
                        seq = (count_result[0] if count_result else 0) + 1
                        hn = f"HN-{year}-{seq:05d}"

                    # Insert new patient
                    self.db.execute(text("""
                        INSERT INTO patients
                            (id, hn_number, first_name_en, last_name_en,
                             first_name_th, last_name_th,
                             date_of_birth, gender, id_number,
                             phone, email, blood_type, allergies,
                             medical_history, marital_status, occupation,
                             address, emergency_contact_name, emergency_contact_phone,
                             referring_doctor, insurance_provider,
                             created_at, created_by)
                        VALUES
                            (:id, :hn, :first_en, :last_en,
                             :first_th, :last_th,
                             :dob, :gender, :id_num,
                             :phone, :email, :blood, :allergies,
                             :med_hist, :marital, :occupation,
                             :address, :emergency_name, :emergency_phone,
                             :ref_doc, :insurance,
                             NOW(), :user_id)
                    """), {
                        "id": str(uuid.uuid4()),
                        "hn": hn,
                        "first_en": first_name,
                        "last_en": last_name,
                        "first_th": self._safe_str(row.get("first_name_th")),
                        "last_th": self._safe_str(row.get("last_name_th")),
                        "dob": dob,
                        "gender": gender,
                        "id_num": id_number,
                        "phone": self._safe_str(row.get("phone")),
                        "email": self._safe_str(row.get("email")),
                        "blood": self._safe_str(row.get("blood_type")),
                        "allergies": self._safe_str(row.get("allergies")),
                        "med_hist": self._safe_str(row.get("medical_history")),
                        "marital": self._safe_str(row.get("marital_status")),
                        "occupation": self._safe_str(row.get("occupation")),
                        "address": self._safe_str(row.get("address")),
                        "emergency_name": self._safe_str(row.get("emergency_contact")),
                        "emergency_phone": self._safe_str(row.get("emergency_phone")),
                        "ref_doc": self._safe_str(row.get("referring_doctor")),
                        "insurance": self._safe_str(row.get("insurance")),
                        "user_id": user_id,
                    })
                    result["imported"] += 1

                # If diagnosis/treatment notes exist, create a history record
                diagnosis = self._safe_str(row.get("diagnosis"))
                treatment = self._safe_str(row.get("treatment_notes"))
                if diagnosis or treatment:
                    pid = str(existing[0]) if existing else hn
                    patient_row = self.db.execute(text(
                        "SELECT id FROM patients WHERE hn_number = :hn"
                    ), {"hn": hn}).fetchone()
                    if patient_row:
                        self.db.execute(text("""
                            INSERT INTO patient_import_history
                                (id, patient_id, diagnosis, treatment_notes,
                                 source_file, imported_at, imported_by)
                            VALUES
                                (:id, :pid, :dx, :notes, :file, NOW(), :uid)
                        """), {
                            "id": str(uuid.uuid4()),
                            "pid": str(patient_row[0]),
                            "dx": diagnosis,
                            "notes": treatment,
                            "file": filename,
                            "uid": user_id,
                        })

            except Exception as e:
                result["errors"].append({
                    "row": idx + 2,
                    "name": f"{row.get('first_name_en', '')} {row.get('last_name_en', '')}",
                    "error": str(e)
                })
                result["skipped"] += 1

        self.db.commit()
        return result

    # ─── TEMPLATE GENERATORS ────────────────────────────────

    def generate_inventory_template(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "item_code", "name_en", "name_th", "category", "unit",
            "quantity", "reorder_level", "unit_price", "supplier",
            "expiry_date", "storage_location", "lot_number"
        ])

    def generate_patient_template(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "hn_number", "first_name_en", "last_name_en",
            "first_name_th", "last_name_th",
            "date_of_birth", "gender", "id_number",
            "phone", "email", "blood_type", "allergies",
            "medical_history", "diagnosis", "treatment_notes",
            "marital_status", "occupation", "address",
            "emergency_contact", "emergency_phone",
            "referring_doctor", "insurance"
        ])
