"""
Cycle report (Binflux: 'cycle report' in HIS and CareU) — bilingual A4 PDF summarising stimulation,
monitoring, OPU, fertilisation, embryo development, transfer, cryo and outcome.
"""
from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from module2.backend.models.lab_models import TreatmentCycle

from ..core.config import jsettings
from .common import now, th_date, to_json
from .labels import _fonts, _font
from .observation import workspace

RUBY = colors.HexColor("#E0115F")
SAPPHIRE_DEEP = colors.HexColor("#151667")
EMERALD = colors.HexColor("#009473")
GRAY = colors.HexColor("#6B7280")


def _line(pdf, x, y, text, size=10, bold=False, color=colors.black):
    pdf.setFont(_font(bold), size)
    pdf.setFillColor(color)
    pdf.drawString(x, y, str(text))
    pdf.setFillColor(colors.black)


def cycle_report_pdf(db: Session, c: TreatmentCycle) -> bytes:
    _fonts()
    ws = workspace(db, c)
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    L = 18 * mm
    y = h - 20 * mm

    # Header band
    pdf.setFillColor(SAPPHIRE_DEEP)
    pdf.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    _line(pdf, L, h - 9 * mm, jsettings.CLINIC_NAME_EN + "  ·  Cycle report / รายงานผลรอบการรักษา", 12, True, colors.white)
    y = h - 24 * mm
    p, partner, cyc = ws["patient"], ws["partner"], ws["cycle"]
    _line(pdf, L, y, f"{p['name_en']} ({p['name_th']})   HN {p['hn_number']}   Age {p['age'] or ''}", 11, True)
    y -= 5.5 * mm
    if partner:
        _line(pdf, L, y, f"Partner: {partner['name_en']}   HN {partner['hn_number']}", 9.5, False, GRAY)
        y -= 5 * mm
    _line(pdf, L, y, f"Cycle {cyc['cycle_number']} · {cyc['package']['name_en'] if cyc.get('package') else cyc['cycle_type']} · "
                     f"Physician {cyc.get('physician') or ''} · Status {cyc['status']}", 9.5, False, GRAY)
    y -= 5 * mm
    _line(pdf, L, y, f"Medication start {cyc.get('medication_start_date') or '-'} · Trigger {str(cyc.get('trigger_at') or '-')[:16]} · "
                     f"D0 {cyc.get('d0_date') or '-'} · Report {th_date(now().date())}", 9.5, False, GRAY)
    y -= 9 * mm

    # Stimulation chart
    _line(pdf, L, y, "Stimulation / ยากระตุ้น", 11, True, RUBY); y -= 5.5 * mm
    for m in ws["chart"]["medications"]:
        _line(pdf, L, y, f"• {m['drug_en']} ({m.get('drug_th') or ''}) {to_json(m.get('dose')) or ''} {m.get('unit') or ''} {m.get('route') or ''} "
                         f"{m.get('slot') or ''}  day {m['start_day_index']}–{m['end_day_index']}", 9.5)
        y -= 4.8 * mm
    y -= 3 * mm

    # Monitoring
    if ws["monitoring"]:
        _line(pdf, L, y, "Monitoring / การติดตาม", 11, True, RUBY); y -= 5.5 * mm
        _line(pdf, L, y, "Date        Day  Follicles R / L            Endo   E2      LH     P4", 8.5, True, GRAY); y -= 4.5 * mm
        for mo in ws["monitoring"]:
            fr = ",".join(str(x) for x in (mo.get("follicles_right") or []))
            fl = ",".join(str(x) for x in (mo.get("follicles_left") or []))
            _line(pdf, L, y, f"{mo['calendar_date']}  {mo.get('day_index') or '':>3}  {fr[:14]:<14} / {fl[:14]:<14}  "
                             f"{to_json(mo.get('endometrium_mm')) or '-':>4}  {to_json(mo.get('e2')) or '-':>6}  {to_json(mo.get('lh')) or '-':>5}  {to_json(mo.get('p4')) or '-':>5}", 8.5)
            y -= 4.3 * mm
        y -= 3 * mm

    # Lab summary
    s = ws["observation"]["summary"]
    _line(pdf, L, y, "Laboratory / ห้องปฏิบัติการ", 11, True, RUBY); y -= 5.5 * mm
    _line(pdf, L, y, f"Follicles aspirated {s['follicles_aspirated'] or '-'} · Oocytes {s['oocytes_retrieved'] or '-'} · MII {s['mii'] or 0} · "
                     f"Inseminated {s['inseminated']} · 2PN {s['2pn']} · Embryos {s['embryos']} · Blastocysts {s['blastocysts']} · "
                     f"Biopsied {s['biopsied']} · Frozen {s['frozen']} · Transferred {s['transferred']}", 9.5)
    y -= 6 * mm
    for e in ws["observation"]["table"]:
        if not e.get("embryo_code"):
            continue
        days = "  ".join(f"D{d}:{v.get('grade') or ''}" for d, v in sorted(e["days"].items(), key=lambda kv: int(kv[0])))
        fate = e.get("disposition") or ""
        pg = f" PGT-A {e['pgta']}" if e.get("pgta") else ""
        _line(pdf, L, y, f"{e['embryo_code']}  {days}  → {fate}{pg}", 8.5)
        y -= 4.3 * mm
        if y < 40 * mm:
            pdf.showPage(); y = h - 20 * mm
    y -= 3 * mm

    # Outcome
    o = ws.get("outcome")
    _line(pdf, L, y, "Outcome / ผลการรักษา", 11, True, RUBY); y -= 5.5 * mm
    if o:
        txt = (f"hCG {o.get('hcg_date') or ''} {to_json(o.get('hcg_value')) or ''} → {'positive' if o.get('hcg_positive') else ('negative' if o.get('hcg_positive') is False else 'pending')}"
               f" · Clinical pregnancy {o.get('clinical_pregnancy')} · Sacs {o.get('gestational_sacs') or ''} · FH {o.get('fetal_hearts') or ''}"
               f" · Ongoing {o.get('ongoing_pregnancy')} · Live birth {o.get('live_birth')}")
        _line(pdf, L, y, txt, 9.5)
    else:
        _line(pdf, L, y, "Pending / รอผล", 9.5, False, GRAY)
    y -= 10 * mm
    _line(pdf, L, y, "Success rates vary with age and individual medical factors. This report summarises this cycle only.", 8, False, GRAY)
    y -= 4 * mm
    _line(pdf, L, y, "อัตราความสำเร็จขึ้นกับอายุและปัจจัยทางการแพทย์ของแต่ละบุคคล รายงานนี้สรุปเฉพาะรอบการรักษานี้", 8, False, GRAY)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()
