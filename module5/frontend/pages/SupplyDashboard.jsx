/**
 * FCMS Module 5 — Medical Supply Dashboard / แดชบอร์ดเวชภัณฑ์
 * Tabs: Dashboard, Supply Catalogue, Stock, Requisitions, Suppliers, Usage, Alerts
 * Design: Cloud font, Ruby #E0115F sidebar, Sapphire Deep headers
 * Fully bilingual (EN/TH) throughout
 */

import React, { useState, useEffect, useCallback } from 'react';

const API = '/api/v1/supplies';

// ── Design Tokens ────────────────────────────────────────
const C = {
  sapphire:     '#0F52BA',
  sapphireDeep: '#151667',
  sapphireLight:'#4A7FD4',
  sapphireMuted:'#E8EEFA',
  emerald:      '#009473',
  emeraldVivid: '#50C878',
  emeraldDark:  '#006B54',
  emeraldMuted: '#E0F5EF',
  ruby:         '#E0115F',
  rubyDark:     '#A00040',
  rubyMuted:    '#FCE4EE',
  amber:        '#F59E0B',
  amberMuted:   '#FEF3C7',
  gold:         '#C5A044',
  gray900:      '#111827',
  gray500:      '#6B7280',
  gray200:      '#E5E7EB',
  gray50:       '#F9FAFB',
  white:        '#FFFFFF',
};

// ── Bilingual labels ────────────────────────────────────
const T = {
  dashboard:        { en: 'Dashboard',           th: 'แดชบอร์ด' },
  supplyCatalogue:  { en: 'Supply Catalogue',    th: 'รายการเวชภัณฑ์' },
  stock:            { en: 'Stock',               th: 'สต็อก' },
  requisitions:     { en: 'Requisitions',        th: 'ใบเบิก' },
  suppliers:        { en: 'Suppliers',           th: 'ผู้จำหน่าย' },
  usageLog:         { en: 'Usage Log',           th: 'บันทึกการใช้' },
  alerts:           { en: 'Alerts',              th: 'แจ้งเตือน' },
  search:           { en: 'Search',              th: 'ค้นหา' },
  addItem:          { en: 'Add Item',            th: 'เพิ่มรายการ' },
  addSupplier:      { en: 'Add Supplier',        th: 'เพิ่มผู้จำหน่าย' },
  receiveStock:     { en: 'Receive Stock',        th: 'รับสต็อกเข้า' },
  createReq:        { en: 'Create Requisition',   th: 'สร้างใบเบิก' },
  recordUsage:      { en: 'Record Usage',         th: 'บันทึกการใช้' },
  name:             { en: 'Name',                th: 'ชื่อ' },
  category:         { en: 'Category',            th: 'หมวดหมู่' },
  department:       { en: 'Department',          th: 'แผนก' },
  unit:             { en: 'Unit',                th: 'หน่วย' },
  currentStock:     { en: 'Current Stock',       th: 'คงคลัง' },
  status:           { en: 'Status',              th: 'สถานะ' },
  actions:          { en: 'Actions',             th: 'การดำเนินการ' },
  totalItems:       { en: 'Total Items',         th: 'รายการทั้งหมด' },
  totalSuppliers:   { en: 'Total Suppliers',     th: 'ผู้จำหน่ายทั้งหมด' },
  stockValue:       { en: 'Stock Value',         th: 'มูลค่าสต็อก' },
  pendingReqs:      { en: 'Pending Reqs',        th: 'ใบเบิกรอ' },
  lowStock:         { en: 'Low Stock',           th: 'สต็อกต่ำ' },
  outOfStock:       { en: 'Out of Stock',        th: 'หมดสต็อก' },
  ok:               { en: 'In Stock',            th: 'มีสต็อก' },
  expiring30d:      { en: 'Expiring ≤30d',      th: 'หมดอายุ ≤30 วัน' },
  pending:          { en: 'Pending',             th: 'รอดำเนินการ' },
  approved:         { en: 'Approved',            th: 'อนุมัติแล้ว' },
  issued:           { en: 'Issued',              th: 'จ่ายแล้ว' },
  rejected:         { en: 'Rejected',            th: 'ปฏิเสธ' },
  lotNumber:        { en: 'Lot',                 th: 'เลขล็อต' },
  expiryDate:       { en: 'Expiry',              th: 'วันหมดอายุ' },
  quantity:         { en: 'Qty',                 th: 'จำนวน' },
  daysLeft:         { en: 'Days Left',           th: 'เหลือ (วัน)' },
  valueAtRisk:      { en: 'Value at Risk',       th: 'มูลค่าเสี่ยง' },
  reqNumber:        { en: 'Req #',               th: 'เลขใบเบิก' },
  procedureType:    { en: 'Procedure',           th: 'หัตถการ' },
  supplier:         { en: 'Supplier',            th: 'ผู้จำหน่าย' },
  contactPerson:    { en: 'Contact',             th: 'ผู้ติดต่อ' },
  phone:            { en: 'Phone',               th: 'โทรศัพท์' },
  email:            { en: 'Email',               th: 'อีเมล' },
};
const bi = (key) => T[key] ? `${T[key].en} / ${T[key].th}` : key;

// ── Category / Department labels ─────────────────────────
const CAT_LABELS = {
  plasticware: { en: 'Plasticware', th: 'พลาสติกแวร์' },
  lab_media:   { en: 'Lab Media',   th: 'มีเดียแล็บ' },
  test_kit:    { en: 'Test Kit',    th: 'ชุดตรวจ' },
  cryostorage: { en: 'Cryostorage', th: 'วัสดุแช่แข็ง' },
  consumable:  { en: 'Consumable',  th: 'วัสดุสิ้นเปลือง' },
  ppe:         { en: 'PPE',         th: 'อุปกรณ์ป้องกัน' },
  cleaning:    { en: 'Cleaning',    th: 'ทำความสะอาด' },
  general:     { en: 'General',     th: 'ทั่วไป' },
};

const DEPT_LABELS = {
  embryology_lab: { en: 'Embryology Lab', th: 'แล็บตัวอ่อน' },
  andrology_lab:  { en: 'Andrology Lab',  th: 'แล็บอสุจิ' },
  general_lab:    { en: 'General Lab',     th: 'แล็บทั่วไป' },
  clinic:         { en: 'Clinic Room',     th: 'ห้องตรวจ' },
  operating_room: { en: 'Operating Room',  th: 'ห้องผ่าตัด' },
  all:            { en: 'All',             th: 'ทุกแผนก' },
};

const catLabel = (v) => CAT_LABELS[v] ? `${CAT_LABELS[v].en} / ${CAT_LABELS[v].th}` : v;
const deptLabel = (v) => DEPT_LABELS[v] ? `${DEPT_LABELS[v].en} / ${DEPT_LABELS[v].th}` : v;

// ══════════════════════════════════════════════════════════
// Shared Components
// ══════════════════════════════════════════════════════════

function StatCard({ label, labelTh, value, sub, color, icon }) {
  return (
    <div style={{
      background: C.white, borderRadius: 10, padding: '20px 24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)', borderLeft: `4px solid ${color}`,
      flex: 1, minWidth: 180,
    }}>
      <div style={{ fontSize: 13, color: C.gray500, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 12, color: C.gray500, marginBottom: 8 }}>{labelTh}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: C.gray900 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function Badge({ text, color, bg }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 12,
      fontSize: 12, fontWeight: 600, color, background: bg,
    }}>{text}</span>
  );
}

function StockBadge({ status }) {
  const m = {
    ok:           { text: bi('ok'),         color: C.emeraldDark,  bg: C.emeraldMuted },
    low:          { text: bi('lowStock'),    color: C.amber,        bg: C.amberMuted },
    out_of_stock: { text: bi('outOfStock'),  color: C.rubyDark,     bg: C.rubyMuted },
  };
  const s = m[status] || m.ok;
  return <Badge text={s.text} color={s.color} bg={s.bg} />;
}

function ReqStatusBadge({ status }) {
  const m = {
    pending:           { text: bi('pending'),   color: C.amber,       bg: C.amberMuted },
    approved:          { text: bi('approved'),  color: C.sapphire,    bg: C.sapphireMuted },
    issued:            { text: bi('issued'),    color: C.emeraldDark, bg: C.emeraldMuted },
    partially_issued:  { text: 'Partial / บางส่วน', color: C.sapphire, bg: C.sapphireMuted },
    rejected:          { text: bi('rejected'),  color: C.rubyDark,    bg: C.rubyMuted },
    cancelled:         { text: 'Cancelled / ยกเลิก', color: C.gray500, bg: C.gray200 },
  };
  const s = m[status] || m.pending;
  return <Badge text={s.text} color={s.color} bg={s.bg} />;
}

function SeverityBadge({ severity }) {
  const m = {
    expired:  { text: 'Expired / หมดอายุ',   color: C.white,      bg: C.rubyDark },
    critical: { text: 'Critical / วิกฤต',     color: C.rubyDark,   bg: C.rubyMuted },
    warning:  { text: 'Warning / เตือน',      color: C.amber,      bg: C.amberMuted },
    info:     { text: 'Info / ข้อมูล',         color: C.sapphire,   bg: C.sapphireMuted },
  };
  const s = m[severity] || m.info;
  return <Badge text={s.text} color={s.color} bg={s.bg} />;
}

const thStyle = {
  padding: '10px 14px', textAlign: 'left', fontSize: 12, fontWeight: 600,
  color: C.white, background: C.sapphireDeep, whiteSpace: 'nowrap',
};
const tdStyle = {
  padding: '10px 14px', fontSize: 13, borderBottom: `1px solid ${C.gray200}`,
};

function Btn({ children, onClick, color = C.sapphire, outline = false, small = false, disabled = false }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: small ? '4px 12px' : '8px 20px',
      borderRadius: 6, border: outline ? `1px solid ${color}` : 'none',
      background: outline ? 'transparent' : disabled ? C.gray200 : color,
      color: outline ? color : C.white,
      fontSize: small ? 12 : 14, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
    }}>{children}</button>
  );
}

// ══════════════════════════════════════════════════════════
// TAB: Dashboard
// ══════════════════════════════════════════════════════════

function DashboardTab() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/dashboard`).then(r => r.json()).then(setData).catch(() => {
      setData({
        total_items: 0, total_suppliers: 0, total_stock_value: 0,
        low_stock_items: 0, out_of_stock_items: 0, expiring_30d: 0,
        pending_requisitions: 0, approved_requisitions: 0, categories: [],
      });
    });
  }, []);

  if (!data) return <div style={{ padding: 40, color: C.gray500 }}>Loading... / กำลังโหลด...</div>;

  return (
    <div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard label="Total Items" labelTh="รายการทั้งหมด" value={data.total_items} color={C.sapphire} />
        <StatCard label="Suppliers" labelTh="ผู้จำหน่าย" value={data.total_suppliers} color={C.sapphireLight} />
        <StatCard label="Stock Value" labelTh="มูลค่าสต็อก"
          value={`฿${(data.total_stock_value || 0).toLocaleString('th-TH', { minimumFractionDigits: 0 })}`}
          color={C.emerald} />
        <StatCard label="Pending Reqs" labelTh="ใบเบิกรอ" value={data.pending_requisitions} color={C.amber} />
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard label="Low Stock" labelTh="สต็อกต่ำ" value={data.low_stock_items} color={C.amber}
          sub={`${data.out_of_stock_items} out of stock / หมดสต็อก`} />
        <StatCard label="Expiring ≤30d" labelTh="หมดอายุ ≤30 วัน" value={data.expiring_30d} color={C.ruby} />
        <StatCard label="Approved Reqs" labelTh="ใบเบิกอนุมัติ" value={data.approved_requisitions} color={C.sapphire} />
      </div>

      {data.categories && data.categories.length > 0 && (
        <div style={{ background: C.white, borderRadius: 10, padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: C.gray900, marginBottom: 16 }}>
            Stock by Category / สต็อกตามหมวดหมู่
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>Category / หมวดหมู่</th>
                <th style={thStyle}>Items / รายการ</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Value / มูลค่า</th>
              </tr>
            </thead>
            <tbody>
              {data.categories.map((c, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                  <td style={tdStyle}>{catLabel(c.category)}</td>
                  <td style={tdStyle}>{c.item_count}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>฿{(c.value || 0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// TAB: Supply Catalogue
// ══════════════════════════════════════════════════════════

function CatalogueTab() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const load = useCallback(() => {
    const params = new URLSearchParams({ page, per_page: 20 });
    if (search) params.set('search', search);
    if (catFilter) params.set('category', catFilter);
    fetch(`${API}/items?${params}`).then(r => r.json()).then(d => {
      setItems(d.items || []);
      setTotalPages(d.total_pages || 1);
    }).catch(() => setItems([]));
  }, [search, catFilter, page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder={bi('search')}
          value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={{
            padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`,
            fontSize: 14, flex: 1, minWidth: 200,
          }}
        />
        <select value={catFilter} onChange={e => { setCatFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Categories / ทุกหมวดหมู่</option>
          {Object.entries(CAT_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l.en} / {l.th}</option>
          ))}
        </select>
        <Btn>{bi('addItem')}</Btn>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead>
            <tr>
              <th style={thStyle}>{bi('name')}</th>
              <th style={thStyle}>{bi('category')}</th>
              <th style={thStyle}>{bi('department')}</th>
              <th style={thStyle}>{bi('unit')}</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>{bi('currentStock')}</th>
              <th style={thStyle}>{bi('status')}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No supplies found / ไม่พบเวชภัณฑ์
              </td></tr>
            ) : items.map((item, i) => (
              <tr key={item.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 600, color: C.gray900 }}>{item.name_en}</div>
                  {item.name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{item.name_th}</div>}
                  {item.sku && <div style={{ fontSize: 11, color: C.gray500 }}>SKU: {item.sku}</div>}
                </td>
                <td style={tdStyle}>{catLabel(item.category)}</td>
                <td style={tdStyle}>{deptLabel(item.department)}</td>
                <td style={tdStyle}>{item.unit}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>{item.current_stock}</td>
                <td style={tdStyle}><StockBadge status={item.stock_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <Btn small outline disabled={page <= 1} onClick={() => setPage(p => p - 1)}>←</Btn>
          <span style={{ padding: '4px 12px', fontSize: 13, color: C.gray500 }}>
            {page} / {totalPages}
          </span>
          <Btn small outline disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</Btn>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// TAB: Stock
// ══════════════════════════════════════════════════════════

function StockTab() {
  const [levels, setLevels] = useState([]);
  const [catFilter, setCatFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  useEffect(() => {
    const params = new URLSearchParams();
    if (catFilter) params.set('category', catFilter);
    if (deptFilter) params.set('department', deptFilter);
    fetch(`${API}/stock/levels?${params}`).then(r => r.json()).then(d => {
      setLevels(d.items || []);
    }).catch(() => setLevels([]));
  }, [catFilter, deptFilter]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={catFilter} onChange={e => setCatFilter(e.target.value)}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Categories / ทุกหมวดหมู่</option>
          {Object.entries(CAT_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l.en} / {l.th}</option>
          ))}
        </select>
        <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Departments / ทุกแผนก</option>
          {Object.entries(DEPT_LABELS).filter(([v]) => v !== 'all').map(([v, l]) => (
            <option key={v} value={v}>{l.en} / {l.th}</option>
          ))}
        </select>
        <Btn>{bi('receiveStock')}</Btn>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead>
            <tr>
              <th style={thStyle}>{bi('name')}</th>
              <th style={thStyle}>{bi('category')}</th>
              <th style={thStyle}>{bi('unit')}</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>{bi('currentStock')}</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Reorder Lvl / ระดับสั่งซื้อ</th>
              <th style={thStyle}>{bi('status')}</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Suggested Order / แนะนำสั่ง</th>
            </tr>
          </thead>
          <tbody>
            {levels.map((item, i) => (
              <tr key={item.id} style={{
                background: item.status === 'out_of_stock' ? C.rubyMuted
                           : item.status === 'low' ? C.amberMuted
                           : i % 2 === 0 ? C.white : C.gray50,
              }}>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 600 }}>{item.name_en}</div>
                  {item.name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{item.name_th}</div>}
                </td>
                <td style={tdStyle}>{catLabel(item.category)}</td>
                <td style={tdStyle}>{item.unit}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700 }}>{item.current_stock}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{item.reorder_level}</td>
                <td style={tdStyle}><StockBadge status={item.status} /></td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600,
                  color: item.suggested_order > 0 ? C.ruby : C.gray500,
                }}>
                  {item.suggested_order > 0 ? item.suggested_order : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// TAB: Requisitions
// ══════════════════════════════════════════════════════════

function RequisitionsTab() {
  const [reqs, setReqs] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const params = new URLSearchParams({ page, per_page: 20 });
    if (statusFilter) params.set('status', statusFilter);
    fetch(`${API}/requisitions?${params}`).then(r => r.json()).then(d => {
      setReqs(d.requisitions || []);
      setTotalPages(d.total_pages || 1);
    }).catch(() => setReqs([]));
  }, [statusFilter, page]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Status / ทุกสถานะ</option>
          <option value="pending">Pending / รอดำเนินการ</option>
          <option value="approved">Approved / อนุมัติแล้ว</option>
          <option value="issued">Issued / จ่ายแล้ว</option>
          <option value="partially_issued">Partial / บางส่วน</option>
          <option value="rejected">Rejected / ปฏิเสธ</option>
        </select>
        <Btn>{bi('createReq')}</Btn>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead>
            <tr>
              <th style={thStyle}>{bi('reqNumber')}</th>
              <th style={thStyle}>{bi('department')}</th>
              <th style={thStyle}>Items / รายการ</th>
              <th style={thStyle}>{bi('status')}</th>
              <th style={thStyle}>Date / วันที่</th>
            </tr>
          </thead>
          <tbody>
            {reqs.length === 0 ? (
              <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No requisitions found / ไม่พบใบเบิก
              </td></tr>
            ) : reqs.map((r, i) => (
              <tr key={r.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: C.sapphire }}>{r.req_number}</td>
                <td style={tdStyle}>{deptLabel(r.department)}</td>
                <td style={tdStyle}>{r.item_count}</td>
                <td style={tdStyle}><ReqStatusBadge status={r.status} /></td>
                <td style={{ ...tdStyle, fontSize: 12, color: C.gray500 }}>
                  {r.created_at ? new Date(r.created_at).toLocaleDateString('th-TH') : '—'}
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
// TAB: Suppliers
// ══════════════════════════════════════════════════════════

function SuppliersTab() {
  const [suppliers, setSuppliers] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const params = new URLSearchParams({ per_page: 50 });
    if (search) params.set('search', search);
    fetch(`${API}/suppliers?${params}`).then(r => r.json()).then(d => {
      setSuppliers(d.suppliers || []);
    }).catch(() => setSuppliers([]));
  }, [search]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <input
          placeholder={bi('search')}
          value={search} onChange={e => setSearch(e.target.value)}
          style={{
            padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`,
            fontSize: 14, flex: 1, minWidth: 200,
          }}
        />
        <Btn>{bi('addSupplier')}</Btn>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead>
            <tr>
              <th style={thStyle}>Code</th>
              <th style={thStyle}>{bi('name')}</th>
              <th style={thStyle}>{bi('contactPerson')}</th>
              <th style={thStyle}>{bi('phone')}</th>
              <th style={thStyle}>{bi('email')}</th>
              <th style={thStyle}>Terms</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.length === 0 ? (
              <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No suppliers found / ไม่พบผู้จำหน่าย
              </td></tr>
            ) : suppliers.map((s, i) => (
              <tr key={s.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: C.sapphire }}>{s.code || '—'}</td>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 600 }}>{s.name}</div>
                  {s.name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{s.name_th}</div>}
                </td>
                <td style={tdStyle}>{s.contact_person || '—'}</td>
                <td style={tdStyle}>{s.phone || '—'}</td>
                <td style={tdStyle}>{s.email || '—'}</td>
                <td style={tdStyle}>{s.payment_terms || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// TAB: Usage Log
// ══════════════════════════════════════════════════════════

function UsageTab() {
  const [logs, setLogs] = useState([]);
  const [deptFilter, setDeptFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const params = new URLSearchParams({ page, per_page: 20 });
    if (deptFilter) params.set('department', deptFilter);
    fetch(`${API}/usage?${params}`).then(r => r.json()).then(d => {
      setLogs(d.usage_logs || []);
      setTotalPages(d.total_pages || 1);
    }).catch(() => setLogs([]));
  }, [deptFilter, page]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <select value={deptFilter} onChange={e => { setDeptFilter(e.target.value); setPage(1); }}
          style={{ padding: '8px 14px', borderRadius: 6, border: `1px solid ${C.gray200}`, fontSize: 14 }}>
          <option value="">All Departments / ทุกแผนก</option>
          {Object.entries(DEPT_LABELS).filter(([v]) => v !== 'all').map(([v, l]) => (
            <option key={v} value={v}>{l.en} / {l.th}</option>
          ))}
        </select>
        <Btn>{bi('recordUsage')}</Btn>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
          <thead>
            <tr>
              <th style={thStyle}>Supply / เวชภัณฑ์</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>{bi('quantity')}</th>
              <th style={thStyle}>{bi('department')}</th>
              <th style={thStyle}>{bi('procedureType')}</th>
              <th style={thStyle}>Date / วันที่</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: C.gray500, padding: 40 }}>
                No usage records / ไม่พบบันทึกการใช้
              </td></tr>
            ) : logs.map((l, i) => (
              <tr key={l.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 600 }}>{l.supply_name_en}</div>
                  {l.supply_name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{l.supply_name_th}</div>}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>{l.quantity_used}</td>
                <td style={tdStyle}>{deptLabel(l.department)}</td>
                <td style={tdStyle}>{l.procedure_type || '—'}</td>
                <td style={{ ...tdStyle, fontSize: 12, color: C.gray500 }}>
                  {l.created_at ? new Date(l.created_at).toLocaleDateString('th-TH') : '—'}
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
// TAB: Alerts (Expiry + Low Stock)
// ══════════════════════════════════════════════════════════

function AlertsTab() {
  const [expiryAlerts, setExpiryAlerts] = useState([]);
  const [lowStockAlerts, setLowStockAlerts] = useState([]);
  const [subTab, setSubTab] = useState('expiry');

  useEffect(() => {
    fetch(`${API}/alerts/expiry?days=90`).then(r => r.json()).then(d => {
      setExpiryAlerts(d.alerts || []);
    }).catch(() => {});
    fetch(`${API}/alerts/low-stock`).then(r => r.json()).then(d => {
      setLowStockAlerts(d.alerts || []);
    }).catch(() => {});
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <Btn onClick={() => setSubTab('expiry')} outline={subTab !== 'expiry'} color={C.ruby}>
          Expiry Alerts / แจ้งเตือนหมดอายุ ({expiryAlerts.length})
        </Btn>
        <Btn onClick={() => setSubTab('lowstock')} outline={subTab !== 'lowstock'} color={C.amber}>
          Low Stock / สต็อกต่ำ ({lowStockAlerts.length})
        </Btn>
      </div>

      {subTab === 'expiry' && (
        <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
            <thead>
              <tr>
                <th style={thStyle}>Supply / เวชภัณฑ์</th>
                <th style={thStyle}>{bi('lotNumber')}</th>
                <th style={thStyle}>{bi('expiryDate')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{bi('daysLeft')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{bi('quantity')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{bi('valueAtRisk')}</th>
                <th style={thStyle}>Severity / ระดับ</th>
              </tr>
            </thead>
            <tbody>
              {expiryAlerts.length === 0 ? (
                <tr><td colSpan={7} style={{ ...tdStyle, textAlign: 'center', color: C.emerald, padding: 40 }}>
                  No expiry alerts / ไม่มีแจ้งเตือนหมดอายุ ✓
                </td></tr>
              ) : expiryAlerts.map((a, i) => (
                <tr key={a.lot_id} style={{
                  background: a.severity === 'expired' ? C.rubyMuted
                             : a.severity === 'critical' ? '#FFF5F5'
                             : i % 2 === 0 ? C.white : C.gray50,
                }}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600 }}>{a.supply_name_en}</div>
                    {a.supply_name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{a.supply_name_th}</div>}
                  </td>
                  <td style={tdStyle}>{a.lot_number}</td>
                  <td style={tdStyle}>{a.expiry_date || '—'}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700,
                    color: a.days_left <= 0 ? C.rubyDark : a.days_left <= 7 ? C.ruby : C.amber,
                  }}>{a.days_left}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>{a.current_quantity} {a.unit}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>฿{a.value_at_risk.toLocaleString()}</td>
                  <td style={tdStyle}><SeverityBadge severity={a.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {subTab === 'lowstock' && (
        <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: C.white }}>
            <thead>
              <tr>
                <th style={thStyle}>Supply / เวชภัณฑ์</th>
                <th style={thStyle}>{bi('category')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{bi('currentStock')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Reorder Lvl / ระดับสั่ง</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Suggested / แนะนำ</th>
                <th style={thStyle}>Severity / ระดับ</th>
              </tr>
            </thead>
            <tbody>
              {lowStockAlerts.length === 0 ? (
                <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', color: C.emerald, padding: 40 }}>
                  All stock levels OK / ระดับสต็อกปกติ ✓
                </td></tr>
              ) : lowStockAlerts.map((a, i) => (
                <tr key={a.id} style={{
                  background: a.severity === 'critical' ? C.rubyMuted
                             : i % 2 === 0 ? C.white : C.gray50,
                }}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600 }}>{a.name_en}</div>
                    {a.name_th && <div style={{ fontSize: 12, color: C.gray500 }}>{a.name_th}</div>}
                  </td>
                  <td style={tdStyle}>{catLabel(a.category)}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700,
                    color: a.current_stock === 0 ? C.rubyDark : C.amber,
                  }}>{a.current_stock} {a.unit}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>{a.reorder_level}</td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600, color: C.sapphire }}>
                    {a.suggested_order}
                  </td>
                  <td style={tdStyle}><SeverityBadge severity={a.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


// ══════════════════════════════════════════════════════════
// MAIN: SupplyDashboard
// ══════════════════════════════════════════════════════════

const TABS = [
  { key: 'dashboard',    label: T.dashboard },
  { key: 'catalogue',    label: T.supplyCatalogue },
  { key: 'stock',        label: T.stock },
  { key: 'requisitions', label: T.requisitions },
  { key: 'suppliers',    label: T.suppliers },
  { key: 'usage',        label: T.usageLog },
  { key: 'alerts',       label: T.alerts },
];

export default function SupplyDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const tabContent = {
    dashboard:    <DashboardTab />,
    catalogue:    <CatalogueTab />,
    stock:        <StockTab />,
    requisitions: <RequisitionsTab />,
    suppliers:    <SuppliersTab />,
    usage:        <UsageTab />,
    alerts:       <AlertsTab />,
  };

  return (
    <div style={{ fontFamily: "'Cloud', sans-serif", background: C.gray50, minHeight: '100vh' }}>
      {/* Header */}
      <div style={{
        background: C.sapphireDeep, color: C.white, padding: '20px 32px',
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <div style={{ fontSize: 24, fontWeight: 700 }}>
          Medical Supply / เวชภัณฑ์
        </div>
        <div style={{ fontSize: 13, opacity: 0.7, marginLeft: 'auto' }}>
          Life by Dr. Pat — FCMS Module 5
        </div>
      </div>

      {/* Tab Bar */}
      <div style={{
        background: C.white, borderBottom: `2px solid ${C.gray200}`,
        display: 'flex', gap: 0, overflowX: 'auto', padding: '0 24px',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '14px 20px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: activeTab === tab.key ? 700 : 400,
              color: activeTab === tab.key ? C.sapphire : C.gray500,
              borderBottom: activeTab === tab.key ? `3px solid ${C.sapphire}` : '3px solid transparent',
              whiteSpace: 'nowrap',
            }}
          >
            <span>{tab.label.en}</span>
            <span style={{ fontSize: 11, marginLeft: 4, opacity: 0.7 }}>{tab.label.th}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: '24px 32px' }}>
        {tabContent[activeTab]}
      </div>
    </div>
  );
}
