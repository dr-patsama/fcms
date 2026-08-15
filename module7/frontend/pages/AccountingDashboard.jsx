/**
 * FCMS Module 7 — Accounting Dashboard / แดชบอร์ดบัญชี
 * Tabs: Dashboard, Invoices, Payments, Price List, Expenses, Reports, Daily Closing
 * Design: Cloud font, Ruby #E0115F sidebar, Sapphire Deep #151667 headers & primary buttons
 * Fully bilingual (EN/TH). Printable receipt shows Buddhist calendar year (พ.ศ.).
 */

import React, { useState, useEffect, useCallback } from 'react';

const API = '/api/v1/accounting';

const C = {
  sapphire: '#0F52BA', sapphireDeep: '#151667', sapphireLight: '#4A7FD4', sapphireMuted: '#E8EEFA',
  emerald: '#009473', emeraldVivid: '#50C878', emeraldDark: '#006B54', emeraldMuted: '#E0F5EF',
  ruby: '#E0115F', rubyDark: '#A00040', rubyMuted: '#FCE4EE',
  amber: '#F59E0B', amberMuted: '#FEF3C7', gold: '#C5A044',
  gray900: '#111827', gray500: '#6B7280', gray200: '#E5E7EB', gray50: '#F9FAFB', white: '#FFFFFF',
};

const T = {
  dashboard:      { en: 'Dashboard',           th: 'แดชบอร์ด' },
  invoices:       { en: 'Invoices',            th: 'ใบแจ้งหนี้' },
  payments:       { en: 'Payments',            th: 'การรับชำระ' },
  services:       { en: 'Price List',          th: 'รายการค่าบริการ' },
  expenses:       { en: 'Expenses',            th: 'ค่าใช้จ่าย' },
  reports:        { en: 'Reports',             th: 'รายงาน' },
  closing:        { en: 'Daily Closing',       th: 'ปิดยอดประจำวัน' },
  invoiceNum:     { en: 'Invoice #',           th: 'เลขที่ใบแจ้งหนี้' },
  receiptNum:     { en: 'Receipt #',           th: 'เลขที่ใบเสร็จ' },
  patient:        { en: 'Patient',             th: 'ผู้ป่วย' },
  date:           { en: 'Date',                th: 'วันที่' },
  status:         { en: 'Status',              th: 'สถานะ' },
  subtotal:       { en: 'Subtotal',            th: 'รวมก่อนส่วนลด' },
  discount:       { en: 'Discount',            th: 'ส่วนลด' },
  vat:            { en: 'VAT',                 th: 'ภาษีมูลค่าเพิ่ม' },
  total:          { en: 'Total',               th: 'รวมทั้งสิ้น' },
  paid:           { en: 'Paid',                th: 'ชำระแล้ว' },
  balance:        { en: 'Balance Due',         th: 'ยอดคงเหลือ' },
  amount:         { en: 'Amount',              th: 'จำนวนเงิน' },
  method:         { en: 'Method',              th: 'วิธีชำระ' },
  code:           { en: 'Code',                th: 'รหัส' },
  service:        { en: 'Service',             th: 'รายการ' },
  category:       { en: 'Category',            th: 'หมวดหมู่' },
  unitPrice:      { en: 'Unit Price',          th: 'ราคาต่อหน่วย' },
  qty:            { en: 'Qty',                 th: 'จำนวน' },
  lineTotal:      { en: 'Line Total',          th: 'รวม' },
  vendor:         { en: 'Vendor',              th: 'ผู้ขาย' },
  wht:            { en: 'WHT',                 th: 'หัก ณ ที่จ่าย' },
  netPaid:        { en: 'Net Paid',            th: 'จ่ายสุทธิ' },
  todayRevenue:   { en: "Today's Revenue",     th: 'รายรับวันนี้' },
  monthRevenue:   { en: 'Month Revenue',       th: 'รายรับเดือนนี้' },
  monthExpenses:  { en: 'Month Expenses',      th: 'รายจ่ายเดือนนี้' },
  monthNet:       { en: 'Month Net',           th: 'กำไรสุทธิเดือนนี้' },
  outstanding:    { en: 'Outstanding',         th: 'ค้างชำระ' },
  newInvoice:     { en: 'New Invoice',         th: 'สร้างใบแจ้งหนี้' },
  recordPayment:  { en: 'Record Payment',      th: 'บันทึกรับชำระ' },
  newExpense:     { en: 'New Expense',         th: 'บันทึกค่าใช้จ่าย' },
  newService:     { en: 'New Service',         th: 'เพิ่มรายการ' },
  importCSV:      { en: 'Import CSV',          th: 'นำเข้า CSV' },
  printReceipt:   { en: 'Print Receipt',       th: 'พิมพ์ใบเสร็จ' },
  void:           { en: 'Void',                th: 'ยกเลิก' },
  search:         { en: 'Search',              th: 'ค้นหา' },
  actions:        { en: 'Actions',             th: 'การดำเนินการ' },
  save:           { en: 'Save',                th: 'บันทึก' },
  cancel:         { en: 'Cancel',              th: 'ยกเลิก' },
  notes:          { en: 'Notes',               th: 'หมายเหตุ' },
  reference:      { en: 'Reference',           th: 'เลขอ้างอิง' },
  cashExpected:   { en: 'Cash Expected',       th: 'เงินสดตามระบบ' },
  cashCounted:    { en: 'Cash Counted',        th: 'เงินสดนับจริง' },
  variance:       { en: 'Variance',            th: 'ผลต่าง' },
  closeDay:       { en: 'Close Day',           th: 'ปิดยอด' },
  monthlyPL:      { en: 'Monthly P&L',         th: 'กำไร-ขาดทุนรายเดือน' },
  arAging:        { en: 'AR Aging',            th: 'อายุลูกหนี้' },
  taxInvoice:     { en: 'Tax Invoice',         th: 'ใบกำกับภาษี' },
  addLine:        { en: 'Add Line',            th: 'เพิ่มรายการ' },
  description:    { en: 'Description',         th: 'รายละเอียด' },
};
const bi = (k) => T[k] ? `${T[k].en} / ${T[k].th}` : k;

const STATUS_LABELS = {
  draft: 'Draft / ร่าง', issued: 'Issued / ออกแล้ว',
  partially_paid: 'Partially Paid / ชำระบางส่วน', paid: 'Paid / ชำระครบ',
  void: 'Void / ยกเลิกแล้ว',
};
const STATUS_COLORS = {
  draft: { bg: C.gray200, fg: C.gray900 }, issued: { bg: C.sapphireMuted, fg: C.sapphireDeep },
  partially_paid: { bg: C.amberMuted, fg: '#92400E' }, paid: { bg: C.emeraldMuted, fg: C.emeraldDark },
  void: { bg: C.rubyMuted, fg: C.rubyDark },
};
const METHOD_LABELS = {
  cash: 'Cash / เงินสด', credit_card: 'Credit Card / บัตรเครดิต',
  debit_card: 'Debit Card / บัตรเดบิต', bank_transfer: 'Transfer / โอนเงิน',
  promptpay: 'PromptPay / พร้อมเพย์', insurance: 'Insurance / ประกัน', other: 'Other / อื่น ๆ',
};
const SVC_CATEGORIES = {
  consultation: 'Consultation / ค่าตรวจ-ปรึกษา', laboratory: 'Laboratory / ห้องปฏิบัติการ',
  ultrasound: 'Ultrasound / อัลตราซาวด์', procedure: 'Procedure / หัตถการ',
  ivf_package: 'IVF Package / แพ็กเกจเด็กหลอดแก้ว', medication: 'Medication / ยา',
  retail: 'Retail / สินค้า', other: 'Other / อื่น ๆ',
};
const EXP_CATEGORIES = {
  salaries: 'Salaries / เงินเดือน', rent: 'Rent / ค่าเช่า', utilities: 'Utilities / ค่าน้ำ-ค่าไฟ',
  medical_supplies: 'Medical Supplies / เวชภัณฑ์', lab_reagents: 'Lab Reagents / น้ำยาแล็บ',
  medications: 'Medications / ยา', equipment: 'Equipment / อุปกรณ์',
  maintenance: 'Maintenance / ซ่อมบำรุง', marketing: 'Marketing / การตลาด',
  insurance: 'Insurance / ประกัน', professional_fees: 'Professional Fees / ค่าวิชาชีพ',
  bank_fees: 'Bank Fees / ค่าธรรมเนียมธนาคาร', taxes: 'Taxes / ภาษี', other: 'Other / อื่น ๆ',
};

const fmtTHB = (v) =>
  Number(v || 0).toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// Buddhist calendar: พ.ศ. = ค.ศ. + 543
const fmtDateBE = (d) => {
  if (!d) return '';
  const dt = new Date(d);
  return `${dt.getDate()}/${dt.getMonth() + 1}/${dt.getFullYear() + 543}`;
};

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('fcms_token') || ''}`,
});
const api = async (path, opts = {}) => {
  const res = await fetch(`${API}${path}`, { headers: authHeaders(), ...opts });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

// ── Shared UI ─────────────────────────────────────────────

const styles = {
  page: { fontFamily: "'Cloud', sans-serif", background: C.gray50, minHeight: '100vh', color: C.gray900 },
  card: { background: C.white, borderRadius: 10, border: `1px solid ${C.gray200}`, padding: 20 },
  th: { background: C.sapphireDeep, color: C.white, textAlign: 'left', padding: '10px 12px', fontWeight: 500, fontSize: 13 },
  td: { padding: '10px 12px', borderBottom: `1px solid ${C.gray200}`, fontSize: 13 },
  btnPrimary: { background: C.sapphireDeep, color: C.white, border: 'none', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 },
  btnGhost: { background: C.white, color: C.sapphireDeep, border: `1px solid ${C.sapphireDeep}`, borderRadius: 6, padding: '7px 14px', cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 },
  btnDanger: { background: C.white, color: C.rubyDark, border: `1px solid ${C.rubyDark}`, borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontFamily: 'inherit', fontSize: 12 },
  input: { border: `1px solid ${C.gray200}`, borderRadius: 6, padding: '8px 10px', fontSize: 13, fontFamily: 'inherit', width: '100%' },
  label: { fontSize: 12, color: C.gray500, marginBottom: 4, display: 'block' },
};

const Badge = ({ status }) => {
  const c = STATUS_COLORS[status] || STATUS_COLORS.draft;
  return (
    <span style={{ background: c.bg, color: c.fg, borderRadius: 6, padding: '3px 10px', fontSize: 12 }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
};

const StatCard = ({ label, value, accent = C.sapphireDeep, sub }) => (
  <div style={{ ...styles.card, borderTop: `3px solid ${accent}`, flex: 1, minWidth: 180 }}>
    <div style={{ fontSize: 12, color: C.gray500 }}>{label}</div>
    <div style={{ fontSize: 24, fontWeight: 600, marginTop: 6, color: accent }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: C.gray500, marginTop: 4 }}>{sub}</div>}
  </div>
);

const Modal = ({ title, onClose, children, wide }) => (
  <div style={{ position: 'fixed', inset: 0, background: 'rgba(17,24,39,.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
    <div style={{ background: C.white, borderRadius: 16, padding: 24, width: wide ? 760 : 480, maxHeight: '88vh', overflowY: 'auto', fontFamily: "'Cloud', sans-serif" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, color: C.sapphireDeep, fontSize: 17 }}>{title}</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: C.gray500 }}>×</button>
      </div>
      {children}
    </div>
  </div>
);

const Field = ({ label, children }) => (
  <div style={{ marginBottom: 12 }}>
    <label style={styles.label}>{label}</label>
    {children}
  </div>
);

// ── Print receipt (Thai official layout, Buddhist year) ──

function printReceipt(invoice, payment) {
  const isTax = invoice.is_tax_invoice;
  const rows = (invoice.items || []).map((it, i) => `
    <tr>
      <td style="text-align:center">${i + 1}</td>
      <td>${it.description}${it.description_th ? `<br/><span style="color:#555">${it.description_th}</span>` : ''}</td>
      <td style="text-align:center">${Number(it.quantity)}</td>
      <td style="text-align:right">${fmtTHB(it.unit_price)}</td>
      <td style="text-align:right">${fmtTHB(it.line_total)}</td>
    </tr>`).join('');
  const w = window.open('', '_blank');
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${payment ? payment.receipt_number : invoice.invoice_number}</title>
    <style>
      @font-face { font-family:'Cloud'; src:url('/design-system/fonts/Cloud-Regular.ttf'); }
      body { font-family:'Cloud',sans-serif; margin:32px; color:#111827; font-size:13px; }
      .head { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #151667; padding-bottom:12px; }
      .logo { height:56px; }
      h1 { font-size:18px; color:#151667; margin:4px 0; }
      table { width:100%; border-collapse:collapse; margin-top:16px; }
      th { background:#151667; color:#fff; padding:8px; font-weight:500; font-size:12px; }
      td { padding:8px; border-bottom:1px solid #E5E7EB; }
      .totals td { border:none; padding:4px 8px; }
      .grand { font-weight:700; color:#151667; font-size:15px; }
      .foot { margin-top:40px; display:flex; justify-content:space-between; }
      .sig { text-align:center; width:220px; border-top:1px solid #6B7280; padding-top:6px; color:#6B7280; }
    </style></head><body>
    <div class="head">
      <div>
        <img src="/design-system/gold_2026.png" class="logo" alt="Life by Dr. Pat"/>
      </div>
      <div style="text-align:right">
        <h1>${payment ? 'ใบเสร็จรับเงิน / Receipt' : (isTax ? 'ใบแจ้งหนี้-ใบกำกับภาษี / Invoice-Tax Invoice' : 'ใบแจ้งหนี้ / Invoice')}</h1>
        <div>${payment ? `เลขที่ / No: <b>${payment.receipt_number}</b>` : `เลขที่ / No: <b>${invoice.invoice_number}</b>`}</div>
        ${isTax && invoice.tax_invoice_number ? `<div>ใบกำกับภาษีเลขที่: <b>${invoice.tax_invoice_number}</b></div>` : ''}
        <div>วันที่ / Date: ${fmtDateBE(payment ? payment.payment_date : invoice.invoice_date)} (พ.ศ.)</div>
      </div>
    </div>
    <div style="margin-top:12px">
      <div><b>ผู้ป่วย / Patient:</b> ${invoice.billing_name || invoice.patient_id}</div>
      ${invoice.tax_id ? `<div><b>เลขประจำตัวผู้เสียภาษี / Tax ID:</b> ${invoice.tax_id}</div>` : ''}
      ${invoice.billing_address ? `<div>${invoice.billing_address}</div>` : ''}
    </div>
    <table>
      <thead><tr><th style="width:36px">#</th><th>รายการ / Description</th><th style="width:60px">จำนวน</th><th style="width:110px">ราคา/หน่วย</th><th style="width:110px">รวม</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <table class="totals" style="width:320px; margin-left:auto;">
      <tr><td>รวมก่อนส่วนลด / Subtotal</td><td style="text-align:right">${fmtTHB(invoice.subtotal)}</td></tr>
      ${Number(invoice.discount_amount) > 0 ? `<tr><td>ส่วนลด / Discount</td><td style="text-align:right">−${fmtTHB(invoice.discount_amount)}</td></tr>` : ''}
      ${Number(invoice.vat_amount) > 0 ? `<tr><td>ภาษีมูลค่าเพิ่ม / VAT</td><td style="text-align:right">${fmtTHB(invoice.vat_amount)}</td></tr>` : ''}
      <tr class="grand"><td>รวมทั้งสิ้น / Total (THB)</td><td style="text-align:right">${fmtTHB(invoice.total_amount)}</td></tr>
      ${payment ? `<tr><td>ชำระครั้งนี้ / This Payment (${METHOD_LABELS[payment.method] || payment.method})</td><td style="text-align:right">${fmtTHB(payment.amount)}</td></tr>
      <tr><td>ยอดคงเหลือ / Balance</td><td style="text-align:right">${fmtTHB(invoice.balance_due)}</td></tr>` : ''}
    </table>
    <div class="foot">
      <div class="sig">ผู้รับเงิน / Cashier</div>
      <div class="sig">ผู้ชำระเงิน / Payer</div>
    </div>
    <script>window.onload = () => window.print();</script>
    </body></html>`);
  w.document.close();
}

// ── Tabs ──────────────────────────────────────────────────

function DashboardTab() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api('/dashboard').then(setData).catch(e => setErr(e.message)); }, []);
  if (err) return <div style={{ color: C.rubyDark }}>{err}</div>;
  if (!data) return <div style={{ color: C.gray500 }}>Loading…</div>;
  return (
    <div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
        <StatCard label={bi('todayRevenue')} value={`฿${fmtTHB(data.today.total)}`} accent={C.emeraldDark}
                  sub={`${data.today.payment_count} payments / รายการ`} />
        <StatCard label={bi('monthRevenue')} value={`฿${fmtTHB(data.month_revenue)}`} accent={C.sapphireDeep} />
        <StatCard label={bi('monthExpenses')} value={`฿${fmtTHB(data.month_expenses)}`} accent={C.rubyDark} />
        <StatCard label={bi('monthNet')} value={`฿${fmtTHB(data.month_net)}`}
                  accent={Number(data.month_net) >= 0 ? C.emeraldDark : C.rubyDark} />
        <StatCard label={bi('outstanding')} value={`฿${fmtTHB(data.outstanding_total)}`} accent={C.amber}
                  sub={`${data.outstanding_count} invoices / ใบ`} />
      </div>
      <div style={styles.card}>
        <h4 style={{ marginTop: 0, color: C.sapphireDeep }}>Recent Payments / รับชำระล่าสุด</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>{bi('receiptNum')}</th><th style={styles.th}>{bi('date')}</th>
            <th style={styles.th}>{bi('method')}</th><th style={{ ...styles.th, textAlign: 'right' }}>{bi('amount')}</th>
          </tr></thead>
          <tbody>
            {data.recent_payments.map(p => (
              <tr key={p.id}>
                <td style={styles.td}>{p.receipt_number}</td>
                <td style={styles.td}>{p.payment_date}</td>
                <td style={styles.td}>{METHOD_LABELS[p.method] || p.method}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(p.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InvoicesTab() {
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [detail, setDetail] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showPay, setShowPay] = useState(null);
  const [err, setErr] = useState('');

  const load = useCallback(() => {
    const q = new URLSearchParams();
    if (search) q.set('search', search);
    if (status) q.set('status', status);
    api(`/invoices?${q}`).then(d => setRows(d.items)).catch(e => setErr(e.message));
  }, [search, status]);
  useEffect(load, [load]);

  const openDetail = (id) => api(`/invoices/${id}`).then(setDetail).catch(e => setErr(e.message));

  const voidInvoice = async (inv) => {
    const reason = window.prompt('Void reason / เหตุผลการยกเลิก:');
    if (!reason) return;
    try {
      await api(`/invoices/${inv.id}/void`, { method: 'POST', body: JSON.stringify({ void_reason: reason }) });
      load(); setDetail(null);
    } catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input style={{ ...styles.input, width: 220 }} placeholder={bi('search')}
               value={search} onChange={e => setSearch(e.target.value)} />
        <select style={{ ...styles.input, width: 200 }} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">All / ทั้งหมด</option>
          {Object.keys(STATUS_LABELS).map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <button style={styles.btnPrimary} onClick={() => setShowCreate(true)}>+ {bi('newInvoice')}</button>
      </div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>{bi('invoiceNum')}</th><th style={styles.th}>{bi('date')}</th>
            <th style={styles.th}>{bi('status')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('total')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('balance')}</th>
            <th style={styles.th}>{bi('actions')}</th>
          </tr></thead>
          <tbody>
            {rows.map(inv => (
              <tr key={inv.id}>
                <td style={{ ...styles.td, color: C.sapphire, cursor: 'pointer' }}
                    onClick={() => openDetail(inv.id)}>{inv.invoice_number}</td>
                <td style={styles.td}>{inv.invoice_date}</td>
                <td style={styles.td}><Badge status={inv.status} /></td>
                <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(inv.total_amount)}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(inv.balance_due)}</td>
                <td style={styles.td}>
                  {['issued', 'partially_paid'].includes(inv.status) &&
                    <button style={{ ...styles.btnGhost, marginRight: 6 }}
                            onClick={() => setShowPay(inv)}>{bi('recordPayment')}</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && <InvoiceCreateModal onClose={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); load(); }} />}
      {showPay && <PaymentModal invoice={showPay} onClose={() => setShowPay(null)}
                                onSaved={() => { setShowPay(null); load(); }} />}
      {detail && (
        <Modal title={`${detail.invoice_number} — ${STATUS_LABELS[detail.status] || detail.status}`} wide
               onClose={() => setDetail(null)}>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 12 }}>
            <thead><tr>
              <th style={styles.th}>{bi('description')}</th><th style={styles.th}>{bi('qty')}</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>{bi('unitPrice')}</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>{bi('lineTotal')}</th>
            </tr></thead>
            <tbody>{detail.items.map(it => (
              <tr key={it.id}>
                <td style={styles.td}>{it.description}{it.description_th && <div style={{ color: C.gray500, fontSize: 12 }}>{it.description_th}</div>}</td>
                <td style={styles.td}>{Number(it.quantity)}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(it.unit_price)}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(it.line_total)}</td>
              </tr>))}
            </tbody>
          </table>
          <div style={{ textAlign: 'right', fontSize: 14, lineHeight: 1.9 }}>
            <div>{bi('subtotal')}: ฿{fmtTHB(detail.subtotal)}</div>
            {Number(detail.discount_amount) > 0 && <div>{bi('discount')}: −฿{fmtTHB(detail.discount_amount)}</div>}
            {Number(detail.vat_amount) > 0 && <div>{bi('vat')}: ฿{fmtTHB(detail.vat_amount)}</div>}
            <div style={{ fontWeight: 700, color: C.sapphireDeep }}>{bi('total')}: ฿{fmtTHB(detail.total_amount)}</div>
            <div style={{ color: C.emeraldDark }}>{bi('paid')}: ฿{fmtTHB(detail.paid_amount)}</div>
            <div style={{ color: C.rubyDark }}>{bi('balance')}: ฿{fmtTHB(detail.balance_due)}</div>
          </div>
          {detail.payments?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <b>Receipts / ใบเสร็จ:</b>
              {detail.payments.map(p => (
                <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${C.gray200}`, fontSize: 13 }}>
                  <span>{p.receipt_number} · {p.payment_date} · {METHOD_LABELS[p.method] || p.method}{p.is_void ? ' · VOID' : ''}</span>
                  <span>
                    ฿{fmtTHB(p.amount)}
                    {!p.is_void && <button style={{ ...styles.btnGhost, marginLeft: 10, padding: '3px 8px', fontSize: 11 }}
                                           onClick={() => printReceipt(detail, p)}>{bi('printReceipt')}</button>}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, marginTop: 18, justifyContent: 'flex-end' }}>
            <button style={styles.btnGhost} onClick={() => printReceipt(detail, null)}>Print Invoice / พิมพ์ใบแจ้งหนี้</button>
            {['draft', 'issued'].includes(detail.status) && Number(detail.paid_amount) === 0 &&
              <button style={styles.btnDanger} onClick={() => voidInvoice(detail)}>{bi('void')}</button>}
          </div>
        </Modal>
      )}
    </div>
  );
}

function InvoiceCreateModal({ onClose, onSaved }) {
  const [services, setServices] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [items, setItems] = useState([{ service_id: '', description: '', description_th: '', quantity: 1, unit_price: 0, vat_rate: 0 }]);
  const [discount, setDiscount] = useState(0);
  const [isTax, setIsTax] = useState(false);
  const [taxId, setTaxId] = useState('');
  const [billingName, setBillingName] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => { api('/services?active=true&limit=500').then(d => setServices(d.items)).catch(() => {}); }, []);

  const setItem = (i, patch) => setItems(list => list.map((it, idx) => idx === i ? { ...it, ...patch } : it));
  const pickService = (i, id) => {
    const svc = services.find(s => s.id === id);
    if (svc) setItem(i, { service_id: id, description: svc.name_en, description_th: svc.name_th || '', unit_price: Number(svc.unit_price), vat_rate: Number(svc.vat_rate) });
    else setItem(i, { service_id: '' });
  };
  const subtotal = items.reduce((s, it) => s + Number(it.quantity) * Number(it.unit_price), 0);
  const vat = items.reduce((s, it) => s + Number(it.quantity) * Number(it.unit_price) * Number(it.vat_rate) / 100, 0);
  const total = subtotal - Number(discount) + vat;

  const save = async () => {
    try {
      await api('/invoices', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          items: items.filter(it => it.description),
          discount_amount: Number(discount) || 0,
          is_tax_invoice: isTax, tax_id: taxId || null, billing_name: billingName || null,
        }),
      });
      onSaved();
    } catch (e) { setErr(e.message); }
  };

  return (
    <Modal title={bi('newInvoice')} wide onClose={onClose}>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Field label="Patient ID / รหัสผู้ป่วย">
          <input style={styles.input} value={patientId} onChange={e => setPatientId(e.target.value)} />
        </Field>
        <Field label="Billing Name / ชื่อในใบเสร็จ">
          <input style={styles.input} value={billingName} onChange={e => setBillingName(e.target.value)} />
        </Field>
      </div>
      {items.map((it, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 70px 110px 70px', gap: 8, marginBottom: 8, alignItems: 'end' }}>
          <div>
            <label style={styles.label}>{bi('service')}</label>
            <select style={styles.input} value={it.service_id} onChange={e => pickService(i, e.target.value)}>
              <option value="">— custom / กำหนดเอง —</option>
              {services.map(s => <option key={s.id} value={s.id}>{s.service_code} · {s.name_en}</option>)}
            </select>
          </div>
          <div>
            <label style={styles.label}>{bi('description')}</label>
            <input style={styles.input} value={it.description} onChange={e => setItem(i, { description: e.target.value })} />
          </div>
          <div>
            <label style={styles.label}>{bi('qty')}</label>
            <input style={styles.input} type="number" min="0" value={it.quantity} onChange={e => setItem(i, { quantity: e.target.value })} />
          </div>
          <div>
            <label style={styles.label}>{bi('unitPrice')}</label>
            <input style={styles.input} type="number" min="0" value={it.unit_price} onChange={e => setItem(i, { unit_price: e.target.value })} />
          </div>
          <div>
            <label style={styles.label}>VAT %</label>
            <input style={styles.input} type="number" min="0" value={it.vat_rate} onChange={e => setItem(i, { vat_rate: e.target.value })} />
          </div>
        </div>
      ))}
      <button style={{ ...styles.btnGhost, marginBottom: 14 }}
              onClick={() => setItems([...items, { service_id: '', description: '', description_th: '', quantity: 1, unit_price: 0, vat_rate: 0 }])}>
        + {bi('addLine')}
      </button>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <Field label={`${bi('discount')} (฿)`}>
          <input style={styles.input} type="number" min="0" value={discount} onChange={e => setDiscount(e.target.value)} />
        </Field>
        <Field label={bi('taxInvoice')}>
          <label style={{ fontSize: 13 }}>
            <input type="checkbox" checked={isTax} onChange={e => setIsTax(e.target.checked)} /> ออกใบกำกับภาษี
          </label>
        </Field>
        {isTax && <Field label="Tax ID / เลขผู้เสียภาษี">
          <input style={styles.input} value={taxId} onChange={e => setTaxId(e.target.value)} />
        </Field>}
      </div>
      <div style={{ textAlign: 'right', fontSize: 14, lineHeight: 1.8, marginTop: 8 }}>
        <div>{bi('subtotal')}: ฿{fmtTHB(subtotal)}</div>
        <div>{bi('vat')}: ฿{fmtTHB(vat)}</div>
        <div style={{ fontWeight: 700, color: C.sapphireDeep }}>{bi('total')}: ฿{fmtTHB(total)}</div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
        <button style={styles.btnGhost} onClick={onClose}>{bi('cancel')}</button>
        <button style={styles.btnPrimary} onClick={save} disabled={!patientId}>{bi('save')}</button>
      </div>
    </Modal>
  );
}

function PaymentModal({ invoice, onClose, onSaved }) {
  const [amount, setAmount] = useState(Number(invoice.balance_due));
  const [method, setMethod] = useState('cash');
  const [reference, setReference] = useState('');
  const [err, setErr] = useState('');
  const save = async () => {
    try {
      const pay = await api('/payments', {
        method: 'POST',
        body: JSON.stringify({ invoice_id: invoice.id, amount: Number(amount), method, reference_number: reference || null }),
      });
      const full = await api(`/invoices/${invoice.id}`);
      printReceipt(full, pay);
      onSaved();
    } catch (e) { setErr(e.message); }
  };
  return (
    <Modal title={`${bi('recordPayment')} — ${invoice.invoice_number}`} onClose={onClose}>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ marginBottom: 12, fontSize: 13, color: C.gray500 }}>
        {bi('balance')}: <b style={{ color: C.rubyDark }}>฿{fmtTHB(invoice.balance_due)}</b>
      </div>
      <Field label={bi('amount')}>
        <input style={styles.input} type="number" min="0" value={amount} onChange={e => setAmount(e.target.value)} />
      </Field>
      <Field label={bi('method')}>
        <select style={styles.input} value={method} onChange={e => setMethod(e.target.value)}>
          {Object.keys(METHOD_LABELS).map(m => <option key={m} value={m}>{METHOD_LABELS[m]}</option>)}
        </select>
      </Field>
      <Field label={bi('reference')}>
        <input style={styles.input} value={reference} onChange={e => setReference(e.target.value)} />
      </Field>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button style={styles.btnGhost} onClick={onClose}>{bi('cancel')}</button>
        <button style={styles.btnPrimary} onClick={save}>{bi('save')} & {bi('printReceipt')}</button>
      </div>
    </Modal>
  );
}

function PaymentsTab() {
  const [rows, setRows] = useState([]);
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [method, setMethod] = useState('');
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    const q = new URLSearchParams();
    if (from) q.set('date_from', from);
    if (to) q.set('date_to', to);
    if (method) q.set('method', method);
    api(`/payments?${q}`).then(d => setRows(d.items)).catch(e => setErr(e.message));
  }, [from, to, method]);
  useEffect(load, [load]);
  const voidPayment = async (p) => {
    const reason = window.prompt('Void reason / เหตุผลการยกเลิก:');
    if (!reason) return;
    try {
      await api(`/payments/${p.id}/void`, { method: 'POST', body: JSON.stringify({ void_reason: reason }) });
      load();
    } catch (e) { setErr(e.message); }
  };
  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input style={{ ...styles.input, width: 160 }} type="date" value={from} onChange={e => setFrom(e.target.value)} />
        <input style={{ ...styles.input, width: 160 }} type="date" value={to} onChange={e => setTo(e.target.value)} />
        <select style={{ ...styles.input, width: 200 }} value={method} onChange={e => setMethod(e.target.value)}>
          <option value="">All / ทั้งหมด</option>
          {Object.keys(METHOD_LABELS).map(m => <option key={m} value={m}>{METHOD_LABELS[m]}</option>)}
        </select>
      </div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>{bi('receiptNum')}</th><th style={styles.th}>{bi('date')}</th>
            <th style={styles.th}>{bi('method')}</th><th style={styles.th}>{bi('reference')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('amount')}</th>
            <th style={styles.th}>{bi('actions')}</th>
          </tr></thead>
          <tbody>{rows.map(p => (
            <tr key={p.id}>
              <td style={styles.td}>{p.receipt_number}</td>
              <td style={styles.td}>{p.payment_date}</td>
              <td style={styles.td}>{METHOD_LABELS[p.method] || p.method}</td>
              <td style={styles.td}>{p.reference_number || '—'}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(p.amount)}</td>
              <td style={styles.td}>
                <button style={styles.btnDanger} onClick={() => voidPayment(p)}>{bi('void')}</button>
              </td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ServicesTab() {
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [edit, setEdit] = useState(null);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    const q = new URLSearchParams({ limit: 500 });
    if (search) q.set('search', search);
    if (category) q.set('category', category);
    api(`/services?${q}`).then(d => setRows(d.items)).catch(e => setErr(e.message));
  }, [search, category]);
  useEffect(load, [load]);

  const importCSV = async (file) => {
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(`${API}/services/import-csv`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('fcms_token') || ''}` },
        body: fd,
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Import failed');
      alert(`Created ${d.created}, updated ${d.updated}${d.errors.length ? `\nErrors:\n${d.errors.join('\n')}` : ''}`);
      load();
    } catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input style={{ ...styles.input, width: 220 }} placeholder={bi('search')} value={search} onChange={e => setSearch(e.target.value)} />
        <select style={{ ...styles.input, width: 240 }} value={category} onChange={e => setCategory(e.target.value)}>
          <option value="">All / ทั้งหมด</option>
          {Object.keys(SVC_CATEGORIES).map(c => <option key={c} value={c}>{SVC_CATEGORIES[c]}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <label style={{ ...styles.btnGhost, display: 'inline-block' }}>
          {bi('importCSV')}
          <input type="file" accept=".csv" style={{ display: 'none' }}
                 onChange={e => e.target.files[0] && importCSV(e.target.files[0])} />
        </label>
        <button style={styles.btnPrimary} onClick={() => setShowCreate(true)}>+ {bi('newService')}</button>
      </div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>{bi('code')}</th><th style={styles.th}>{bi('service')}</th>
            <th style={styles.th}>{bi('category')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('unitPrice')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>VAT %</th>
            <th style={styles.th}>{bi('actions')}</th>
          </tr></thead>
          <tbody>{rows.map(s => (
            <tr key={s.id} style={{ opacity: s.active ? 1 : 0.5 }}>
              <td style={styles.td}>{s.service_code}</td>
              <td style={styles.td}>{s.name_en}{s.name_th && <div style={{ color: C.gray500, fontSize: 12 }}>{s.name_th}</div>}</td>
              <td style={styles.td}>{SVC_CATEGORIES[s.category] || s.category}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(s.unit_price)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>{Number(s.vat_rate)}</td>
              <td style={styles.td}>
                <button style={styles.btnGhost} onClick={() => setEdit(s)}>Edit / แก้ไข</button>
              </td>
            </tr>))}
          </tbody>
        </table>
      </div>
      {(showCreate || edit) && (
        <ServiceModal service={edit} onClose={() => { setShowCreate(false); setEdit(null); }}
                      onSaved={() => { setShowCreate(false); setEdit(null); load(); }} />
      )}
    </div>
  );
}

function ServiceModal({ service, onClose, onSaved }) {
  const [f, setF] = useState(service ? { ...service, unit_price: Number(service.unit_price), vat_rate: Number(service.vat_rate) }
    : { name_en: '', name_th: '', category: 'consultation', unit_price: 0, vat_rate: 0, active: true });
  const [err, setErr] = useState('');
  const save = async () => {
    try {
      if (service) {
        await api(`/services/${service.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            name_en: f.name_en, name_th: f.name_th || null, category: f.category,
            unit_price: Number(f.unit_price), vat_rate: Number(f.vat_rate), active: f.active,
          }),
        });
      } else {
        await api('/services', {
          method: 'POST',
          body: JSON.stringify({
            name_en: f.name_en, name_th: f.name_th || null, category: f.category,
            unit_price: Number(f.unit_price), vat_rate: Number(f.vat_rate), active: f.active,
          }),
        });
      }
      onSaved();
    } catch (e) { setErr(e.message); }
  };
  return (
    <Modal title={service ? `Edit / แก้ไข — ${service.service_code}` : bi('newService')} onClose={onClose}>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <Field label="Name (EN)"><input style={styles.input} value={f.name_en} onChange={e => setF({ ...f, name_en: e.target.value })} /></Field>
      <Field label="Name (TH) / ชื่อไทย"><input style={styles.input} value={f.name_th || ''} onChange={e => setF({ ...f, name_th: e.target.value })} /></Field>
      <Field label={bi('category')}>
        <select style={styles.input} value={f.category} onChange={e => setF({ ...f, category: e.target.value })}>
          {Object.keys(SVC_CATEGORIES).map(c => <option key={c} value={c}>{SVC_CATEGORIES[c]}</option>)}
        </select>
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Field label={`${bi('unitPrice')} (฿)`}><input style={styles.input} type="number" min="0" value={f.unit_price} onChange={e => setF({ ...f, unit_price: e.target.value })} /></Field>
        <Field label="VAT % (0 = medical exempt / ยกเว้น)"><input style={styles.input} type="number" min="0" value={f.vat_rate} onChange={e => setF({ ...f, vat_rate: e.target.value })} /></Field>
      </div>
      <Field label="">
        <label style={{ fontSize: 13 }}><input type="checkbox" checked={!!f.active} onChange={e => setF({ ...f, active: e.target.checked })} /> Active / ใช้งาน</label>
      </Field>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button style={styles.btnGhost} onClick={onClose}>{bi('cancel')}</button>
        <button style={styles.btnPrimary} onClick={save} disabled={!f.name_en}>{bi('save')}</button>
      </div>
    </Modal>
  );
}

function ExpensesTab() {
  const [rows, setRows] = useState([]);
  const [category, setCategory] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    const q = new URLSearchParams();
    if (category) q.set('category', category);
    api(`/expenses?${q}`).then(d => setRows(d.items)).catch(e => setErr(e.message));
  }, [category]);
  useEffect(load, [load]);
  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <select style={{ ...styles.input, width: 260 }} value={category} onChange={e => setCategory(e.target.value)}>
          <option value="">All / ทั้งหมด</option>
          {Object.keys(EXP_CATEGORIES).map(c => <option key={c} value={c}>{EXP_CATEGORIES[c]}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <button style={styles.btnPrimary} onClick={() => setShowCreate(true)}>+ {bi('newExpense')}</button>
      </div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>#</th><th style={styles.th}>{bi('date')}</th>
            <th style={styles.th}>{bi('category')}</th><th style={styles.th}>{bi('vendor')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('amount')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('wht')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('netPaid')}</th>
          </tr></thead>
          <tbody>{rows.map(x => (
            <tr key={x.id}>
              <td style={styles.td}>{x.expense_number}</td>
              <td style={styles.td}>{x.expense_date}</td>
              <td style={styles.td}>{EXP_CATEGORIES[x.category] || x.category}</td>
              <td style={styles.td}>{x.vendor_name || '—'}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(x.amount)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(x.withholding_tax_amount)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(x.net_paid)}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
      {showCreate && <ExpenseModal onClose={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); load(); }} />}
    </div>
  );
}

function ExpenseModal({ onClose, onSaved }) {
  const [f, setF] = useState({ category: 'medical_supplies', vendor_name: '', description: '', description_th: '', amount: 0, vat_amount: 0, withholding_tax_rate: 0, payment_method: 'bank_transfer' });
  const [err, setErr] = useState('');
  const save = async () => {
    try {
      await api('/expenses', {
        method: 'POST',
        body: JSON.stringify({ ...f, amount: Number(f.amount), vat_amount: Number(f.vat_amount), withholding_tax_rate: Number(f.withholding_tax_rate) }),
      });
      onSaved();
    } catch (e) { setErr(e.message); }
  };
  return (
    <Modal title={bi('newExpense')} onClose={onClose}>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <Field label={bi('category')}>
        <select style={styles.input} value={f.category} onChange={e => setF({ ...f, category: e.target.value })}>
          {Object.keys(EXP_CATEGORIES).map(c => <option key={c} value={c}>{EXP_CATEGORIES[c]}</option>)}
        </select>
      </Field>
      <Field label={bi('vendor')}><input style={styles.input} value={f.vendor_name} onChange={e => setF({ ...f, vendor_name: e.target.value })} /></Field>
      <Field label={`${bi('description')} (EN)`}><input style={styles.input} value={f.description} onChange={e => setF({ ...f, description: e.target.value })} /></Field>
      <Field label={`${bi('description')} (TH)`}><input style={styles.input} value={f.description_th} onChange={e => setF({ ...f, description_th: e.target.value })} /></Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <Field label={`${bi('amount')} (฿)`}><input style={styles.input} type="number" min="0" value={f.amount} onChange={e => setF({ ...f, amount: e.target.value })} /></Field>
        <Field label="VAT (฿)"><input style={styles.input} type="number" min="0" value={f.vat_amount} onChange={e => setF({ ...f, vat_amount: e.target.value })} /></Field>
        <Field label={`${bi('wht')} %`}>
          <select style={styles.input} value={f.withholding_tax_rate} onChange={e => setF({ ...f, withholding_tax_rate: e.target.value })}>
            {[0, 1, 2, 3, 5].map(r => <option key={r} value={r}>{r}%</option>)}
          </select>
        </Field>
      </div>
      <Field label={bi('method')}>
        <select style={styles.input} value={f.payment_method} onChange={e => setF({ ...f, payment_method: e.target.value })}>
          {Object.keys(METHOD_LABELS).map(m => <option key={m} value={m}>{METHOD_LABELS[m]}</option>)}
        </select>
      </Field>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button style={styles.btnGhost} onClick={onClose}>{bi('cancel')}</button>
        <button style={styles.btnPrimary} onClick={save} disabled={!f.description || !Number(f.amount)}>{bi('save')}</button>
      </div>
    </Modal>
  );
}

function ReportsTab() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [pl, setPl] = useState(null);
  const [ar, setAr] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    api(`/reports/monthly-pl?year=${year}&month=${month}`).then(setPl).catch(e => setErr(e.message));
  }, [year, month]);
  useEffect(() => { api('/reports/outstanding').then(setAr).catch(() => {}); }, []);
  return (
    <div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <select style={{ ...styles.input, width: 120 }} value={year} onChange={e => setYear(Number(e.target.value))}>
          {[year - 2, year - 1, year, year + 1].filter((v, i, a) => a.indexOf(v) === i)
            .map(y => <option key={y} value={y}>{y} / พ.ศ. {y + 543}</option>)}
        </select>
        <select style={{ ...styles.input, width: 100 }} value={month} onChange={e => setMonth(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, i) => i + 1).map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>
      {pl && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
          <div style={{ ...styles.card, flex: 1, minWidth: 300 }}>
            <h4 style={{ marginTop: 0, color: C.sapphireDeep }}>{bi('monthlyPL')} — {pl.period}</h4>
            <div style={{ fontSize: 14, lineHeight: 2 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Revenue Received / รายรับ (เงินสดรับจริง)</span>
                <b style={{ color: C.emeraldDark }}>฿{fmtTHB(pl.revenue_received)}</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Total Expenses / รายจ่ายรวม</span>
                <b style={{ color: C.rubyDark }}>฿{fmtTHB(pl.total_expenses)}</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: `2px solid ${C.sapphireDeep}`, paddingTop: 6 }}>
                <span><b>Net / กำไรสุทธิ</b></span>
                <b style={{ color: Number(pl.net) >= 0 ? C.emeraldDark : C.rubyDark }}>฿{fmtTHB(pl.net)}</b>
              </div>
            </div>
            <h5 style={{ color: C.gray500, marginBottom: 4 }}>Billed by Category / ยอดเรียกเก็บตามหมวด</h5>
            {Object.entries(pl.billed_by_category).map(([c, v]) => (
              <div key={c} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '3px 0' }}>
                <span>{SVC_CATEGORIES[c] || c}</span><span>฿{fmtTHB(v)}</span>
              </div>))}
            <h5 style={{ color: C.gray500, marginBottom: 4 }}>Expenses by Category / รายจ่ายตามหมวด</h5>
            {Object.entries(pl.expenses_by_category).map(([c, v]) => (
              <div key={c} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '3px 0' }}>
                <span>{EXP_CATEGORIES[c] || c}</span><span>฿{fmtTHB(v)}</span>
              </div>))}
          </div>
          {ar && (
            <div style={{ ...styles.card, flex: 1, minWidth: 300 }}>
              <h4 style={{ marginTop: 0, color: C.sapphireDeep }}>{bi('arAging')} — as of {ar.as_of}</h4>
              {[['0_30', '0–30 days / วัน'], ['31_60', '31–60 days / วัน'],
                ['61_90', '61–90 days / วัน'], ['over_90', '90+ days / วัน']].map(([k, lbl]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '6px 0', borderBottom: `1px solid ${C.gray200}` }}>
                  <span>{lbl}</span><b>฿{fmtTHB(ar.buckets[k])}</b>
                </div>))}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, paddingTop: 8 }}>
                <b>{bi('outstanding')}</b><b style={{ color: C.rubyDark }}>฿{fmtTHB(ar.total)}</b>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ClosingTab() {
  const [closings, setClosings] = useState([]);
  const [today, setToday] = useState(null);
  const [counted, setCounted] = useState('');
  const [notes, setNotes] = useState('');
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    api('/closings').then(d => setClosings(d.items)).catch(e => setErr(e.message));
    api('/reports/daily').then(setToday).catch(() => {});
  }, []);
  useEffect(load, [load]);
  const close = async () => {
    try {
      await api('/closings', { method: 'POST', body: JSON.stringify({ cash_counted: Number(counted) || 0, notes: notes || null }) });
      setCounted(''); setNotes(''); load();
    } catch (e) { setErr(e.message); }
  };
  return (
    <div>
      {err && <div style={{ color: C.rubyDark, marginBottom: 10 }}>{err}</div>}
      {today && (
        <div style={{ ...styles.card, marginBottom: 20 }}>
          <h4 style={{ marginTop: 0, color: C.sapphireDeep }}>Today / วันนี้ — {today.date}</h4>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 14 }}>
            <span>Cash / เงินสด: <b>฿{fmtTHB(today.totals.cash)}</b></span>
            <span>Card / บัตร: <b>฿{fmtTHB(today.totals.card)}</b></span>
            <span>Transfer / โอน: <b>฿{fmtTHB(today.totals.transfer)}</b></span>
            <span>PromptPay: <b>฿{fmtTHB(today.totals.promptpay)}</b></span>
            <span>Total / รวม: <b style={{ color: C.emeraldDark }}>฿{fmtTHB(today.totals.total)}</b></span>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 14, alignItems: 'flex-end' }}>
            <div style={{ width: 200 }}>
              <label style={styles.label}>{bi('cashCounted')} (฿)</label>
              <input style={styles.input} type="number" min="0" value={counted} onChange={e => setCounted(e.target.value)} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={styles.label}>{bi('notes')}</label>
              <input style={styles.input} value={notes} onChange={e => setNotes(e.target.value)} />
            </div>
            <button style={styles.btnPrimary} onClick={close}>{bi('closeDay')}</button>
          </div>
        </div>
      )}
      <div style={{ ...styles.card, padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead><tr>
            <th style={styles.th}>{bi('date')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('cashExpected')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('cashCounted')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('variance')}</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Card</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Transfer</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>PromptPay</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>{bi('total')}</th>
          </tr></thead>
          <tbody>{closings.map(cl => (
            <tr key={cl.id}>
              <td style={styles.td}>{cl.closing_date}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(cl.cash_expected)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(cl.cash_counted)}</td>
              <td style={{ ...styles.td, textAlign: 'right', color: Number(cl.cash_variance) === 0 ? C.emeraldDark : C.rubyDark }}>
                ฿{fmtTHB(cl.cash_variance)}
              </td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(cl.card_total)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(cl.transfer_total)}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>฿{fmtTHB(cl.promptpay_total)}</td>
              <td style={{ ...styles.td, textAlign: 'right', fontWeight: 600 }}>฿{fmtTHB(cl.total_revenue)}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────

const TABS = [
  { key: 'dashboard', icon: '📊' }, { key: 'invoices', icon: '🧾' },
  { key: 'payments', icon: '💳' }, { key: 'services', icon: '🏷️' },
  { key: 'expenses', icon: '📤' }, { key: 'reports', icon: '📈' },
  { key: 'closing', icon: '🔒' },
];

export default function AccountingDashboard() {
  const [tab, setTab] = useState('dashboard');
  return (
    <div style={{ ...styles.page, display: 'flex' }}>
      {/* Ruby sidebar */}
      <aside style={{ width: 230, background: C.ruby, color: C.white, padding: '20px 0', minHeight: '100vh' }}>
        <div style={{ padding: '0 20px 20px', borderBottom: '1px solid rgba(255,255,255,.25)', marginBottom: 12 }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Accounting</div>
          <div style={{ fontSize: 13, opacity: .9 }}>ระบบบัญชี</div>
        </div>
        {TABS.map(t => (
          <div key={t.key} onClick={() => setTab(t.key)}
               style={{
                 padding: '11px 20px', cursor: 'pointer', fontSize: 14,
                 background: tab === t.key ? C.rubyDark : 'transparent',
                 borderLeft: tab === t.key ? `4px solid ${C.white}` : '4px solid transparent',
               }}>
            <span style={{ marginRight: 8 }}>{t.icon}</span>{bi(t.key)}
          </div>
        ))}
      </aside>
      <main style={{ flex: 1, padding: 28 }}>
        <h2 style={{ marginTop: 0, color: C.sapphireDeep }}>{bi(tab)}</h2>
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'invoices' && <InvoicesTab />}
        {tab === 'payments' && <PaymentsTab />}
        {tab === 'services' && <ServicesTab />}
        {tab === 'expenses' && <ExpensesTab />}
        {tab === 'reports' && <ReportsTab />}
        {tab === 'closing' && <ClosingTab />}
      </main>
    </div>
  );
}
