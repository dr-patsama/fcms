/**
 * FCMS Module 6 — CRM Dashboard / แดชบอร์ด CRM
 * Tabs: Dashboard, Appointments, Virtual Consultations, Reminders, Communications, Schedule
 * Design: Cloud font, Ruby #E0115F sidebar, Sapphire Deep headers
 * Fully bilingual (EN/TH) — No AI chatbot per clinic preference
 */

import React, { useState, useEffect, useCallback } from 'react';

const API = '/api/v1/crm';

const C = {
  sapphire: '#0F52BA', sapphireDeep: '#151667', sapphireLight: '#4A7FD4', sapphireMuted: '#E8EEFA',
  emerald: '#009473', emeraldVivid: '#50C878', emeraldDark: '#006B54', emeraldMuted: '#E0F5EF',
  ruby: '#E0115F', rubyDark: '#A00040', rubyMuted: '#FCE4EE',
  amber: '#F59E0B', amberMuted: '#FEF3C7', gold: '#C5A044',
  gray900: '#111827', gray500: '#6B7280', gray200: '#E5E7EB', gray50: '#F9FAFB', white: '#FFFFFF',
};

const T = {
  dashboard:       { en: 'Dashboard',            th: 'แดชบอร์ด' },
  appointments:    { en: 'Appointments',          th: 'นัดหมาย' },
  virtualConsult:  { en: 'Virtual Consultation',  th: 'ปรึกษาทางไกล' },
  reminders:       { en: 'Reminders',             th: 'แจ้งเตือน' },
  communications:  { en: 'Communications',        th: 'การสื่อสาร' },
  schedule:        { en: 'Schedule',              th: 'ตารางเวลา' },
  search:          { en: 'Search',                th: 'ค้นหา' },
  newAppt:         { en: 'New Appointment',        th: 'นัดหมายใหม่' },
  bookingNum:      { en: 'Booking #',             th: 'เลขนัดหมาย' },
  patient:         { en: 'Patient',               th: 'ผู้ป่วย' },
  date:            { en: 'Date',                  th: 'วันที่' },
  time:            { en: 'Time',                  th: 'เวลา' },
  type:            { en: 'Type',                  th: 'ประเภท' },
  provider:        { en: 'Provider',              th: 'แพทย์' },
  status:          { en: 'Status',                th: 'สถานะ' },
  source:          { en: 'Source',                th: 'ช่องทาง' },
  channel:         { en: 'Channel',               th: 'ช่องทาง' },
  todayAppts:      { en: "Today's Appts",         th: 'นัดวันนี้' },
  tomorrowAppts:   { en: 'Tomorrow',              th: 'พรุ่งนี้' },
  checkedIn:       { en: 'Checked In',            th: 'เช็คอินแล้ว' },
  waitingVC:       { en: 'Waiting VC',            th: 'รอปรึกษาทางไกล' },
  pendingReminders:{ en: 'Pending Reminders',     th: 'แจ้งเตือนรอส่ง' },
  noShows:         { en: 'No Shows (7d)',          th: 'ไม่มา (7 วัน)' },
  actions:         { en: 'Actions',               th: 'การดำเนินการ' },
};
const bi = (key) => T[key] ? `${T[key].en} / ${T[key].th}` : key;

const APPT_TYPE_LABELS = {
  new_patient: 'New Patient / ผู้ป่วยใหม่', follow_up: 'Follow Up / ติดตามผล',
  consultation: 'Consultation / ปรึกษา', ultrasound: 'Ultrasound / อัลตราซาวด์',
  blood_test: 'Blood Test / ตรวจเลือด', egg_collection: 'OPU / เจาะไข่',
  embryo_transfer: 'ET / ย้ายตัวอ่อน', iui: 'IUI / ฉีดอสุจิ',
  virtual_consultation: 'Virtual Consult / ปรึกษาทางไกล',
  hysteroscopy: 'Hysteroscopy / ส่องกล้อง', prp: 'PRP', procedure: 'Procedure / หัตถการ',
  semen_analysis: 'Semen Analysis / ตรวจอสุจิ', other: 'Other / อื่นๆ',
};
const SOURCE_LABELS = {
  staff: 'Staff / เจ้าหน้าที่', online: 'Online / ออนไลน์', phone: 'Phone / โทรศัพท์',
  line: 'LINE / ไลน์', whatsapp: 'WhatsApp', walk_in: 'Walk-in / เข้ามาเอง',
};
const CHANNEL_LABELS = {
  sms: 'SMS', line: 'LINE / ไลน์', email: 'Email / อีเมล',
  whatsapp: 'WhatsApp / วอทส์แอป', phone_call: 'Phone / โทรศัพท์',
};

// ── Shared Components ────────────────────────────────────
function StatCard({ label, labelTh, value, sub, color }) {
  return (
    <div style={{ background: C.white, borderRadius: 10, padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      borderLeft: `4px solid ${color}`, flex: 1, minWidth: 160 }}>
      <div style={{ fontSize: 13, color: C.gray500 }}>{label}</div>
      <div style={{ fontSize: 12, color: C.gray500, marginBottom: 8 }}>{labelTh}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: C.gray900 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}
function Badge({ text, color, bg }) {
  return <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 12, fontSize: 12,
    fontWeight: 600, color, background: bg }}>{text}</span>;
}
function StatusBadge({ status }) {
  const m = {
    scheduled: { t: 'Scheduled / นัดแล้ว', c: C.sapphire, b: C.sapphireMuted },
    confirmed: { t: 'Confirmed / ยืนยัน', c: C.emeraldDark, b: C.emeraldMuted },
    checked_in: { t: 'Checked In / เช็คอิน', c: C.emerald, b: C.emeraldMuted },
    in_progress: { t: 'In Progress / กำลังดำเนิน', c: C.amber, b: C.amberMuted },
    completed: { t: 'Completed / เสร็จ', c: C.emeraldDark, b: C.emeraldMuted },
    no_show: { t: 'No Show / ไม่มา', c: C.rubyDark, b: C.rubyMuted },
    cancelled: { t: 'Cancelled / ยกเลิก', c: C.gray500, b: C.gray200 },
    rescheduled: { t: 'Rescheduled / เลื่อน', c: C.amber, b: C.amberMuted },
    pending: { t: 'Pending / รอ', c: C.amber, b: C.amberMuted },
    sent: { t: 'Sent / ส่งแล้ว', c: C.emeraldDark, b: C.emeraldMuted },
    delivered: { t: 'Delivered / ส่งถึง', c: C.emeraldDark, b: C.emeraldMuted },
    failed: { t: 'Failed / ล้มเหลว', c: C.rubyDark, b: C.rubyMuted },
    waiting: { t: 'Waiting / รอ', c: C.amber, b: C.amberMuted },
  };
  const s = m[status] || { t: status, c: C.gray500, b: C.gray200 };
  return <Badge text={s.t} color={s.c} bg={s.b} />;
}
const thStyle = { padding: '10px 14px', textAlign: 'left', fontSize: 12, fontWeight: 600,
  color: C.white, background: C.sapphireDeep, whiteSpace: 'nowrap' };
const tdStyle = { padding: '10px 14px', fontSize: 13, borderBottom: `1px solid ${C.gray200}` };
function Btn({ children, onClick, color = C.sapphire, outline = false, small = false, disabled = false }) {
  return <button onClick={onClick} disabled={disabled} style={{ padding: small ? '4px 12px' : '8px 20px',
    borderRadius: 6, border: outline ? `1px solid ${color}` : 'none',
    background: outline ? 'transparent' : disabled ? C.gray200 : color,
    color: outline ? color : C.white, fontSize: small ? 12 : 14, fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1 }}>{children}</button>;
}

// ══════════════════════════════════════════════════════════
function DashboardTab() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch(`${API}/dashboard`).then(r => r.json()).then(setData).catch(() => setData({
      today_appointments: 0, tomorrow_appointments: 0, checked_in_today: 0,
      waiting_virtual: 0, pending_reminders: 0, no_shows_7d: 0,
      today_by_type: [], monthly_by_source: [],
    }));
  }, []);
  if (!data) return <div style={{ padding: 40, color: C.gray500 }}>Loading... / กำลังโหลด...</div>;
  return (
    <div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard label="Today's Appts" labelTh="นัดหมายวันนี้" value={data.today_appointments} color={C.sapphire} />
        <StatCard label="Tomorrow" labelTh="พรุ่งนี้" value={data.tomorrow_appointments} color={C.sapphireLight} />
        <StatCard label="Checked In" labelTh="เช็คอินแล้ว" value={data.checked_in_today} color={C.emerald} />
        <StatCard label="Waiting VC" labelTh="รอปรึกษาทางไกล" value={data.waiting_virtual} color={C.gold} />
      </div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard label="Pending Reminders" labelTh="แจ้งเตือนรอส่ง" value={data.pending_reminders} color={C.amber} />
        <StatCard label="No Shows (7d)" labelTh="ไม่มา (7 วัน)" value={data.no_shows_7d} color={C.ruby} />
      </div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {data.today_by_type.length > 0 && (
          <div style={{ background: C.white, borderRadius: 10, padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', flex: 1, minWidth: 300 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: C.gray900, marginBottom: 12 }}>Today by Type / ประเภทวันนี้</h3>
            {data.today_by_type.map((t, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${C.gray200}` }}>
                <span style={{ fontSize: 13 }}>{APPT_TYPE_LABELS[t.type] || t.type}</span>
                <span style={{ fontWeight: 700, color: C.sapphire }}>{t.count}</span>
              </div>
            ))}
          </div>
        )}
        {data.monthly_by_source.length > 0 && (
          <div style={{ background: C.white, borderRadius: 10, padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', flex: 1, minWidth: 300 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: C.gray900, marginBottom: 12 }}>Monthly by Source / ช่องทาง 30 วัน</h3>
            {data.monthly_by_source.map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${C.gray200}` }}>
                <span style={{ fontSize: 13 }}>{SOURCE_LABELS[s.source] || s.source}</span>
                <span style={{ fontWeight: 700, color: C.emerald }}>{s.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
function AppointmentsTab() {
  const [appts, setAppts] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  useEffect(() => {
    const p = new URLSearchParams({ page, per_page: 20 });
    if (statusFilter) p.set('status', statusFilter);
    if (typeFilter) p.set('appointment_type', typeFilter);
    fetch(`${API}/appointments?${p}`).then(r => r.json()).then(d => {
      setAppts(d.appointments || []); setTotalPages(d.total_pages || 1);
    }).catch(() => setAppts([]));
  }, [statusFilter, typeFilter, page]);
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Status / ทุกสถานะ</option>
          {['scheduled','confirmed','checked_in','in_progress','completed','no_show','cancelled'].map(s =>
            <option key={s} value={s}>{s}</option>
          )}
        </select>
        <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Types / ทุกประเภท</option>
          {Object.entries(APPT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <Btn>{bi('newAppt')}</Btn>
      </div>
      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead><tr>
            <th style={thStyle}>{bi('bookingNum')}</th>
            <th style={thStyle}>{bi('date')}</th>
            <th style={thStyle}>{bi('time')}</th>
            <th style={thStyle}>{bi('type')}</th>
            <th style={thStyle}>{bi('source')}</th>
            <th style={thStyle}>{bi('status')}</th>
          </tr></thead>
          <tbody>
            {appts.length === 0 ? (
              <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No appointments found / ไม่พบนัดหมาย
              </td></tr>
            ) : appts.map((a, i) => (
              <tr key={a.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: C.sapphire }}>{a.booking_number}</td>
                <td style={tdStyle}>{a.appointment_date}</td>
                <td style={tdStyle}>{a.appointment_time}</td>
                <td style={tdStyle}>{APPT_TYPE_LABELS[a.appointment_type] || a.appointment_type}</td>
                <td style={tdStyle}>{SOURCE_LABELS[a.booking_source] || a.booking_source}</td>
                <td style={tdStyle}><StatusBadge status={a.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <Btn small outline disabled={page <= 1} onClick={() => setPage(p => p - 1)}>←</Btn>
          <span style={{ padding: '4px 12px', fontSize: 13, color: C.gray500 }}>{page} / {totalPages}</span>
          <Btn small outline disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</Btn>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
function ConsultationsTab() {
  const [vcs, setVcs] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  useEffect(() => {
    const p = new URLSearchParams({ per_page: 20 });
    if (statusFilter) p.set('status', statusFilter);
    fetch(`${API}/consultations?${p}`).then(r => r.json()).then(d => setVcs(d.consultations || [])).catch(() => setVcs([]));
  }, [statusFilter]);
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Status / ทุกสถานะ</option>
          {['scheduled','waiting','in_progress','completed','cancelled','no_show'].map(s =>
            <option key={s} value={s}>{s}</option>
          )}
        </select>
      </div>
      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead><tr>
            <th style={thStyle}>Platform</th>
            <th style={thStyle}>Scheduled / เวลา</th>
            <th style={thStyle}>Duration / ระยะเวลา</th>
            <th style={thStyle}>{bi('status')}</th>
          </tr></thead>
          <tbody>
            {vcs.length === 0 ? (
              <tr><td colSpan={4} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No virtual consultations / ไม่มีเซสชันปรึกษาทางไกล
              </td></tr>
            ) : vcs.map((vc, i) => (
              <tr key={vc.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{vc.platform}</td>
                <td style={tdStyle}>{vc.scheduled_start ? new Date(vc.scheduled_start).toLocaleString('th-TH') : '—'}</td>
                <td style={tdStyle}>{vc.duration_minutes ? `${vc.duration_minutes} min` : '—'}</td>
                <td style={tdStyle}><StatusBadge status={vc.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
function RemindersTab() {
  const [reminders, setReminders] = useState([]);
  const [channelFilter, setChannelFilter] = useState('');
  useEffect(() => {
    const p = new URLSearchParams({ hours_ahead: 48 });
    if (channelFilter) p.set('channel', channelFilter);
    fetch(`${API}/reminders/pending?${p}`).then(r => r.json()).then(d => setReminders(d.reminders || [])).catch(() => setReminders([]));
  }, [channelFilter]);
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <select value={channelFilter} onChange={e => setChannelFilter(e.target.value)}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Channels / ทุกช่องทาง</option>
          {Object.entries(CHANNEL_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>
      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead><tr>
            <th style={thStyle}>{bi('channel')}</th>
            <th style={thStyle}>Scheduled / กำหนดส่ง</th>
            <th style={thStyle}>Template</th>
            <th style={thStyle}>{bi('status')}</th>
          </tr></thead>
          <tbody>
            {reminders.length === 0 ? (
              <tr><td colSpan={4} style={{ ...tdStyle, textAlign: 'center', color: C.emerald, padding: 40 }}>
                No pending reminders / ไม่มีแจ้งเตือนรอส่ง ✓
              </td></tr>
            ) : reminders.map((r, i) => (
              <tr key={r.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{CHANNEL_LABELS[r.channel] || r.channel}</td>
                <td style={tdStyle}>{r.scheduled_at ? new Date(r.scheduled_at).toLocaleString('th-TH') : '—'}</td>
                <td style={tdStyle}>{r.template_key || '—'}</td>
                <td style={tdStyle}><StatusBadge status="pending" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
function CommunicationsTab() {
  const [logs, setLogs] = useState([]);
  const [channelFilter, setChannelFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  useEffect(() => {
    const p = new URLSearchParams({ page, per_page: 20 });
    if (channelFilter) p.set('channel', channelFilter);
    fetch(`${API}/communications?${p}`).then(r => r.json()).then(d => {
      setLogs(d.communications || []); setTotalPages(d.total_pages || 1);
    }).catch(() => setLogs([]));
  }, [channelFilter, page]);
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <select value={channelFilter} onChange={e => { setChannelFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Channels / ทุกช่องทาง</option>
          {Object.entries(CHANNEL_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <Btn>Send Message / ส่งข้อความ</Btn>
      </div>
      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead><tr>
            <th style={thStyle}>{bi('channel')}</th>
            <th style={thStyle}>Subject / หัวข้อ</th>
            <th style={thStyle}>Template</th>
            <th style={thStyle}>{bi('status')}</th>
            <th style={thStyle}>{bi('date')}</th>
          </tr></thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No communications / ไม่มีบันทึกการสื่อสาร
              </td></tr>
            ) : logs.map((l, i) => (
              <tr key={l.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{CHANNEL_LABELS[l.channel] || l.channel}</td>
                <td style={tdStyle}>{l.subject || l.message_th || '—'}</td>
                <td style={tdStyle}>{l.template_key || '—'}</td>
                <td style={tdStyle}><StatusBadge status={l.status} /></td>
                <td style={{ ...tdStyle, fontSize: 12, color: C.gray500 }}>
                  {l.created_at ? new Date(l.created_at).toLocaleString('th-TH') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <Btn small outline disabled={page <= 1} onClick={() => setPage(p => p - 1)}>←</Btn>
          <span style={{ padding: '4px 12px', fontSize: 13, color: C.gray500 }}>{page} / {totalPages}</span>
          <Btn small outline disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</Btn>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
function ScheduleTab() {
  return (
    <div style={{ background: C.white, borderRadius: 10, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
      <h3 style={{ fontSize: 18, fontWeight: 700, color: C.gray900, marginBottom: 8 }}>
        Provider Schedule / ตารางแพทย์
      </h3>
      <p style={{ color: C.gray500, fontSize: 14, marginBottom: 24 }}>
        Manage weekly schedules, time slots, and day-off exceptions for providers.
        <br />จัดการตารางเวลาประจำสัปดาห์ ช่วงเวลา และวันหยุดของแพทย์
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <Btn>Add Schedule Slot / เพิ่มตาราง</Btn>
        <Btn outline>Add Day Off / เพิ่มวันหยุด</Btn>
      </div>
      <div style={{ marginTop: 24, padding: 20, background: C.sapphireMuted, borderRadius: 8, color: C.sapphireDeep, fontSize: 13 }}>
        <strong>Available Slot Finder / ค้นหาเวลาว่าง</strong>
        <br />Use the API endpoint <code>/api/v1/crm/schedule/available-slots</code> to check real-time slot availability per provider and date.
        <br />ใช้ endpoint สำหรับตรวจสอบเวลาว่างของแพทย์แต่ละท่านตามวันที่
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
const TABS = [
  { key: 'dashboard',      label: T.dashboard },
  { key: 'appointments',   label: T.appointments },
  { key: 'consultations',  label: T.virtualConsult },
  { key: 'reminders',      label: T.reminders },
  { key: 'communications', label: T.communications },
  { key: 'schedule',       label: T.schedule },
];

export default function CRMDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const content = {
    dashboard: <DashboardTab />, appointments: <AppointmentsTab />,
    consultations: <ConsultationsTab />, reminders: <RemindersTab />,
    communications: <CommunicationsTab />, schedule: <ScheduleTab />,
  };
  return (
    <div style={{ fontFamily: "'Cloud', sans-serif", background: C.gray50, minHeight: '100vh' }}>
      <div style={{ background: C.sapphireDeep, color: C.white, padding: '20px 32px', display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ fontSize: 24, fontWeight: 700 }}>CRM / ระบบบริหารลูกค้าสัมพันธ์</div>
        <div style={{ fontSize: 13, opacity: 0.7, marginLeft: 'auto' }}>Life by Dr. Pat — FCMS Module 6</div>
      </div>
      <div style={{ background: C.white, borderBottom: `2px solid ${C.gray200}`, display: 'flex', gap: 0, overflowX: 'auto', padding: '0 24px' }}>
        {TABS.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            padding: '14px 20px', border: 'none', background: 'none', cursor: 'pointer',
            fontSize: 14, fontWeight: activeTab === tab.key ? 700 : 400,
            color: activeTab === tab.key ? C.sapphire : C.gray500,
            borderBottom: activeTab === tab.key ? `3px solid ${C.sapphire}` : '3px solid transparent',
            whiteSpace: 'nowrap',
          }}>
            <span>{tab.label.en}</span>
            <span style={{ fontSize: 11, marginLeft: 4, opacity: 0.7 }}>{tab.label.th}</span>
          </button>
        ))}
      </div>
      <div style={{ padding: '24px 32px' }}>{content[activeTab]}</div>
    </div>
  );
}
