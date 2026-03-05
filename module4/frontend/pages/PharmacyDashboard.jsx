/**
 * FCMS Module 4 — Pharmacy Dashboard / เภสัชกรรม
 *
 * Features:
 *  - Drug catalogue with search, category filter
 *  - Stock levels with low-stock/expiry alerts
 *  - Prescription queue (pending → verify → dispense)
 *  - Dispensing workflow with lot selection
 *  - Medication label preview (bilingual TH/EN)
 *  - Add new drug / receive stock modals
 *  - Dashboard stats
 *
 * Design: Cloud font, FCMS color tokens (Sapphire/Emerald/Ruby)
 */

import React, { useState } from 'react';

const T = {
  ruby:'#E0115F', rubyDark:'#A00040', rubyMuted:'#FCE4EE',
  emerald:'#009473', emeraldVivid:'#50C878', emeraldDark:'#006B54', emeraldMuted:'#E0F5EF',
  sapphire:'#0F52BA', sapphireDeep:'#151667', sapphireLight:'#4A7FD4', sapphireMuted:'#E8EEFA',
  gold:'#C5A044',
  warning:'#F59E0B', warningMuted:'#FEF3C7',
  g900:'#111827', g700:'#374151', g500:'#6B7280', g400:'#9CA3AF', g300:'#D1D5DB', g200:'#E5E7EB', g100:'#F3F4F6', g50:'#F9FAFB', white:'#FFFFFF',
};
const FONT = "'Cloud', -apple-system, BlinkMacSystemFont, sans-serif";
const R = { sm:'6px', md:'10px', lg:'16px' };

const CATEGORIES = [
  {v:'hormonal', en:'Hormonal', th:'ฮอร์โมน', color:T.sapphire},
  {v:'ivf_protocol', en:'IVF Protocol', th:'โปรโตคอล IVF', color:T.emerald},
  {v:'antibiotic', en:'Antibiotic', th:'ยาปฏิชีวนะ', color:T.ruby},
  {v:'analgesic', en:'Analgesic', th:'ยาแก้ปวด', color:T.warning},
  {v:'vitamin', en:'Vitamin/Supplement', th:'วิตามิน', color:T.emeraldVivid},
  {v:'anesthetic', en:'Anesthetic', th:'ยาชา', color:T.sapphireDeep},
  {v:'anticoagulant', en:'Anticoagulant', th:'ยาต้านการแข็งตัว', color:T.rubyDark},
  {v:'other', en:'Other', th:'อื่นๆ', color:T.g500},
];

const DEMO_DRUGS = [
  {id:'D1', name_generic:'Letrozole', name_brand:'Femara', name_thai:'เลโตรโซล', category:'ivf_protocol', form:'tablet', strength:'2.5mg', stock:450, reorder:100, price:45, expiry:'2027-03-15', lot:'LOT-2026-001', storage:'room_temperature'},
  {id:'D2', name_generic:'Progesterone', name_brand:'Utrogestan', name_thai:'โปรเจสเตอโรน', category:'hormonal', form:'capsule', strength:'200mg', stock:280, reorder:150, price:65, expiry:'2026-12-30', lot:'LOT-2025-089', storage:'room_temperature'},
  {id:'D3', name_generic:'Medroxyprogesterone', name_brand:'Provera', name_thai:'เมดรอกซีโปรเจสเตอโรน', category:'hormonal', form:'tablet', strength:'10mg', stock:320, reorder:100, price:35, expiry:'2027-06-20', lot:'LOT-2026-012', storage:'room_temperature'},
  {id:'D4', name_generic:'Cetrotide (Cetrorelix)', name_brand:'Cetrotide', name_thai:'เซโทรไทด์', category:'ivf_protocol', form:'injection', strength:'0.25mg', stock:45, reorder:50, price:1800, expiry:'2026-05-10', lot:'LOT-2025-112', storage:'refrigerated'},
  {id:'D5', name_generic:'Gonal-F (Follitropin alfa)', name_brand:'Gonal-F', name_thai:'โกนาล-เอฟ', category:'ivf_protocol', form:'injection', strength:'300IU', stock:30, reorder:40, price:4500, expiry:'2026-06-15', lot:'LOT-2026-003', storage:'refrigerated'},
  {id:'D6', name_generic:'hCG (Choriogonadotropin)', name_brand:'Ovidrel', name_thai:'โอวิเดรล', category:'ivf_protocol', form:'injection', strength:'250mcg', stock:25, reorder:20, price:2200, expiry:'2026-08-20', lot:'LOT-2026-005', storage:'refrigerated'},
  {id:'D7', name_generic:'Doxycycline', name_brand:'Vibramycin', name_thai:'ดอกซีไซคลิน', category:'antibiotic', form:'capsule', strength:'100mg', stock:500, reorder:200, price:12, expiry:'2027-09-10', lot:'LOT-2026-020', storage:'room_temperature'},
  {id:'D8', name_generic:'Folic Acid', name_brand:'Folvite', name_thai:'โฟลิค แอซิด', category:'vitamin', form:'tablet', strength:'5mg', stock:1200, reorder:300, price:5, expiry:'2028-01-01', lot:'LOT-2026-030', storage:'room_temperature'},
  {id:'D9', name_generic:'Paracetamol', name_brand:'Tylenol', name_thai:'พาราเซตามอล', category:'analgesic', form:'tablet', strength:'500mg', stock:800, reorder:200, price:3, expiry:'2027-11-30', lot:'LOT-2026-025', storage:'room_temperature'},
  {id:'D10', name_generic:'Enoxaparin', name_brand:'Clexane', name_thai:'อีนอกซาพาริน', category:'anticoagulant', form:'injection', strength:'40mg', stock:15, reorder:20, price:950, expiry:'2026-04-20', lot:'LOT-2025-098', storage:'refrigerated'},
];

const DEMO_RX = [
  {id:'RX1', patient:'Patsama V.', hn:'HN-00001', prescriber:'Dr. Pat', date:'2026-03-05', status:'pending', items:[{drug:'Letrozole 2.5mg', qty:10, freq:'Once daily x5 days'},{drug:'Folic Acid 5mg', qty:30, freq:'Once daily'}]},
  {id:'RX2', patient:'Nattaya S.', hn:'HN-00045', prescriber:'Dr. Pat', date:'2026-03-05', status:'pending', items:[{drug:'Gonal-F 300IU', qty:5, freq:'Daily injection'},{drug:'Cetrotide 0.25mg', qty:4, freq:'Daily from Day 6'}]},
  {id:'RX3', patient:'Malai C.', hn:'HN-00078', prescriber:'Dr. Pat', date:'2026-03-04', status:'verified', items:[{drug:'Progesterone 200mg', qty:28, freq:'Twice daily'}]},
  {id:'RX4', patient:'Jiraporn K.', hn:'HN-00023', prescriber:'Dr. Pat', date:'2026-03-03', status:'dispensed', items:[{drug:'Doxycycline 100mg', qty:14, freq:'Twice daily x7 days'}]},
];

// Shared styles
const inp = { width:'100%', padding:'10px 14px', border:`1.5px solid ${T.g200}`, borderRadius:R.md, fontSize:'13px', outline:'none', boxSizing:'border-box', fontFamily:FONT, color:T.g900 };
const lbl = { display:'block', fontSize:'13px', fontWeight:600, color:T.g700, marginBottom:'4px', fontFamily:FONT };
const btnP = { padding:'10px 20px', background:T.sapphire, color:T.white, border:'none', borderRadius:R.md, fontSize:'13px', fontWeight:600, cursor:'pointer', fontFamily:FONT, display:'flex', alignItems:'center', gap:'8px' };
const btnG = { padding:'10px 20px', background:'transparent', color:T.sapphire, border:`1.5px solid ${T.sapphire}`, borderRadius:R.md, fontSize:'13px', fontWeight:600, cursor:'pointer', fontFamily:FONT };
const actBtn = { padding:'5px 10px', border:`1px solid ${T.g200}`, borderRadius:R.sm, fontSize:'12px', cursor:'pointer', background:T.white, fontFamily:FONT };
const thStyle = { padding:'12px 16px', textAlign:'left', fontSize:'11px', fontWeight:600, color:T.white, textTransform:'uppercase', letterSpacing:'0.06em', fontFamily:FONT };
const tdStyle = { padding:'12px 16px', borderBottom:`1px solid ${T.g200}`, fontSize:'13px', fontFamily:FONT, color:T.g900 };

function CatBadge({ category }) {
  const cat = CATEGORIES.find(c => c.v === category) || { en: category, color: T.g500 };
  return <span style={{ padding:'3px 10px', borderRadius:'99px', fontSize:'11px', fontWeight:600, fontFamily:FONT, background:`${cat.color}14`, color:cat.color, border:`1px solid ${cat.color}30` }}>{cat.en}</span>;
}

function StatusBadge({ status }) {
  const map = { pending: { bg:T.warningMuted, c:'#92400E', l:'Pending' }, verified: { bg:T.sapphireMuted, c:T.sapphire, l:'Verified' }, dispensed: { bg:T.emeraldMuted, c:T.emeraldDark, l:'Dispensed' }, cancelled: { bg:T.rubyMuted, c:T.rubyDark, l:'Cancelled' } };
  const s = map[status] || map.pending;
  return <span style={{ padding:'3px 10px', borderRadius:'99px', fontSize:'11px', fontWeight:600, fontFamily:FONT, background:s.bg, color:s.c }}>{s.l}</span>;
}

function StockIndicator({ stock, reorder }) {
  const pct = Math.min(stock / (reorder * 3) * 100, 100);
  const color = stock <= 0 ? T.ruby : stock <= reorder ? T.warning : T.emerald;
  const label = stock <= 0 ? 'OUT' : stock <= reorder ? 'LOW' : '';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
      <div style={{ width:'60px', height:'6px', borderRadius:'3px', background:T.g200 }}>
        <div style={{ width:`${pct}%`, height:'100%', borderRadius:'3px', background:color, transition:'width 0.3s' }} />
      </div>
      <span style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT, color }}>{stock}</span>
      {label && <span style={{ fontSize:'9px', fontWeight:700, fontFamily:FONT, color, background:`${color}14`, padding:'1px 5px', borderRadius:'3px' }}>{label}</span>}
    </div>
  );
}

export default function PharmacyDashboard() {
  const [tab, setTab] = useState('drugs');
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const [rxList, setRxList] = useState(DEMO_RX);
  const [labelPreview, setLabelPreview] = useState(null);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const filteredDrugs = DEMO_DRUGS.filter(d => {
    if (search && !`${d.name_generic} ${d.name_brand} ${d.name_thai}`.toLowerCase().includes(search.toLowerCase())) return false;
    if (catFilter && d.category !== catFilter) return false;
    return true;
  });

  const stats = {
    total: DEMO_DRUGS.length,
    lowStock: DEMO_DRUGS.filter(d => d.stock <= d.reorder).length,
    expiring: DEMO_DRUGS.filter(d => { const exp = new Date(d.expiry); const diff = (exp - new Date()) / 86400000; return diff <= 90; }).length,
    pending: rxList.filter(r => r.status === 'pending').length,
    stockValue: DEMO_DRUGS.reduce((s, d) => s + d.stock * d.price, 0),
  };

  const tabBtn = (id) => ({ padding:'8px 18px', border:'none', borderBottom: tab===id ? `2px solid ${T.sapphire}` : '2px solid transparent', background:'none', color: tab===id ? T.sapphire : T.g500, fontWeight:600, fontSize:'13px', cursor:'pointer', fontFamily:FONT });

  // ── Add Drug Modal ───────────────────────────────────
  function AddDrugModal() {
    const [f, setF] = useState({ name_generic:'', name_brand:'', name_thai:'', category:'hormonal', form:'tablet', strength:'', unit:'tablet', purchase_price:'', selling_price:'', reorder_level:'50', storage:'room_temperature' });
    const up = (k,v) => setF({...f,[k]:v});
    return (
      <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000, backdropFilter:'blur(4px)' }} onClick={()=>setModal(null)}>
        <div style={{ background:T.white, borderRadius:R.lg, padding:'28px', width:'560px', maxHeight:'85vh', overflow:'auto', boxShadow:'0 24px 48px rgba(0,0,0,0.15)' }} onClick={e=>e.stopPropagation()}>
          <h3 style={{ fontSize:'18px', fontWeight:700, color:T.g900, fontFamily:FONT, marginBottom:'20px' }}>Add New Drug</h3>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
            <div><label style={lbl}>Generic Name *</label><input style={inp} value={f.name_generic} onChange={e=>up('name_generic',e.target.value)} placeholder="e.g. Letrozole" /></div>
            <div><label style={lbl}>Brand Name</label><input style={inp} value={f.name_brand} onChange={e=>up('name_brand',e.target.value)} placeholder="e.g. Femara" /></div>
          </div>
          <div style={{ marginTop:'12px' }}><label style={lbl}>ชื่อไทย</label><input style={inp} value={f.name_thai} onChange={e=>up('name_thai',e.target.value)} /></div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'12px', marginTop:'12px' }}>
            <div><label style={lbl}>Category *</label><select style={inp} value={f.category} onChange={e=>up('category',e.target.value)}>{CATEGORIES.map(c=><option key={c.v} value={c.v}>{c.en} / {c.th}</option>)}</select></div>
            <div><label style={lbl}>Form *</label><select style={inp} value={f.form} onChange={e=>up('form',e.target.value)}>{['tablet','capsule','injection','cream','suppository','solution','other'].map(v=><option key={v} value={v}>{v}</option>)}</select></div>
            <div><label style={lbl}>Strength *</label><input style={inp} value={f.strength} onChange={e=>up('strength',e.target.value)} placeholder="2.5mg" /></div>
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'12px', marginTop:'12px' }}>
            <div><label style={lbl}>Purchase ฿</label><input style={inp} type="number" value={f.purchase_price} onChange={e=>up('purchase_price',e.target.value)} /></div>
            <div><label style={lbl}>Selling ฿</label><input style={inp} type="number" value={f.selling_price} onChange={e=>up('selling_price',e.target.value)} /></div>
            <div><label style={lbl}>Reorder Level</label><input style={inp} type="number" value={f.reorder_level} onChange={e=>up('reorder_level',e.target.value)} /></div>
          </div>
          <div style={{ marginTop:'12px' }}><label style={lbl}>Storage</label><select style={inp} value={f.storage} onChange={e=>up('storage',e.target.value)}><option value="room_temperature">Room Temperature</option><option value="refrigerated">Refrigerated (2-8°C)</option><option value="frozen">Frozen (-20°C)</option></select></div>
          <div style={{ display:'flex', gap:'10px', justifyContent:'flex-end', marginTop:'20px' }}>
            <button onClick={()=>setModal(null)} style={btnG}>Cancel</button>
            <button onClick={()=>{showToast(`Drug ${f.name_generic} added`);setModal(null);}} style={btnP}>Add Drug</button>
          </div>
        </div>
      </div>
    );
  }

  // ── Receive Stock Modal ──────────────────────────────
  function ReceiveStockModal() {
    const [f, setF] = useState({ drug_id:'D1', quantity:'', lot_number:'', expiry_date:'', invoice:'', location:'' });
    const up = (k,v) => setF({...f,[k]:v});
    return (
      <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }} onClick={()=>setModal(null)}>
        <div style={{ background:T.white, borderRadius:R.lg, padding:'28px', width:'480px', boxShadow:'0 24px 48px rgba(0,0,0,0.15)' }} onClick={e=>e.stopPropagation()}>
          <h3 style={{ fontSize:'18px', fontWeight:700, color:T.g900, fontFamily:FONT, marginBottom:'20px' }}>Receive Stock</h3>
          <div><label style={lbl}>Drug</label><select style={inp} value={f.drug_id} onChange={e=>up('drug_id',e.target.value)}>{DEMO_DRUGS.map(d=><option key={d.id} value={d.id}>{d.name_generic} ({d.name_brand}) — {d.strength}</option>)}</select></div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginTop:'12px' }}>
            <div><label style={lbl}>Quantity *</label><input style={inp} type="number" value={f.quantity} onChange={e=>up('quantity',e.target.value)} /></div>
            <div><label style={lbl}>Lot Number *</label><input style={inp} value={f.lot_number} onChange={e=>up('lot_number',e.target.value)} placeholder="LOT-2026-XXX" /></div>
          </div>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginTop:'12px' }}>
            <div><label style={lbl}>Expiry Date *</label><input style={inp} type="date" value={f.expiry_date} onChange={e=>up('expiry_date',e.target.value)} /></div>
            <div><label style={lbl}>Invoice No.</label><input style={inp} value={f.invoice} onChange={e=>up('invoice',e.target.value)} /></div>
          </div>
          <div style={{ marginTop:'12px' }}><label style={lbl}>Storage Location</label><input style={inp} value={f.location} onChange={e=>up('location',e.target.value)} placeholder="e.g. Shelf A3, Fridge 2" /></div>
          <div style={{ display:'flex', gap:'10px', justifyContent:'flex-end', marginTop:'20px' }}>
            <button onClick={()=>setModal(null)} style={btnG}>Cancel</button>
            <button onClick={()=>{showToast('Stock received');setModal(null);}} style={{...btnP, background:T.emerald}}>Receive Stock</button>
          </div>
        </div>
      </div>
    );
  }

  // ── Label Preview Modal ──────────────────────────────
  function LabelModal() {
    return (
      <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }} onClick={()=>setLabelPreview(null)}>
        <div style={{ background:T.white, borderRadius:R.lg, padding:'0', width:'420px', boxShadow:'0 24px 48px rgba(0,0,0,0.15)', overflow:'hidden' }} onClick={e=>e.stopPropagation()}>
          {/* Label preview */}
          <div style={{ padding:'24px', border:`2px solid ${T.g900}`, margin:'20px', borderRadius:R.sm }}>
            <div style={{ textAlign:'center', borderBottom:`1px solid ${T.g200}`, paddingBottom:'8px', marginBottom:'10px' }}>
              <div style={{ fontSize:'14px', fontWeight:700, color:T.g900, fontFamily:FONT }}>Life by Dr. Pat</div>
              <div style={{ fontSize:'11px', color:T.g500, fontFamily:FONT }}>คลินิกไลฟ์ บาย ดร.แพท · Tel: 02-xxx-xxxx</div>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'4px', marginBottom:'10px' }}>
              <div><span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Patient / ผู้ป่วย:</span><div style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT }}>Patsama V.</div><div style={{ fontSize:'11px', fontFamily:FONT }}>พัชมา ว.</div></div>
              <div style={{ textAlign:'right' }}><span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>HN:</span><div style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT }}>HN-00001</div><div style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Date: 2026-03-05</div></div>
            </div>
            <div style={{ background:T.sapphireMuted, borderRadius:R.sm, padding:'10px', marginBottom:'10px' }}>
              <div style={{ fontSize:'15px', fontWeight:700, color:T.sapphire, fontFamily:FONT }}>Letrozole 2.5mg</div>
              <div style={{ fontSize:'12px', color:T.sapphireDeep, fontFamily:FONT }}>เลโตรโซล 2.5 มก.</div>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'8px', marginBottom:'10px' }}>
              <div><span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Dose / ขนาด:</span><div style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT }}>2.5mg</div></div>
              <div><span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Qty / จำนวน:</span><div style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT }}>10 tablets</div></div>
            </div>
            <div style={{ marginBottom:'10px' }}>
              <span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Frequency / ความถี่:</span>
              <div style={{ fontSize:'13px', fontWeight:600, fontFamily:FONT }}>Once daily for 5 days</div>
              <div style={{ fontSize:'12px', color:T.g700, fontFamily:FONT }}>วันละ 1 ครั้ง เป็นเวลา 5 วัน</div>
            </div>
            <div style={{ marginBottom:'10px' }}>
              <span style={{ fontSize:'10px', color:T.g400, fontFamily:FONT }}>Instructions / คำแนะนำ:</span>
              <div style={{ fontSize:'12px', fontFamily:FONT }}>Take after meals / รับประทานหลังอาหาร</div>
            </div>
            <div style={{ borderTop:`1px solid ${T.g200}`, paddingTop:'6px', fontSize:'10px', color:T.g400, fontFamily:FONT, display:'flex', justifyContent:'space-between' }}>
              <span>Prescriber: Dr. Pat</span>
              <span>Pharmacist: Kanya P.</span>
            </div>
          </div>
          <div style={{ padding:'16px 20px', background:T.g50, borderTop:`1px solid ${T.g200}`, display:'flex', justifyContent:'flex-end', gap:'10px' }}>
            <button onClick={()=>setLabelPreview(null)} style={btnG}>Close</button>
            <button onClick={()=>{showToast('Label sent to printer');setLabelPreview(null);}} style={btnP}>Print Label</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ fontFamily:FONT, background:T.g50, minHeight:'100vh' }}>
      {toast && <div style={{ position:'fixed', top:20, right:20, zIndex:9999, padding:'12px 20px', borderRadius:R.md, fontSize:'13px', fontWeight:600, fontFamily:FONT, boxShadow:'0 8px 24px rgba(0,0,0,0.12)', background:T.emeraldMuted, color:T.emeraldDark, borderLeft:`4px solid ${T.emerald}` }}>✓ {toast}</div>}

      {/* Header */}
      <div style={{ background:T.white, borderBottom:`1px solid ${T.g200}`, padding:'16px 32px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'12px' }}>
          <div>
            <h1 style={{ fontSize:'22px', fontWeight:700, color:T.g900, fontFamily:FONT }}>Pharmacy / เภสัชกรรม</h1>
            <p style={{ fontSize:'12px', color:T.g500, fontFamily:FONT }}>Drug stock management, prescriptions, and dispensing</p>
          </div>
          <div style={{ display:'flex', gap:'10px' }}>
            <button onClick={()=>setModal('receive')} style={{...btnP, background:T.emerald}}>+ Receive Stock</button>
            <button onClick={()=>setModal('addDrug')} style={btnP}>+ Add Drug</button>
          </div>
        </div>
        <div style={{ display:'flex', gap:'4px' }}>
          {[{id:'drugs',l:'Drug Catalogue'},{id:'prescriptions',l:'Prescriptions'},{id:'alerts',l:'Alerts'}].map(t => (
            <button key={t.id} style={tabBtn(t.id)} onClick={()=>setTab(t.id)}>{t.l}</button>
          ))}
        </div>
      </div>

      <div style={{ padding:'24px 32px' }}>
        {/* Stats */}
        <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'12px', marginBottom:'24px' }}>
          {[
            {n:stats.total, l:'Total Drugs', c:T.sapphire},
            {n:`฿${(stats.stockValue/1000).toFixed(0)}k`, l:'Stock Value', c:T.emeraldDark},
            {n:stats.lowStock, l:'Low Stock', c:T.warning},
            {n:stats.expiring, l:'Expiring ≤90d', c:T.ruby},
            {n:stats.pending, l:'Pending Rx', c:T.sapphireDeep},
          ].map((s,i) => (
            <div key={i} style={{ background:T.white, borderRadius:R.lg, padding:'16px 20px', border:`1px solid ${T.g200}`, boxShadow:'0 1px 3px rgba(0,0,0,0.08)' }}>
              <div style={{ fontSize:'28px', fontWeight:700, color:s.c, lineHeight:1, fontFamily:FONT }}>{s.n}</div>
              <div style={{ fontSize:'12px', color:T.g500, marginTop:'4px', fontWeight:500, fontFamily:FONT }}>{s.l}</div>
            </div>
          ))}
        </div>

        {/* ── DRUG CATALOGUE TAB ── */}
        {tab === 'drugs' && <>
          <div style={{ display:'flex', gap:'10px', marginBottom:'16px' }}>
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search drug name (EN/TH/Brand)..." style={{...inp, flex:1, maxWidth:'400px'}} />
            <select value={catFilter} onChange={e=>setCatFilter(e.target.value)} style={{...inp, width:'auto'}}>
              <option value="">All Categories</option>
              {CATEGORIES.map(c => <option key={c.v} value={c.v}>{c.en} / {c.th}</option>)}
            </select>
          </div>

          <div style={{ borderRadius:R.lg, overflow:'hidden', border:`1px solid ${T.g200}` }}>
            <table style={{ width:'100%', borderCollapse:'collapse', background:T.white }}>
              <thead><tr style={{ background:T.sapphireDeep }}>
                {['Drug Name','Category','Form','Strength','Stock','Lot','Expiry','Storage','Price ฿',''].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {filteredDrugs.map(d => {
                  const daysToExpiry = Math.round((new Date(d.expiry) - new Date()) / 86400000);
                  const isExpiring = daysToExpiry <= 90;
                  return (
                    <tr key={d.id} style={{ transition:'background 0.1s' }}
                      onMouseEnter={e=>e.currentTarget.style.background=T.sapphireMuted}
                      onMouseLeave={e=>e.currentTarget.style.background=T.white}>
                      <td style={tdStyle}>
                        <div style={{ fontWeight:600 }}>{d.name_generic}</div>
                        <div style={{ fontSize:'11px', color:T.g400 }}>{d.name_brand} · {d.name_thai}</div>
                      </td>
                      <td style={tdStyle}><CatBadge category={d.category} /></td>
                      <td style={{...tdStyle, fontSize:'12px', color:T.g500}}>{d.form}</td>
                      <td style={{...tdStyle, fontWeight:600}}>{d.strength}</td>
                      <td style={tdStyle}><StockIndicator stock={d.stock} reorder={d.reorder} /></td>
                      <td style={{...tdStyle, fontSize:'11px', color:T.g500}}>{d.lot}</td>
                      <td style={tdStyle}>
                        <span style={{ fontSize:'12px', fontWeight:600, color: isExpiring ? T.ruby : T.g500 }}>{d.expiry}</span>
                        {isExpiring && <div style={{ fontSize:'9px', fontWeight:700, color:T.ruby }}>{daysToExpiry}d left</div>}
                      </td>
                      <td style={{...tdStyle, fontSize:'11px'}}>
                        {d.storage === 'refrigerated' ? <span style={{ color:T.sapphire }}>❄️ 2-8°C</span> : <span style={{ color:T.g400 }}>🌡️ RT</span>}
                      </td>
                      <td style={{...tdStyle, fontWeight:600}}>฿{d.price}</td>
                      <td style={{...tdStyle, whiteSpace:'nowrap'}}>
                        <button style={actBtn} title="Edit">✏️</button>{' '}
                        <button style={actBtn} title="View stock history">📊</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div style={{ padding:'10px 16px', background:T.g50, borderTop:`1px solid ${T.g200}`, fontSize:'12px', color:T.g400, fontFamily:FONT }}>{filteredDrugs.length} drugs · Demo data</div>
          </div>
        </>}

        {/* ── PRESCRIPTIONS TAB ── */}
        {tab === 'prescriptions' && (
          <div style={{ borderRadius:R.lg, overflow:'hidden', border:`1px solid ${T.g200}` }}>
            <table style={{ width:'100%', borderCollapse:'collapse', background:T.white }}>
              <thead><tr style={{ background:T.sapphireDeep }}>
                {['Rx ID','Date','Patient','HN','Prescriber','Items','Status','Actions'].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {rxList.map(rx => (
                  <tr key={rx.id} style={{ transition:'background 0.1s' }}
                    onMouseEnter={e=>e.currentTarget.style.background=T.sapphireMuted}
                    onMouseLeave={e=>e.currentTarget.style.background=T.white}>
                    <td style={{...tdStyle, fontWeight:600, color:T.sapphire}}>{rx.id}</td>
                    <td style={{...tdStyle, fontSize:'12px'}}>{rx.date}</td>
                    <td style={{...tdStyle, fontWeight:600}}>{rx.patient}</td>
                    <td style={tdStyle}><span style={{ padding:'2px 8px', background:T.sapphireMuted, color:T.sapphire, borderRadius:'4px', fontSize:'11px', fontWeight:600 }}>{rx.hn}</span></td>
                    <td style={{...tdStyle, fontSize:'12px', color:T.g500}}>{rx.prescriber}</td>
                    <td style={tdStyle}>
                      {rx.items.map((item,i) => <div key={i} style={{ fontSize:'12px', color:T.g700 }}>• {item.drug} × {item.qty}</div>)}
                    </td>
                    <td style={tdStyle}><StatusBadge status={rx.status} /></td>
                    <td style={{...tdStyle, whiteSpace:'nowrap'}}>
                      {rx.status === 'pending' && <button style={{...actBtn, color:T.sapphire, borderColor:T.sapphire}} onClick={()=>{setRxList(rxList.map(r=>r.id===rx.id?{...r,status:'verified'}:r));showToast(`${rx.id} verified`);}}>✓ Verify</button>}
                      {rx.status === 'verified' && <>
                        <button style={{...actBtn, color:T.emerald, borderColor:T.emerald}} onClick={()=>{setRxList(rxList.map(r=>r.id===rx.id?{...r,status:'dispensed'}:r));showToast(`${rx.id} dispensed`);}}>💊 Dispense</button>{' '}
                        <button style={actBtn} onClick={()=>setLabelPreview(rx)}>🏷️ Label</button>
                      </>}
                      {rx.status === 'dispensed' && <button style={actBtn} onClick={()=>setLabelPreview(rx)}>🏷️ Label</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── ALERTS TAB ── */}
        {tab === 'alerts' && (
          <div style={{ display:'grid', gap:'16px' }}>
            {/* Expiring Soon */}
            <div style={{ background:T.white, borderRadius:R.lg, border:`1px solid ${T.g200}`, overflow:'hidden' }}>
              <div style={{ padding:'14px 20px', background:T.rubyMuted, borderBottom:`1px solid ${T.ruby}20`, display:'flex', alignItems:'center', gap:'8px' }}>
                <span style={{ fontSize:'16px' }}>⚠️</span>
                <span style={{ fontSize:'14px', fontWeight:700, color:T.rubyDark, fontFamily:FONT }}>Expiring Within 90 Days</span>
              </div>
              {DEMO_DRUGS.filter(d => { const diff = (new Date(d.expiry) - new Date()) / 86400000; return diff <= 90; }).map(d => {
                const days = Math.round((new Date(d.expiry) - new Date()) / 86400000);
                return (
                  <div key={d.id} style={{ padding:'12px 20px', borderBottom:`1px solid ${T.g100}`, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                    <div>
                      <span style={{ fontWeight:600, fontSize:'13px', fontFamily:FONT }}>{d.name_generic}</span>
                      <span style={{ fontSize:'12px', color:T.g400, marginLeft:'8px' }}>{d.name_brand} · Lot: {d.lot}</span>
                    </div>
                    <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                      <span style={{ fontSize:'12px', color:T.g500, fontFamily:FONT }}>Stock: {d.stock}</span>
                      <span style={{ padding:'3px 10px', borderRadius:'99px', fontSize:'11px', fontWeight:700, fontFamily:FONT, background: days<=30 ? T.rubyMuted : T.warningMuted, color: days<=30 ? T.rubyDark : '#92400E' }}>
                        {d.expiry} ({days}d)
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Low Stock */}
            <div style={{ background:T.white, borderRadius:R.lg, border:`1px solid ${T.g200}`, overflow:'hidden' }}>
              <div style={{ padding:'14px 20px', background:T.warningMuted, borderBottom:`1px solid ${T.warning}20`, display:'flex', alignItems:'center', gap:'8px' }}>
                <span style={{ fontSize:'16px' }}>📦</span>
                <span style={{ fontSize:'14px', fontWeight:700, color:'#92400E', fontFamily:FONT }}>Low Stock Items</span>
              </div>
              {DEMO_DRUGS.filter(d => d.stock <= d.reorder).map(d => (
                <div key={d.id} style={{ padding:'12px 20px', borderBottom:`1px solid ${T.g100}`, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <span style={{ fontWeight:600, fontSize:'13px', fontFamily:FONT }}>{d.name_generic}</span>
                    <span style={{ fontSize:'12px', color:T.g400, marginLeft:'8px' }}>{d.strength}</span>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:'12px' }}>
                    <StockIndicator stock={d.stock} reorder={d.reorder} />
                    <span style={{ fontSize:'11px', color:T.g400, fontFamily:FONT }}>Reorder: {d.reorder}</span>
                    <button style={{...actBtn, color:T.emerald, borderColor:T.emerald}} onClick={()=>{setModal('receive');showToast('Opening receive form');}}>+ Reorder</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {modal === 'addDrug' && <AddDrugModal />}
      {modal === 'receive' && <ReceiveStockModal />}
      {labelPreview && <LabelModal />}
    </div>
  );
}
