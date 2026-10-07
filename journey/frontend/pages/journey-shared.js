/* FCMS Journey — shared helpers & components (loaded as text/babel before each page) */
const { useState, useEffect, useMemo, useRef, useCallback } = React;

// ── auth / api ───────────────────────────────────────────────────────────────
const TOKEN = () => sessionStorage.getItem('fcms_token');
const USER = () => { try { return JSON.parse(sessionStorage.getItem('fcms_user') || '{}'); } catch (e) { return {}; } };
function requireLogin() { if (!TOKEN()) { location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search); } }

async function api(path, opts = {}) {
  const headers = Object.assign({ Authorization: 'Bearer ' + TOKEN() }, opts.headers || {});
  let body = opts.body;
  if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  const r = await fetch(path, { method: opts.method || (body ? 'POST' : 'GET'), headers, body });
  if (r.status === 401) { sessionStorage.clear(); requireLogin(); throw new Error('Session expired'); }
  const ct = r.headers.get('content-type') || '';
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = j.detail ? (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)) : JSON.stringify(j); } catch (e) {}
    throw new Error(msg);
  }
  if (ct.includes('application/json')) return r.json();
  return r.blob();
}
function openBlob(blob) { const u = URL.createObjectURL(blob); window.open(u, '_blank'); }

// ── i18n ─────────────────────────────────────────────────────────────────────
const LANG_KEY = 'fcms_lang';
function useLang() {
  const [lang, setLang] = useState(localStorage.getItem(LANG_KEY) || 'th');
  const set = (l) => { localStorage.setItem(LANG_KEY, l); setLang(l); };
  return [lang, set];
}
const DICT = {
  // generic
  'Dashboard': 'หน้าหลัก', 'Cycles': 'รอบการรักษา', 'Lab To-Do': 'งานห้องแล็บ', 'Witness': 'พยานอิเล็กทรอนิกส์', 'Front desk': 'หน้าเคาน์เตอร์',
  'Packages': 'แพ็กเกจการรักษา', 'Insight': 'สถิติ KPI', 'Patient app': 'แอปผู้ป่วย', 'Sign out': 'ออกจากระบบ', 'Search': 'ค้นหา',
  'New cycle': 'สร้างรอบใหม่', 'Patient': 'ผู้ป่วย', 'Partner': 'คู่สมรส', 'Package': 'แพ็กเกจ', 'Physician': 'แพทย์', 'Status': 'สถานะ',
  'Medication start': 'วันเริ่มยา', 'Create': 'สร้าง', 'Cancel': 'ยกเลิก', 'Save': 'บันทึก', 'Close': 'ปิด', 'Date': 'วันที่', 'Time': 'เวลา',
  'Overview': 'ภาพรวม', 'Stimulation chart': 'ตารางยากระตุ้น', 'Monitoring': 'ติดตามผล', 'Schedule & tasks': 'นัดหมายและงานแล็บ',
  'Observation': 'ไข่/ตัวอ่อน', 'Consents': 'เอกสารยินยอม', 'Outcome': 'ผลการรักษา', 'Events': 'ประวัติเหตุการณ์',
  'Publish plan': 'เผยแพร่แผนให้ผู้ป่วย', 'Set trigger': 'กำหนดเวลา trigger', 'Schedule procedure': 'นัดหัตถการ', 'Print labels': 'พิมพ์ฉลาก',
  'Cycle report': 'รายงานรอบการรักษา', 'Add medication': 'เพิ่มยา', 'Drug': 'ยา', 'Dose': 'ขนาด', 'Unit': 'หน่วย', 'Route': 'วิธีให้', 'Slot': 'เวลา',
  'From day': 'จากวันที่', 'To day': 'ถึงวันที่', 'Add': 'เพิ่ม', 'Delete': 'ลบ', 'Taken': 'ใช้ยาแล้ว', 'Pending': 'รอดำเนินการ', 'Done': 'เสร็จ',
  'Failed': 'ไม่สำเร็จ', 'Blocked': 'รอเอกสารยินยอม', 'Sign': 'ลงนาม', 'Signed': 'ลงนามแล้ว', 'PDF': 'PDF', 'Release to patient': 'เผยแพร่ให้ผู้ป่วย',
  'Released': 'เผยแพร่แล้ว', 'Upload photo': 'อัปโหลดรูป', 'Follicles right': 'ฟอลลิเคิลขวา (มม.)', 'Follicles left': 'ฟอลลิเคิลซ้าย (มม.)',
  'Endometrium': 'เยื่อบุโพรงมดลูก (มม.)', 'Decision': 'การตัดสินใจ', 'Record': 'บันทึก', 'Procedure date (D0)': 'วันหัตถการ (D0)', 'Room': 'ห้อง',
  'Physician order': 'คำสั่งแพทย์', 'Trigger time': 'เวลาฉีด trigger', 'Suggested OPU': 'เวลาเก็บไข่ที่แนะนำ', 'Today': 'วันนี้', 'All': 'ทั้งหมด',
  'Start witness': 'เริ่มพยาน', 'Manual double-witness': 'พยานบุคคลที่สอง', 'Scan record': 'ประวัติการสแกน', 'Incidents': 'เหตุการณ์ผิดพลาด',
  'Oocytes retrieved': 'ไข่ที่เก็บได้', 'Follicles aspirated': 'ฟอลลิเคิลที่เจาะ', 'Fertilisation': 'การปฏิสนธิ', 'Embryos': 'ตัวอ่อน', 'Blastocysts': 'บลาสโตซิสต์',
  'Frozen': 'แช่แข็ง', 'Transferred': 'ย้ายแล้ว', 'Summary': 'สรุป', 'Album': 'อัลบั้ม', 'Cryo': 'แช่แข็ง', 'Freeze': 'แช่แข็ง', 'Transfer': 'ย้ายตัวอ่อน',
  'Grade': 'เกรด', 'Cells': 'จำนวนเซลล์', 'Fragmentation %': 'เศษเซลล์ %', 'Expansion': 'การขยาย', 'ICM': 'ICM', 'TE': 'TE', 'Disposition': 'การจัดการ',
  'hCG date': 'วันตรวจ hCG', 'hCG value': 'ค่า hCG', 'Positive': 'บวก', 'Negative': 'ลบ', 'Clinical pregnancy': 'ตั้งครรภ์ทางคลินิก', 'Fetal hearts': 'หัวใจทารก',
  'Ongoing pregnancy': 'ตั้งครรภ์ต่อเนื่อง', 'Live birth': 'คลอดมีชีวิต', 'Miscarriage': 'แท้ง', 'Ectopic': 'ท้องนอกมดลูก', 'OHSS': 'OHSS',
  'Cancelled before OPU': 'ยกเลิกก่อนเก็บไข่', 'Notes': 'หมายเหตุ', 'Queue': 'คิว', 'Call': 'เรียกคิว', 'Check-in': 'เช็คอิน', 'Booking requests': 'คำขอนัดหมาย',
  'Confirm': 'ยืนยัน', 'Decline': 'ปฏิเสธ', 'Cryo renewals due': 'ครบกำหนดต่ออายุแช่แข็ง', 'Renew': 'ต่ออายุ', 'Connections': 'การเชื่อมต่อ',
  'Broadcast': 'ประกาศถึงผู้ป่วย', 'Send': 'ส่ง', 'Laboratory': 'ห้องปฏิบัติการ', 'Clinical': 'คลินิก', 'Operational': 'การปฏิบัติงาน', 'Export Excel': 'ส่งออก Excel',
};
function tr(lang, s) { return lang === 'th' ? (DICT[s] || s) : s; }

// ── formatting ───────────────────────────────────────────────────────────────
const TH_MONTHS = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
function fmtDate(s, lang = 'en') {
  if (!s) return '—';
  const d = new Date(s.length === 10 ? s + 'T00:00:00' : s);
  if (isNaN(d)) return s;
  if (lang === 'th') return `${d.getDate()} ${TH_MONTHS[d.getMonth()]} ${d.getFullYear() + 543}`;
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}
function fmtDT(s, lang = 'en') { if (!s) return '—'; const d = new Date(s); return fmtDate(s, lang) + ' ' + d.toTimeString().slice(0, 5); }
const todayISO = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const addDays = (iso, n) => { const d = new Date(iso + 'T00:00:00'); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const nameOf = (o, lang) => lang === 'th' ? (o.patient_th || o.name_th || o.patient_en || o.name_en) : (o.patient_en || o.name_en || o.patient_th);

// ── components ───────────────────────────────────────────────────────────────
function Shell({ active, lang, setLang, title, actions, children }) {
  const u = USER();
  const nav = [
    ['sec', 'Clinic'], ['/dashboard', 'Dashboard', '⌂'], ['/cycles', 'Cycles', '◎'], ['/desk', 'Front desk', '☰'],
    ['sec', 'Laboratory'], ['/lab/todo', 'Lab To-Do', '✓'], ['/lab/witness', 'Witness', '▣'], ['/board/embryo', 'Embryo board', '▤'],
    ['sec', 'Management'], ['/insight', 'Insight', '▲'], ['/admin/packages', 'Packages', '⚙'], ['/portal', 'Patient app', '☺'],
  ];
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">LIFE by Dr. Pat<small>Fertility Clinic Management · life 360</small></div>
        <nav>{nav.map((n, i) => n[0] === 'sec' ? <div key={i} className="sec">{n[1]}</div> :
          <a key={i} href={n[0]} className={active === n[0] ? 'active' : ''}><span>{n[2]}</span>{tr(lang, n[1])}</a>)}</nav>
        <div className="foot">{u.first_name_th || u.first_name_en || u.email} · {u.role}
          <div className="lang" style={{ marginTop: 8 }}><button className={lang === 'th' ? 'on' : ''} onClick={() => setLang('th')}>ไทย</button><button className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')}>EN</button></div>
          <button className="btn gold sm block" onClick={() => { sessionStorage.clear(); location.href = '/login'; }}>{tr(lang, 'Sign out')}</button>
        </div>
      </aside>
      <main className="main">
        <div className="topbar"><h1>{title}</h1><div className="spacer" />{actions}</div>
        {children}
      </main>
    </div>
  );
}
function Toast({ msg }) { return msg ? <div className={'toast' + (msg.err ? ' err' : '')}>{msg.text}</div> : null; }
function useToast() {
  const [msg, setMsg] = useState(null);
  const show = (text, err = false) => { setMsg({ text, err }); setTimeout(() => setMsg(null), err ? 6000 : 3000); };
  return [msg, show];
}
function Modal({ title, onClose, children, wide }) {
  return <div className="modal-bg" onClick={onClose}><div className="modal" style={wide ? { width: 'min(1100px,100%)' } : {}} onClick={e => e.stopPropagation()}>
    <div className="flex"><h3 style={{ flex: 1 }}>{title}</h3><button className="btn ghost xs" onClick={onClose}>✕</button></div>{children}</div></div>;
}
function Pill({ s, children }) { return <span className={'pill ' + (s || 'gray')}>{children !== undefined && children !== null ? children : s}</span>; }
function Field({ label, children }) { return <label className="f"><span>{label}</span>{children}</label>; }
function Stat({ label, value, small, ink }) { return <div className={'card stat' + (ink ? ' ink' : '')}><div className="label">{label}</div><b>{value ?? '—'}</b>{small && <small>{small}</small>}</div>; }

/* Signature canvas (mouse + touch) → data URL */
function SignaturePad({ onChange }) {
  const ref = useRef(null); const drawing = useRef(false);
  useEffect(() => { const c = ref.current; c.width = c.offsetWidth * 2; c.height = c.offsetHeight * 2; const ctx = c.getContext('2d'); ctx.scale(2, 2); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#151667'; }, []);
  const pos = (e) => { const r = ref.current.getBoundingClientRect(); const p = e.touches ? e.touches[0] : e; return [p.clientX - r.left, p.clientY - r.top]; };
  const start = (e) => { drawing.current = true; const ctx = ref.current.getContext('2d'); const [x, y] = pos(e); ctx.beginPath(); ctx.moveTo(x, y); e.preventDefault(); };
  const move = (e) => { if (!drawing.current) return; const ctx = ref.current.getContext('2d'); const [x, y] = pos(e); ctx.lineTo(x, y); ctx.stroke(); e.preventDefault(); };
  const end = () => { if (!drawing.current) return; drawing.current = false; onChange(ref.current.toDataURL('image/png')); };
  const clear = () => { const c = ref.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); onChange(null); };
  return <div><canvas ref={ref} className="sig" onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end} onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
    <button className="btn ghost xs" style={{ marginTop: 6 }} onClick={clear}>Clear</button></div>;
}

/* Tiny SVG line chart */
function Spark({ data, color = '#0F52BA', max }) {
  const vals = data.map(v => (v == null ? null : +v));
  const m = max || Math.max(1, ...vals.filter(v => v != null));
  const w = 300, h = 70, n = Math.max(1, vals.length - 1);
  const pts = vals.map((v, i) => v == null ? null : [i / n * (w - 10) + 5, h - 8 - (v / m) * (h - 16)]).filter(Boolean);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  return <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"><path d={d} fill="none" stroke={color} strokeWidth="2.5" />
    {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="3" fill={color} />)}</svg>;
}
