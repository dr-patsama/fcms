/**
 * FCMS Module 4 — Pharmacy Dashboard / แดชบอร์ดเภสัชกรรม
 * Tabs: Dashboard, Drug Catalogue, Stock, Prescriptions, Labels, Alerts
 * Design: Cloud font, Sapphire Deep headers, Emerald accent for pharmacy module
 * Fully bilingual (EN/TH) throughout
 */

import React, { useState, useEffect, useCallback } from 'react';

const API = '/api/v1/pharmacy';

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
  dashboard:       { en: 'Dashboard',        th: 'แดชบอร์ด' },
  drugCatalogue:   { en: 'Drug Catalogue',   th: 'รายการยา' },
  stock:           { en: 'Stock',            th: 'สต็อก' },
  prescriptions:   { en: 'Prescriptions',    th: 'ใบสั่งยา' },
  labels:          { en: 'Labels',           th: 'ฉลากยา' },
  alerts:          { en: 'Alerts',           th: 'แจ้งเตือน' },
  search:          { en: 'Search',           th: 'ค้นหา' },
  addDrug:         { en: 'Add Drug',         th: 'เพิ่มยา' },
  receiveStock:    { en: 'Receive Stock',    th: 'รับสต็อกเข้า' },
  genericName:     { en: 'Generic Name',     th: 'ชื่อสามัญ' },
  brandName:       { en: 'Brand Name',       th: 'ชื่อการค้า' },
  category:        { en: 'Category',         th: 'หมวดหมู่' },
  form:            { en: 'Form',             th: 'รูปแบบ' },
  strength:        { en: 'Strength',         th: 'ความแรง' },
  currentStock:    { en: 'Current Stock',    th: 'คงคลัง' },
  status:          { en: 'Status',           th: 'สถานะ' },
  actions:         { en: 'Actions',          th: 'การดำเนินการ' },
  pending:         { en: 'Pending',          th: 'รอดำเนินการ' },
  verified:        { en: 'Verified',         th: 'ตรวจสอบแล้ว' },
  dispensed:       { en: 'Dispensed',        th: 'จ่ายแล้ว' },
  cancelled:       { en: 'Cancelled',        th: 'ยกเลิก' },
  lowStock:        { en: 'Low Stock',        th: 'สต็อกต่ำ' },
  outOfStock:      { en: 'Out of Stock',     th: 'หมดสต็อก' },
  ok:              { en: 'In Stock',         th: 'มีสต็อก' },
  expiring30d:     { en: 'Expiring ≤30d',   th: 'หมดอายุ ≤30 วัน' },
  expired:         { en: 'Expired',          th: 'หมดอายุแล้ว' },
  totalDrugs:      { en: 'Total Drugs',      th: 'ยาทั้งหมด' },
  stockValue:      { en: 'Stock Value',      th: 'มูลค่าสต็อก' },
  dispensedToday:  { en: 'Dispensed Today',  th: 'จ่ายวันนี้' },
  pendingRx:       { en: 'Pending Rx',       th: 'ใบสั่งยารอ' },
  printLabel:      { en: 'Print Label',      th: 'พิมพ์ฉลาก' },
  previewLabel:    { en: 'Preview Label',    th: 'ดูตัวอย่างฉลาก' },
  lotNumber:       { en: 'Lot',              th: 'เลขล็อต' },
  expiryDate:      { en: 'Expiry',           th: 'วันหมดอายุ' },
  quantity:        { en: 'Qty',              th: 'จำนวน' },
  daysLeft:        { en: 'Days Left',        th: 'เหลือ (วัน)' },
  valueAtRisk:     { en: 'Value at Risk',    th: 'มูลค่าเสี่ยง' },
};
const bi = (key) => T[key] ? `${T[key].en} / ${T[key].th}` : key;

// ── Shared Components ────────────────────────────────────

function StatCard({ label, labelTh, value, sub, color, icon }) {
  return (
    <div style={{
      background: C.white, borderRadius: 14, padding: '18px 20px',
      border: `1px solid ${C.gray200}`, boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
      minWidth: 160,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: C.gray500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {label}
          </div>
          {labelTh && <div style={{ fontSize: 10, color: C.gray500, marginTop: 1 }}>{labelTh}</div>}
          <div style={{ fontSize: 28, fontWeight: 700, color: color || C.gray900, lineHeight: 1, marginTop: 8 }}>{value}</div>
          {sub && <div style={{ fontSize: 11, color: C.gray500, marginTop: 4 }}>{sub}</div>}
        </div>
        {icon && <span style={{ fontSize: 24, opacity: 0.5 }}>{icon}</span>}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    ok:           { bg: C.emeraldMuted, color: C.emeraldDark, label: '✓ In Stock / มีสต็อก' },
    low:          { bg: C.amberMuted,   color: '#92400E',     label: '⚠ Low / สต็อกต่ำ' },
    out_of_stock: { bg: C.rubyMuted,    color: C.rubyDark,    label: '✕ Out / หมด' },
    pending:      { bg: C.amberMuted,   color: '#92400E',     label: '⏳ Pending / รอ' },
    verified:     { bg: C.sapphireMuted, color: C.sapphire,   label: '✓ Verified / ตรวจแล้ว' },
    dispensed:    { bg: C.emeraldMuted, color: C.emeraldDark, label: '✓ Dispensed / จ่ายแล้ว' },
    cancelled:    { bg: C.rubyMuted,    color: C.rubyDark,    label: '✕ Cancelled / ยกเลิก' },
  };
  const s = map[status] || map.pending;
  return (
    <span style={{
      background: s.bg, color: s.color, padding: '3px 10px',
      borderRadius: 99, fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
    }}>{s.label}</span>
  );
}

function TableHeader({ columns }) {
  return (
    <thead>
      <tr>
        {columns.map((col, i) => (
          <th key={i} style={{
            background: C.sapphireDeep, color: C.white, padding: '10px 14px',
            fontSize: 11, fontWeight: 600, textAlign: 'left', textTransform: 'uppercase',
            letterSpacing: '0.05em', whiteSpace: 'nowrap',
            borderTopLeftRadius: i === 0 ? 10 : 0,
            borderTopRightRadius: i === columns.length - 1 ? 10 : 0,
          }}>
            {col.en && col.th ? (
              <div>
                <div>{col.en}</div>
                <div style={{ fontWeight: 400, fontSize: 10, opacity: 0.7 }}>{col.th}</div>
              </div>
            ) : col.label || col}
          </th>
        ))}
      </tr>
    </thead>
  );
}

function Btn({ children, onClick, variant = 'primary', size = 'md', disabled }) {
  const styles = {
    primary: { bg: C.sapphire, color: C.white, border: 'none' },
    emerald: { bg: C.emerald, color: C.white, border: 'none' },
    danger:  { bg: C.ruby, color: C.white, border: 'none' },
    outline: { bg: 'transparent', color: C.sapphire, border: `1px solid ${C.sapphire}` },
    ghost:   { bg: 'transparent', color: C.gray500, border: 'none' },
  };
  const s = styles[variant] || styles.primary;
  const pad = size === 'sm' ? '5px 12px' : '8px 18px';
  const fs = size === 'sm' ? 12 : 13;
  return (
    <button
      onClick={onClick} disabled={disabled}
      style={{
        background: disabled ? C.gray200 : s.bg,
        color: disabled ? C.gray500 : s.color,
        border: s.border, borderRadius: 6, padding: pad, fontSize: fs,
        fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.15s',
      }}
    >{children}</button>
  );
}


// ══════════════════════════════════════════════════════════
// TAB: DASHBOARD / แดชบอร์ด
// ══════════════════════════════════════════════════════════

function DashboardTab({ stats }) {
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard label="Total Drugs" labelTh="ยาทั้งหมด" value={stats.total_drugs || 0} icon="💊" color={C.sapphire} />
        <StatCard label="Stock Value" labelTh="มูลค่าสต็อก" value={`฿${(stats.total_stock_value || 0).toLocaleString()}`} icon="💰" color={C.emeraldDark} />
        <StatCard label="Pending Rx" labelTh="ใบสั่งยารอ" value={stats.pending_prescriptions || 0} icon="📋" color={C.amber} />
        <StatCard label="Dispensed Today" labelTh="จ่ายวันนี้" value={stats.dispensed_today || 0} icon="✅" color={C.emerald} />
        <StatCard label="Low Stock" labelTh="สต็อกต่ำ" value={stats.low_stock_items || 0} icon="⚠️" color={C.amber} />
        <StatCard label="Out of Stock" labelTh="หมดสต็อก" value={stats.out_of_stock_items || 0} icon="🚫" color={C.ruby} />
        <StatCard label="Expiring ≤30d" labelTh="หมดอายุ ≤30 วัน" value={stats.expiring_30d || 0} icon="⏰" color={C.rubyDark} />
        <StatCard label="Verified Rx" labelTh="ตรวจแล้วรอจ่าย" value={stats.verified_prescriptions || 0} icon="📝" color={C.sapphireLight} />
      </div>
    </div>
  );
}


// ══════════════════════════════════════════════════════════
// TAB: DRUG CATALOGUE / รายการยา
// ══════════════════════════════════════════════════════════

function DrugCatalogueTab({ drugs, filters, onSearch, searchTerm }) {
  const cols = [
    { en: 'Generic Name', th: 'ชื่อสามัญ' },
    { en: 'Brand', th: 'ชื่อการค้า' },
    { en: 'Category', th: 'หมวดหมู่' },
    { en: 'Form', th: 'รูปแบบ' },
    { en: 'Strength', th: 'ความแรง' },
    { en: 'Stock', th: 'คงคลัง' },
    { en: 'Status', th: 'สถานะ' },
    { en: 'Price (฿)', th: 'ราคา (฿)' },
  ];

  return (
    <div>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 400 }}>
          <input
            value={searchTerm} onChange={e => onSearch(e.target.value)}
            placeholder="Search drugs / ค้นหายา..."
            style={{
              width: '100%', padding: '8px 14px 8px 36px', borderRadius: 6,
              border: `1px solid ${C.gray200}`, fontSize: 13, outline: 'none',
            }}
          />
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 14, color: C.gray500 }}>🔍</span>
        </div>
        <Btn variant="emerald">+ {bi('addDrug')}</Btn>
      </div>

      {/* Table */}
      <div style={{ borderRadius: 10, overflow: 'hidden', border: `1px solid ${C.gray200}` }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <TableHeader columns={cols} />
          <tbody>
            {drugs.length === 0 ? (
              <tr><td colSpan={cols.length} style={{ textAlign: 'center', padding: 40, color: C.gray500 }}>
                No drugs found / ไม่พบข้อมูลยา
              </td></tr>
            ) : drugs.map((d, i) => (
              <tr key={d.id} style={{
                background: i % 2 === 0 ? C.white : C.gray50,
                transition: 'background 0.15s',
              }}
                onMouseEnter={e => e.currentTarget.style.background = C.sapphireMuted}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? C.white : C.gray50}
              >
                <td style={{ padding: '10px 14px', fontSize: 13 }}>
                  <div style={{ fontWeight: 600 }}>{d.generic_name}</div>
                  {d.generic_name_th && <div style={{ fontSize: 11, color: C.gray500 }}>{d.generic_name_th}</div>}
                </td>
                <td style={{ padding: '10px 14px', fontSize: 13 }}>
                  {d.brand_name || '—'}
                  {d.brand_name_th && <div style={{ fontSize: 11, color: C.gray500 }}>{d.brand_name_th}</div>}
                </td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: C.gray500 }}>{d.category}</td>
                <td style={{ padding: '10px 14px', fontSize: 12 }}>
                  {d.form}{d.form_th ? ` / ${d.form_th}` : ''}
                </td>
                <td style={{ padding: '10px 14px', fontSize: 12 }}>{d.strength}</td>
                <td style={{ padding: '10px 14px', fontSize: 13, fontWeight: 600,
                  color: d.current_stock === 0 ? C.ruby : d.stock_status === 'low' ? C.amber : C.gray900,
                }}>{d.current_stock}</td>
                <td style={{ padding: '10px 14px' }}><StatusBadge status={d.stock_status} /></td>
                <td style={{ padding: '10px 14px', fontSize: 13 }}>
                  {d.selling_price ? `฿${d.selling_price.toFixed(2)}` : '—'}
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
// TAB: PRESCRIPTIONS / ใบสั่งยา
// ══════════════════════════════════════════════════════════

function PrescriptionsTab({ prescriptions, counts }) {
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all'
    ? prescriptions
    : prescriptions.filter(rx => rx.status === filter);

  const statusFilters = [
    { key: 'all', label: 'All / ทั้งหมด', count: prescriptions.length },
    { key: 'pending', label: '⏳ Pending / รอ', count: counts.pending || 0, color: C.amber },
    { key: 'verified', label: '✓ Verified / ตรวจแล้ว', count: counts.verified || 0, color: C.sapphire },
    { key: 'dispensed', label: '✓ Dispensed / จ่ายแล้ว', count: counts.dispensed || 0, color: C.emerald },
    { key: 'cancelled', label: '✕ Cancelled / ยกเลิก', count: counts.cancelled || 0, color: C.ruby },
  ];

  return (
    <div>
      {/* Status filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {statusFilters.map(sf => (
          <button key={sf.key} onClick={() => setFilter(sf.key)}
            style={{
              padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600,
              border: filter === sf.key ? `2px solid ${sf.color || C.sapphire}` : `1px solid ${C.gray200}`,
              background: filter === sf.key ? (sf.color ? sf.color + '15' : C.sapphireMuted) : C.white,
              color: filter === sf.key ? (sf.color || C.sapphire) : C.gray500,
              cursor: 'pointer',
            }}
          >{sf.label} ({sf.count})</button>
        ))}
      </div>

      <div style={{ borderRadius: 10, overflow: 'hidden', border: `1px solid ${C.gray200}` }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <TableHeader columns={[
            { en: 'Rx Number', th: 'เลขใบสั่งยา' },
            { en: 'Patient', th: 'ผู้ป่วย' },
            { en: 'Items', th: 'รายการ' },
            { en: 'Priority', th: 'ความเร่งด่วน' },
            { en: 'Status', th: 'สถานะ' },
            { en: 'Date', th: 'วันที่' },
            { en: 'Actions', th: 'การดำเนินการ' },
          ]} />
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40, color: C.gray500 }}>
                No prescriptions / ไม่มีใบสั่งยา
              </td></tr>
            ) : filtered.map((rx, i) => (
              <tr key={rx.id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                <td style={{ padding: '10px 14px', fontSize: 13, fontWeight: 600 }}>{rx.rx_number || '—'}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: C.gray500 }}>{rx.patient_id?.slice(0,8)}...</td>
                <td style={{ padding: '10px 14px', fontSize: 13 }}>{rx.item_count}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{
                    background: rx.priority === 'stat' ? C.rubyMuted : rx.priority === 'urgent' ? C.amberMuted : C.gray50,
                    color: rx.priority === 'stat' ? C.ruby : rx.priority === 'urgent' ? '#92400E' : C.gray500,
                    padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                  }}>{rx.priority?.toUpperCase()}</span>
                </td>
                <td style={{ padding: '10px 14px' }}><StatusBadge status={rx.status} /></td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: C.gray500 }}>
                  {rx.created_at ? new Date(rx.created_at).toLocaleDateString('th-TH') : '—'}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {rx.status === 'pending' && <Btn size="sm" variant="primary">Verify / ตรวจสอบ</Btn>}
                    {rx.status === 'verified' && <Btn size="sm" variant="emerald">Dispense / จ่าย</Btn>}
                    {rx.status === 'dispensed' && <Btn size="sm" variant="outline">Label / ฉลาก</Btn>}
                  </div>
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
// TAB: LABEL PREVIEW / ดูตัวอย่างฉลากยา
// ══════════════════════════════════════════════════════════

function LabelPreviewTab() {
  // Demo label data
  const demo = {
    clinic_name_en: 'Life by Dr. Pat',
    clinic_name_th: 'คลินิก ไลฟ์ บาย ดร.แพท',
    clinic_phone: '02-XXX-XXXX',
    patient_hn: 'HN-2026-00042',
    patient_name_en: 'Somying Thongdee',
    patient_name_th: 'สมหญิง ทองดี',
    drug_name_en: 'Progesterone (Utrogestan)',
    drug_name_th: 'โปรเจสเตอโรน (อูโทรเจสแตน)',
    strength: '200mg',
    form_en: 'Capsule',
    form_th: 'แคปซูล',
    quantity: 30,
    unit_en: 'capsules',
    unit_th: 'แคปซูล',
    dosage_en: 'Take 1 capsule',
    dosage_th: 'รับประทานครั้งละ 1 แคปซูล',
    frequency_en: 'Three times daily',
    frequency_th: 'วันละ 3 ครั้ง',
    route_en: 'Vaginal',
    route_th: 'สอดช่องคลอด',
    instructions_en: 'Insert vaginally at bedtime',
    instructions_th: 'สอดช่องคลอดก่อนนอน',
    warnings_en: ['Store in refrigerator (2-8°C)'],
    warnings_th: ['เก็บในตู้เย็น (2-8°C)'],
    dispensed_date: '05/03/2026',
    dispensed_date_th: '05/03/2569',
    barcode_data: 'RX-HN-2026-00042-202603051030',
    prescriber_name: 'Dr. Patsama V.',
  };

  return (
    <div>
      <div style={{ fontSize: 14, fontWeight: 600, color: C.gray900, marginBottom: 8 }}>
        Label Preview / ดูตัวอย่างฉลากยา
      </div>
      <div style={{ fontSize: 12, color: C.gray500, marginBottom: 20 }}>
        Standard 80mm × 50mm pharmacy label with bilingual content / ฉลากยามาตรฐาน 80×50 มม. สองภาษา
      </div>

      {/* Label card — simulates 80×50mm at ~2× scale */}
      <div style={{
        width: 604, minHeight: 378, border: `2px solid ${C.gray200}`,
        borderRadius: 6, padding: 14, background: C.white,
        fontFamily: "'Cloud', 'Noto Sans Thai', sans-serif",
        boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        position: 'relative',
      }}>
        {/* Clinic header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: `2px solid ${C.emerald}`, paddingBottom: 6, marginBottom: 8,
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: C.emeraldDark }}>{demo.clinic_name_en}</div>
            <div style={{ fontWeight: 600, fontSize: 11, color: C.emerald }}>{demo.clinic_name_th}</div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 10, color: C.gray500 }}>
            <div>☎ {demo.clinic_phone}</div>
          </div>
        </div>

        {/* Patient info */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', marginBottom: 8,
          background: C.sapphireMuted, borderRadius: 4, padding: '5px 8px',
        }}>
          <div>
            <span style={{ fontSize: 10, color: C.gray500 }}>Patient / ผู้ป่วย: </span>
            <span style={{ fontSize: 12, fontWeight: 600 }}>{demo.patient_name_en}</span>
            <span style={{ fontSize: 11, color: C.gray500, marginLeft: 4 }}>({demo.patient_name_th})</span>
          </div>
          <div style={{ fontSize: 11, fontWeight: 600, color: C.sapphire }}>{demo.patient_hn}</div>
        </div>

        {/* Drug name */}
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.gray900 }}>
            💊 {demo.drug_name_en} {demo.strength}
          </div>
          <div style={{ fontSize: 12, color: C.gray500 }}>
            {demo.drug_name_th} — {demo.form_en} / {demo.form_th}
          </div>
        </div>

        {/* Dosage instructions */}
        <div style={{
          background: C.emeraldMuted, borderRadius: 4, padding: '6px 8px', marginBottom: 6,
          borderLeft: `3px solid ${C.emerald}`,
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.emeraldDark }}>
            {demo.dosage_en} — {demo.frequency_en} — {demo.route_en}
          </div>
          <div style={{ fontSize: 11, color: C.emeraldDark }}>
            {demo.dosage_th} — {demo.frequency_th} — {demo.route_th}
          </div>
          {demo.instructions_en && (
            <div style={{ fontSize: 11, color: C.gray500, marginTop: 2 }}>
              📌 {demo.instructions_en} / {demo.instructions_th}
            </div>
          )}
        </div>

        {/* Warnings */}
        {demo.warnings_en.length > 0 && (
          <div style={{
            background: C.rubyMuted, borderRadius: 4, padding: '4px 8px', marginBottom: 6,
            borderLeft: `3px solid ${C.ruby}`,
          }}>
            {demo.warnings_en.map((w, i) => (
              <div key={i} style={{ fontSize: 11, fontWeight: 600, color: C.rubyDark }}>
                ⚠️ {w} / {demo.warnings_th[i] || ''}
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
          borderTop: `1px solid ${C.gray200}`, paddingTop: 6, marginTop: 4,
        }}>
          <div style={{ fontSize: 10, color: C.gray500 }}>
            <div>Qty / จำนวน: <b>{demo.quantity} {demo.unit_en} / {demo.unit_th}</b></div>
            <div>Dr. / แพทย์: {demo.prescriber_name}</div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 10, color: C.gray500 }}>
            <div>Date / วันที่: {demo.dispensed_date}</div>
            <div>พ.ศ. {demo.dispensed_date_th}</div>
            <div style={{ fontFamily: 'monospace', fontSize: 9, marginTop: 2, letterSpacing: 1 }}>
              {demo.barcode_data}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
        <Btn variant="primary">🖨️ Print / พิมพ์</Btn>
        <Btn variant="outline">📄 Export PDF / ส่งออก PDF</Btn>
      </div>
    </div>
  );
}


// ══════════════════════════════════════════════════════════
// TAB: ALERTS / แจ้งเตือน
// ══════════════════════════════════════════════════════════

function AlertsTab({ alerts }) {
  const sections = [
    { key: 'already_expired', label: '🔴 Expired / หมดอายุแล้ว', color: C.ruby, items: alerts.already_expired || [] },
    { key: 'expiring_30d',    label: '🟡 ≤30 Days / ≤30 วัน', color: C.amber, items: alerts.expiring_30d || [] },
    { key: 'expiring_60d',    label: '🟠 31–60 Days / 31–60 วัน', color: '#F97316', items: alerts.expiring_60d || [] },
    { key: 'expiring_90d',    label: '🔵 61–90 Days / 61–90 วัน', color: C.sapphireLight, items: alerts.expiring_90d || [] },
  ];

  return (
    <div>
      <div style={{
        background: C.rubyMuted, borderRadius: 10, padding: '12px 16px', marginBottom: 16,
        borderLeft: `4px solid ${C.ruby}`, display: 'flex', justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: C.rubyDark }}>
          ⚠️ Total Value at Risk / มูลค่าเสี่ยงรวม
        </span>
        <span style={{ fontSize: 15, fontWeight: 700, color: C.ruby }}>
          ฿{(alerts.total_value_at_risk || 0).toLocaleString()}
        </span>
      </div>

      {sections.map(sec => (
        <div key={sec.key} style={{ marginBottom: 20 }}>
          <div style={{
            fontSize: 13, fontWeight: 700, color: sec.color, marginBottom: 8,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            {sec.label}
            <span style={{
              background: sec.color + '20', color: sec.color,
              padding: '2px 8px', borderRadius: 10, fontSize: 11,
            }}>{sec.items.length}</span>
          </div>

          {sec.items.length > 0 ? (
            <div style={{ borderRadius: 10, overflow: 'hidden', border: `1px solid ${C.gray200}` }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <TableHeader columns={[
                  { en: 'Drug', th: 'ยา' },
                  { en: 'Lot', th: 'ล็อต' },
                  { en: 'Expiry', th: 'หมดอายุ' },
                  { en: 'Days Left', th: 'เหลือ (วัน)' },
                  { en: 'Qty', th: 'จำนวน' },
                  { en: 'Value (฿)', th: 'มูลค่า (฿)' },
                ]} />
                <tbody>
                  {sec.items.map((item, i) => (
                    <tr key={item.lot_id} style={{ background: i % 2 === 0 ? C.white : C.gray50 }}>
                      <td style={{ padding: '8px 14px', fontSize: 12 }}>
                        <div style={{ fontWeight: 600 }}>{item.drug_name}</div>
                        {item.drug_name_th && <div style={{ fontSize: 11, color: C.gray500 }}>{item.drug_name_th}</div>}
                      </td>
                      <td style={{ padding: '8px 14px', fontSize: 12, fontFamily: 'monospace' }}>{item.lot_number}</td>
                      <td style={{ padding: '8px 14px', fontSize: 12 }}>{item.expiry_date}</td>
                      <td style={{ padding: '8px 14px', fontSize: 13, fontWeight: 700,
                        color: item.days_to_expiry <= 0 ? C.ruby : item.days_to_expiry <= 30 ? C.amber : C.gray900,
                      }}>{item.days_to_expiry}</td>
                      <td style={{ padding: '8px 14px', fontSize: 12 }}>{item.current_quantity} {item.unit}</td>
                      <td style={{ padding: '8px 14px', fontSize: 12 }}>
                        ฿{(item.value_at_risk || 0).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: 20, textAlign: 'center', color: C.gray500, fontSize: 12,
              background: C.gray50, borderRadius: 10,
            }}>No items / ไม่มีรายการ ✓</div>
          )}
        </div>
      ))}
    </div>
  );
}


// ══════════════════════════════════════════════════════════
// MAIN DASHBOARD SHELL / โครงหลัก
// ══════════════════════════════════════════════════════════

export default function PharmacyDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState({});
  const [drugs, setDrugs] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [rxCounts, setRxCounts] = useState({});
  const [alerts, setAlerts] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  // Demo data for preview (API would populate in production)
  useEffect(() => {
    setStats({
      total_drugs: 87, total_stock_value: 1245780,
      low_stock_items: 12, out_of_stock_items: 3,
      expiring_30d: 8, pending_prescriptions: 15,
      verified_prescriptions: 6, dispensed_today: 23,
    });
    setDrugs([
      { id: '1', generic_name: 'Progesterone', generic_name_th: 'โปรเจสเตอโรน', brand_name: 'Utrogestan', brand_name_th: 'อูโทรเจสแตน', category: 'Hormonal', form: 'Capsule', form_th: 'แคปซูล', strength: '200mg', current_stock: 450, reorder_level: 100, stock_status: 'ok', selling_price: 35.00 },
      { id: '2', generic_name: 'Follitropin Alfa', generic_name_th: 'ฟอลลิโทรพินอัลฟา', brand_name: 'Gonal-F', brand_name_th: 'โกนาล-เอฟ', category: 'IVF Protocol', form: 'Injection', form_th: 'ยาฉีด', strength: '300IU', current_stock: 24, reorder_level: 30, stock_status: 'low', selling_price: 4500.00 },
      { id: '3', generic_name: 'Cetorelix', generic_name_th: 'ซีโทรีลิกซ์', brand_name: 'Cetrotide', brand_name_th: 'ซีโทรไทด์', category: 'IVF Protocol', form: 'Injection', form_th: 'ยาฉีด', strength: '0.25mg', current_stock: 0, reorder_level: 20, stock_status: 'out_of_stock', selling_price: 2800.00 },
      { id: '4', generic_name: 'Letrozole', generic_name_th: 'เลโทรโซล', brand_name: 'Femara', brand_name_th: 'ฟีมาร่า', category: 'IVF Protocol', form: 'Tablet', form_th: 'เม็ด', strength: '2.5mg', current_stock: 300, reorder_level: 50, stock_status: 'ok', selling_price: 120.00 },
      { id: '5', generic_name: 'Enoxaparin', generic_name_th: 'อีนอกซาพาริน', brand_name: 'Clexane', brand_name_th: 'เคล็กเซน', category: 'Anticoagulant', form: 'Injection', form_th: 'ยาฉีด', strength: '40mg/0.4ml', current_stock: 85, reorder_level: 30, stock_status: 'ok', selling_price: 650.00 },
      { id: '6', generic_name: 'Folic Acid', generic_name_th: 'กรดโฟลิก', brand_name: null, brand_name_th: null, category: 'Vitamin', form: 'Tablet', form_th: 'เม็ด', strength: '5mg', current_stock: 1200, reorder_level: 200, stock_status: 'ok', selling_price: 5.00 },
      { id: '7', generic_name: 'Doxycycline', generic_name_th: 'ด็อกซีไซคลิน', brand_name: null, brand_name_th: null, category: 'Antibiotic', form: 'Capsule', form_th: 'แคปซูล', strength: '100mg', current_stock: 180, reorder_level: 100, stock_status: 'ok', selling_price: 8.00 },
      { id: '8', generic_name: 'Estradiol Valerate', generic_name_th: 'เอสตราไดออลวาเลอเรต', brand_name: 'Progynova', brand_name_th: 'โปรจีโนวา', category: 'Hormonal', form: 'Tablet', form_th: 'เม็ด', strength: '2mg', current_stock: 42, reorder_level: 50, stock_status: 'low', selling_price: 22.00 },
    ]);
    setPrescriptions([
      { id: 'rx1', rx_number: 'RX-2026-00148', patient_id: 'pt-abc-12345678', status: 'pending', priority: 'normal', item_count: 3, created_at: '2026-03-05T09:15:00Z' },
      { id: 'rx2', rx_number: 'RX-2026-00147', patient_id: 'pt-def-87654321', status: 'verified', priority: 'urgent', item_count: 5, created_at: '2026-03-05T08:45:00Z' },
      { id: 'rx3', rx_number: 'RX-2026-00146', patient_id: 'pt-ghi-11223344', status: 'dispensed', priority: 'normal', item_count: 2, created_at: '2026-03-04T16:30:00Z', dispensed_at: '2026-03-04T17:00:00Z' },
      { id: 'rx4', rx_number: 'RX-2026-00145', patient_id: 'pt-jkl-55667788', status: 'pending', priority: 'stat', item_count: 1, created_at: '2026-03-05T10:00:00Z' },
    ]);
    setRxCounts({ pending: 15, verified: 6, dispensed: 23, cancelled: 2 });
    setAlerts({
      already_expired: [
        { lot_id: 'e1', drug_id: 'd1', drug_name: 'Cetrotide', drug_name_th: 'ซีโทรไทด์', lot_number: 'LOT-2024-A1', expiry_date: '2026-02-28', current_quantity: 5, unit: 'vials', days_to_expiry: -5, value_at_risk: 14000 },
      ],
      expiring_30d: [
        { lot_id: 'e2', drug_id: 'd2', drug_name: 'Gonal-F 300IU', drug_name_th: 'โกนาล-เอฟ 300IU', lot_number: 'LOT-2025-G3', expiry_date: '2026-03-25', current_quantity: 8, unit: 'pens', days_to_expiry: 20, value_at_risk: 36000 },
        { lot_id: 'e3', drug_id: 'd3', drug_name: 'Progynova 2mg', drug_name_th: 'โปรจีโนวา 2mg', lot_number: 'LOT-2025-P7', expiry_date: '2026-04-01', current_quantity: 30, unit: 'tablets', days_to_expiry: 27, value_at_risk: 660 },
      ],
      expiring_60d: [],
      expiring_90d: [
        { lot_id: 'e4', drug_id: 'd4', drug_name: 'Clexane 40mg', drug_name_th: 'เคล็กเซน 40mg', lot_number: 'LOT-2025-C9', expiry_date: '2026-05-15', current_quantity: 20, unit: 'syringes', days_to_expiry: 71, value_at_risk: 13000 },
      ],
      total_value_at_risk: 63660,
    });
    setLoading(false);
  }, []);

  const tabs = [
    { key: 'dashboard',    icon: '📊', en: 'Dashboard',    th: 'แดชบอร์ด' },
    { key: 'drugs',        icon: '💊', en: 'Drug Catalogue', th: 'รายการยา' },
    { key: 'prescriptions',icon: '📋', en: 'Prescriptions', th: 'ใบสั่งยา' },
    { key: 'labels',       icon: '🏷️', en: 'Labels',        th: 'ฉลากยา' },
    { key: 'alerts',       icon: '⚠️', en: 'Alerts',        th: 'แจ้งเตือน' },
  ];

  return (
    <div style={{
      fontFamily: "'Cloud', 'Noto Sans Thai', -apple-system, sans-serif",
      background: C.gray50, minHeight: '100vh',
    }}>
      {/* Header */}
      <div style={{
        background: C.sapphireDeep, color: C.white, padding: '16px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24 }}>💊</span>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>Pharmacy / เภสัชกรรม</div>
            <div style={{ fontSize: 11, opacity: 0.7 }}>Module 4 — Drug Management & Dispensing / จัดการยาและจ่ายยา</div>
          </div>
        </div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>
          Life by Dr. Pat / คลินิก ไลฟ์ บาย ดร.แพท
        </div>
      </div>

      {/* Tab bar */}
      <div style={{
        background: C.white, borderBottom: `1px solid ${C.gray200}`,
        display: 'flex', padding: '0 24px', gap: 4,
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '12px 18px', fontSize: 13, fontWeight: 600,
              border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: activeTab === tab.key ? `3px solid ${C.emerald}` : '3px solid transparent',
              color: activeTab === tab.key ? C.emeraldDark : C.gray500,
              transition: 'all 0.2s',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <span>{tab.icon}</span>
            <span>{tab.en}</span>
            <span style={{ fontSize: 11, opacity: 0.6 }}>{tab.th}</span>
            {tab.key === 'prescriptions' && (rxCounts.pending > 0) && (
              <span style={{
                background: C.ruby, color: C.white, padding: '1px 6px',
                borderRadius: 10, fontSize: 10, fontWeight: 700, minWidth: 18, textAlign: 'center',
              }}>{rxCounts.pending}</span>
            )}
            {tab.key === 'alerts' && (alerts.already_expired?.length > 0) && (
              <span style={{
                background: C.ruby, color: C.white, padding: '1px 6px',
                borderRadius: 10, fontSize: 10, fontWeight: 700,
              }}>!</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        {activeTab === 'dashboard' && <DashboardTab stats={stats} />}
        {activeTab === 'drugs' && (
          <DrugCatalogueTab
            drugs={searchTerm ? drugs.filter(d =>
              d.generic_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
              (d.generic_name_th || '').includes(searchTerm) ||
              (d.brand_name || '').toLowerCase().includes(searchTerm.toLowerCase())
            ) : drugs}
            filters={{}} onSearch={setSearchTerm} searchTerm={searchTerm}
          />
        )}
        {activeTab === 'prescriptions' && <PrescriptionsTab prescriptions={prescriptions} counts={rxCounts} />}
        {activeTab === 'labels' && <LabelPreviewTab />}
        {activeTab === 'alerts' && <AlertsTab alerts={alerts} />}
      </div>
    </div>
  );
}
