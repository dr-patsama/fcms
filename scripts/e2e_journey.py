"""
End-to-end exercise of the journey layer against the live database (run from repo root):
    PYTHONPATH=. python scripts/e2e_journey.py
Creates a demo couple, runs a full IVF/ICSI freeze-all cycle through every lane, and the patient-app flow.
Safe to re-run (new HNs each time).
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime, timedelta, time

from fastapi.testclient import TestClient

from app.main import app
from module1.backend.core.database import SessionLocal
from module1.backend.models.emr_models import Patient

c = TestClient(app)
OK = 0
FAIL = 0


def check(name, cond, extra=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {extra}")


def login(email, pw="LifeByDrPat2026!"):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def j(r):
    try:
        return r.json()
    except Exception:
        return r.text


print("── auth")
H = login("admin@lifeclinic.com")            # admin passes every role check
HP = login("physician@lifeclinic.com", "Fcms2026!") if c.post("/api/v1/auth/login", json={"email": "physician@lifeclinic.com", "password": "Fcms2026!"}).status_code == 200 else H

print("── seed packages")
r = c.post("/api/v1/journey/packages/seed", headers=H)
check("seed", r.status_code == 200, j(r))
pk = c.get("/api/v1/journey/packages", headers=H).json()
check("packages listed", len(pk) >= 10, len(pk))
pkg = next(p for p in pk if p["code"] == "IVF_ICSI_PGT_A")

print("── demo couple")
db = SessionLocal()
tag = uuid.uuid4().hex[:4].upper()
f = Patient(id=str(uuid.uuid4()), hn_number=f"HN-E2E-{tag}F", first_name_en="Anong", last_name_en=f"Test{tag}", first_name_th="อนงค์", last_name_th="ทดสอบ",
            gender="female", date_of_birth=date(1990, 5, 2), phone=f"08{tag.lower().encode().hex()[:8]}", preferred_language="th", email="anong@example.com")
m = Patient(id=str(uuid.uuid4()), hn_number=f"HN-E2E-{tag}M", first_name_en="Somchai", last_name_en=f"Test{tag}", first_name_th="สมชาย", last_name_th="ทดสอบ",
            gender="male", date_of_birth=date(1988, 1, 9), phone=f"09{tag.lower().encode().hex()[:8]}", preferred_language="th")
db.add(f); db.flush(); db.add(m); db.commit()
F_ID, M_ID = str(f.id), str(m.id)
db.close()
r = c.post(f"/api/v1/journey/patients/{F_ID}/partner", json={"partner_id": M_ID}, headers=H)
check("partner linked", r.status_code == 200, j(r))
r = c.get("/api/v1/journey/patients/search", params={"q": f"E2E-{tag}F"}, headers=H)
check("patient search shows partner", r.status_code == 200 and r.json()[0]["partner"]["id"] == M_ID, j(r))

print("── create cycle from package")
start = date.today() - timedelta(days=9)
r = c.post("/api/v1/journey/cycles", json={"patient_id": F_ID, "package_id": pkg["id"], "medication_start_date": str(start),
                                            "physician_order": "Freeze-all, PGT-A"}, headers=HP)
check("cycle created", r.status_code == 200, j(r))
cyc = r.json(); CID = cyc["id"]
ws = c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()
check("chart pre-filled from package", len(ws["chart"]["medications"]) == 3, len(ws["chart"]["medications"]))
check("consents created", len(ws["consents"]) == len(pkg["consents"]), (len(ws["consents"]), len(pkg["consents"])))
check("cycle.created event → consent.pending notification", any(e["type"] == "cycle.created" for e in ws["events"]))

print("── stimulation chart → publish")
r = c.post(f"/api/v1/journey/cycles/{CID}/publish", headers=HP)
check("plan published", r.status_code == 200 and r.json()["doses_created"] > 0, j(r))
ws = c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()
check("cycle status stimulating", ws["cycle"]["status"] == "stimulating", ws["cycle"]["status"])
n_notif = c.get("/api/v1/journey/notifications", params={"patient_id": F_ID}, headers=H).json()
check("dose reminders scheduled", any(n["type"] == "dose.reminder" for n in n_notif), len(n_notif))

print("── monitoring + trigger")
r = c.post(f"/api/v1/journey/cycles/{CID}/monitoring", json={"calendar_date": str(start + timedelta(days=5)), "follicles_right": [12, 11, 10], "follicles_left": [13, 9],
                                                             "endometrium_mm": 7.5, "e2": 820, "lh": 2.1, "released_to_patient": True}, headers=HP)
check("monitoring recorded", r.status_code == 200, j(r))
trig = datetime.combine(start + timedelta(days=10), time(21, 0))
r = c.post(f"/api/v1/journey/cycles/{CID}/trigger", json={"trigger_at": trig.isoformat(), "drug": "hCG 250 mcg"}, headers=HP)
check("trigger set", r.status_code == 200 and "suggested_opu" in r.json(), j(r))

print("── schedule OPU → lab tasks")
d0 = start + timedelta(days=12)
r = c.post(f"/api/v1/journey/cycles/{CID}/schedule", json={"d0": str(d0), "time": "08:00", "room": "OR-1"}, headers=HP)
check("OPU scheduled", r.status_code == 200 and r.json()["tasks_generated"] > 0, j(r))
ws = c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()
tasks = ws["tasks"]
check("tasks grouped D0..D7", {t["lab_day"] for t in tasks} >= {0, 1, 3, 5}, sorted({t["lab_day"] for t in tasks}))
check("appointment created & linked", len(ws["appointments"]) == 1 and ws["appointments"][0]["appointment_type"] == "egg_collection", ws["appointments"])
opu_task = next(t for t in tasks if t["key"] == "opu")
check("OPU blocked by unsigned consents", opu_task["effective_status"] == "blocked" and len(opu_task["blocked_by_consent"]) >= 2, opu_task["blocked_by_consent"])
r = c.get("/api/v1/journey/lab/tasks", params={"on": str(d0)}, headers=H)
check("lab to-do for the day", r.status_code == 200 and "opu" in r.json()["groups"], list(j(r).get("groups", {}).keys()) if r.status_code == 200 else j(r))

print("── consent gating: witness refused until signed, then sign in clinic")
r = c.post(f"/api/v1/journey/lab/tasks/{opu_task['id']}/witness/start", headers=H)
check("witness start refused (consent)", r.status_code == 409, r.status_code)
sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
for cc in ws["consents"]:
    r = c.post(f"/api/v1/journey/consents/{cc['id']}/sign", json={"signature": sig, "channel": "clinic_tablet"}, headers=H)
    assert r.status_code == 200, r.text
check("all consents signed", all(x["status"] == "signed" for x in c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()["consents"]))
r = c.get(f"/api/v1/journey/consents/{ws['consents'][0]['id']}/file", headers=H)
check("consent PDF produced", r.status_code == 200 and r.content[:4] == b"%PDF", r.status_code)

print("── labels")
r = c.post("/api/v1/journey/labels/print", json={"task_ids": [t["id"] for t in tasks if t["lab_day"] == 0], "copies": 1}, headers=H)
check("label PDF", r.status_code == 200 and r.content[:4] == b"%PDF", r.status_code)
items = c.get(f"/api/v1/journey/cycles/{CID}/items", headers=H).json()
check("lab items created (wristband, tubes, dishes)", {i["item_type"] for i in items} >= {"wristband", "opu_tube", "oocyte_dish", "sperm_tube", "prep_tube"}, {i["item_type"] for i in items})
check("partner items belong to partner", any(i["item_type"] == "sperm_tube" and i["patient_id"] == M_ID for i in items))

print("── witnessing by scan")
def scan_all(task):
    r = c.post(f"/api/v1/journey/lab/tasks/{task['id']}/witness/start", headers=H)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    last = None
    for it_type in task["items_required"]:
        # pick the item of that type for this cycle (partner's for sperm items)
        cand = [i for i in items if i["item_type"] == it_type and (i["lab_day"] in (None, task["lab_day"]) or it_type != "cryo_device")]
        owner = M_ID if it_type in ("sperm_tube", "prep_tube") else F_ID
        cand = [i for i in cand if i["patient_id"] == owner] or cand
        last = c.post(f"/api/v1/journey/witness/{sid}/scan", json={"payload": cand[0]["label_code"]}, headers=H).json()
    return last

res = scan_all(opu_task)
check("OPU witnessed by scans", res["status"] == "match", res)
# mismatch test: scan a foreign label on sperm collection
sc_task = next(t for t in tasks if t["key"] == "sperm_collection")
r = c.post(f"/api/v1/journey/lab/tasks/{sc_task['id']}/witness/start", headers=H); sid = r.json()["id"]
r = c.post(f"/api/v1/journey/witness/{sid}/scan", json={"payload": "LBL-NOTAREALCODE"}, headers=H)
check("unknown label → mismatch + incident", r.json()["status"] == "mismatch" and r.json().get("incident_id"), j(r))
inc = c.get("/api/v1/journey/lab/incidents", headers=H).json()
check("incident listed", any(i["lab_task_id"] == sc_task["id"] for i in inc))
res = scan_all(sc_task)
check("sperm collection witnessed after retry", res["status"] == "match", res)
# manual double witness on sperm prep
sp_task = next(t for t in tasks if t["key"] == "sperm_prep")
r = c.post(f"/api/v1/journey/lab/tasks/{sp_task['id']}/witness/manual", json={"second_email": "embryologist@lifeclinic.com", "second_password": "Fcms2026!"}, headers=H)
check("manual double-witness", r.status_code == 200 and r.json()["status"] == "manual", j(r))
rec = c.get(f"/api/v1/journey/cycles/{CID}/scan-record", headers=H).json()
check("scan record has sessions", len(rec) >= 3, len(rec))

print("── observation D0–D5")
r = c.post(f"/api/v1/journey/cycles/{CID}/opu", json={"total_follicles_aspirated": 12, "total_oocytes_retrieved": 8, "mii_count": 6, "mi_count": 1, "gv_count": 1}, headers=H)
check("OPU recorded, oocytes created", r.status_code == 200 and len(r.json()["table"]) == 8, j(r) if r.status_code != 200 else len(r.json()["table"]))
den = next(t for t in tasks if t["key"] == "denudation")
r = c.post(f"/api/v1/journey/lab/tasks/{den['id']}/done", headers=H)
check("non-witness task done manually", r.status_code == 200 and r.json()["status"] == "done", j(r))
icsi = next(t for t in tasks if t["key"] == "icsi")
res = scan_all(icsi)
check("ICSI witnessed → insemination time written back", res["status"] == "match" and
      all(x["inseminated"] for x in c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()["observation"]["table"]), res)
obs = c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()["observation"]
fert_items = [{"oocyte_id": x["oocyte_id"], "status": s} for x, s in zip(obs["table"], ["2PN", "2PN", "2PN", "2PN", "1PN", "0PN", "2PN", "DG"])]
r = c.post(f"/api/v1/journey/cycles/{CID}/fertilization", json={"items": fert_items}, headers=H)
check("fertilisation recorded, embryos created for 2PN", r.status_code == 200 and r.json()["summary"]["embryos"] == 5, j(r) if r.status_code != 200 else r.json()["summary"])
obs = r.json()
embryos = [x for x in obs["table"] if x["embryo_id"]]
for i, e in enumerate(embryos):
    c.post(f"/api/v1/journey/cycles/{CID}/embryos/{e['embryo_id']}/assessment", json={"assessment_day": 3, "cell_count": 8 if i < 4 else 5, "fragmentation_pct": 5}, headers=H)
    if i < 3:
        r = c.post(f"/api/v1/journey/cycles/{CID}/embryos/{e['embryo_id']}/assessment",
                   json={"assessment_day": 5, "expansion": "4", "icm_grade": "A", "te_grade": "B", "disposition": "frozen", "pgta_result": "euploid" if i < 2 else "aneuploid"}, headers=H)
        assert r.status_code == 200, r.text
check("D5 grades", all(e["days"].get("5", {}).get("grade") == "4AB" for e in [x for x in c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()["observation"]["table"] if x.get("embryo_id")][:3]))
for e in embryos[:2]:
    r = c.post(f"/api/v1/journey/cycles/{CID}/embryos/{e['embryo_id']}/freeze", json={"device": "cryotop", "tank_id": "T1", "canister": "C2", "goblet": "G3", "position": "1"}, headers=H)
    assert r.status_code == 200, r.text
ws = c.get(f"/api/v1/journey/cycles/{CID}", headers=H).json()
check("frozen embryos → cryo storage term opened", ws["observation"]["summary"]["frozen"] == 2 and len(ws["cryo_terms"]) >= 1, (ws["observation"]["summary"]["frozen"], len(ws["cryo_terms"])))
items = c.get(f"/api/v1/journey/cycles/{CID}/items", headers=H).json()
check("cryo devices labelled", sum(1 for i in items if i["item_type"] == "cryo_device" and i["reference_id"]) == 2)

print("── photos & album")
import io
from PIL import Image
buf = io.BytesIO(); Image.new("RGB", (64, 64), (200, 30, 90)).save(buf, "JPEG"); buf.seek(0)
r = c.post(f"/api/v1/journey/cycles/{CID}/photos", files={"file": ("emb.jpg", buf.getvalue(), "image/jpeg")},
           data={"embryo_id": embryos[0]["embryo_id"], "lab_day": "5", "caption_en": "Day 5 blastocyst", "release": "true"}, headers=H)
check("photo uploaded and released", r.status_code == 200 and r.json()["released_to_patient"], j(r))

print("── outcome, report, cryo due, KPIs")
r = c.post(f"/api/v1/journey/cycles/{CID}/outcome", json={"ohss_grade": "none"}, headers=HP)
check("outcome saved", r.status_code == 200, j(r))
r = c.get(f"/api/v1/journey/cycles/{CID}/report.pdf", headers=H)
check("cycle report PDF", r.status_code == 200 and r.content[:4] == b"%PDF", r.status_code)
r = c.get("/api/v1/journey/cryo/due", params={"within_days": 400}, headers=H)
check("cryo due list", r.status_code == 200 and any(x["cycle_id"] == CID for x in r.json()), j(r))
term = next(x for x in r.json() if x["cycle_id"] == CID)
r = c.post(f"/api/v1/journey/cryo/terms/{term['id']}/renew", json={"annual_fee": 12000, "payment_method": "promptpay", "reference": "TEST"}, headers=H)
check("renewal → invoice + payment", r.status_code == 200 and r.json()["invoice_id"], j(r))
r = c.post("/api/v1/journey/cryo/run-reminders", headers=H)
check("cryo reminder job runs", r.status_code == 200, j(r))
r = c.get("/api/v1/journey/kpi", headers=H)
k = r.json()
check("KPIs computed", r.status_code == 200 and k["laboratory"]["icsi_normal_fertilisation_rate_pct"] is not None, k.get("laboratory", {}).get("icsi_normal_fertilisation_rate_pct"))
r = c.get("/api/v1/journey/kpi/export.xlsx", headers=H)
check("KPI xlsx", r.status_code == 200 and len(r.content) > 2000)
r = c.get("/api/v1/journey/calendar/status", headers=H)
check("calendar status endpoint", r.status_code == 200 and r.json()["enabled"] in (True, False))
r = c.post("/api/v1/journey/jobs/daily", headers=H)
check("daily job", r.status_code == 200, j(r))

print("── CRM hook: front-desk booking → journey events")
r = c.post("/api/v1/crm/appointments", json={"patient_id": F_ID, "appointment_date": str(date.today() + timedelta(days=3)), "appointment_time": "14:00", "appointment_type": "follow_up"}, headers=H)
check("CRM appointment created", r.status_code == 200, j(r))
appt_id = r.json()["id"]
r = c.post(f"/api/v1/crm/appointments/{appt_id}/check-in", headers=H) if False else None
n_notif = c.get("/api/v1/journey/notifications", params={"patient_id": F_ID}, headers=H).json()
check("visit.booked notification", any(n["type"] == "visit.booked" for n in n_notif), [n["type"] for n in n_notif][:10])

print("── patient portal")
r = c.post("/api/v1/portal/auth/otp/request", json={"hn": f"HN-E2E-{tag}F", "dob": "1990-05-02"})
check("OTP requested (dev echo)", r.status_code == 200 and "dev_code" in r.json(), j(r))
r2 = c.post("/api/v1/portal/auth/otp/verify", json={"account_id": r.json()["account_id"], "code": r.json()["dev_code"]})
check("OTP verified → patient token", r2.status_code == 200 and r2.json().get("access_token"), j(r2))
PH = {"Authorization": f"Bearer {r2.json()['access_token']}"}
r = c.get("/api/v1/portal/home", headers=PH)
check("portal home", r.status_code == 200 and r.json()["cycle"]["id"] == CID, j(r))
r = c.get(f"/api/v1/portal/cycles/{CID}", headers=PH)
check("portal cycle calendar + album + released monitoring", r.status_code == 200 and len(r.json()["calendar"]) > 10 and len(r.json()["album"]) == 1 and len(r.json()["monitoring"]) == 1, (len(j(r).get("calendar", {})), len(j(r).get("album", []))))
dose = next(iter(d for day in r.json()["calendar"].values() for d in day.get("doses", [])), None)
r = c.post(f"/api/v1/portal/doses/{dose['id']}/taken", headers=PH)
check("patient ticks a dose", r.status_code == 200 and r.json()["taken_at"], j(r))
r = c.get("/api/v1/portal/results", headers=PH)
check("portal results", r.status_code == 200 and len(r.json()["monitoring"]) == 1)
r = c.get("/api/v1/portal/cryo", headers=PH)
check("portal cryo inventory", r.status_code == 200 and len(r.json()["embryos"]) == 2 and len(r.json()["terms"]) >= 1, j(r))
r = c.get("/api/v1/portal/invoices", headers=PH)
check("portal invoices", r.status_code == 200 and len(r.json()) >= 1)
r = c.post("/api/v1/portal/booking-requests", json={"date": str(date.today() + timedelta(days=7)), "time": "15:00", "appointment_type": "follow_up", "note": "ขอเลื่อนบ่าย"}, headers=PH)
check("booking request", r.status_code == 200, j(r))
req_id = r.json()["id"]
r = c.post(f"/api/v1/journey/booking-requests/{req_id}/confirm", json={}, headers=H)
check("desk confirms booking → appointment", r.status_code == 200 and r.json()["appointment_id"], j(r))
r = c.get("/api/v1/portal/notifications", headers=PH)
check("portal notification feed", r.status_code == 200 and len(r.json()) >= 3, len(j(r)))
r = c.get("/api/v1/portal/album", headers=PH)
pid = r.json()[0]["id"]
r = c.get(f"/api/v1/portal/album/{pid}/file", headers=PH)
check("album photo download", r.status_code == 200 and r.headers["content-type"].startswith("image/"))
r = c.get(f"/api/v1/portal/reports/{CID}.pdf", headers=PH)
check("patient cycle report", r.status_code == 200 and r.content[:4] == b"%PDF")

print("── pages served")
for path in ["/cycles", f"/cycles/{CID}", "/lab/todo", "/lab/witness", "/admin/packages", "/insight", "/desk", "/portal"]:
    r = c.get(path)
    check(f"GET {path}", r.status_code == 200 and "<html" in r.text.lower()[:300], r.status_code)

print(f"\n{OK} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
