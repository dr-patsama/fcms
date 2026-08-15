/**
 * FCMS Module 4 — Prescription Writer / เครื่องมือสร้างใบสั่งยา
 * Structured sig entry → quantity computed and rounded UP to full packs
 * (drugs.pack_size) silently; only the final quantity prints.
 * Optional prefill from an uploaded photo/PDF (JPEG/PNG/HEIC/PDF) via
 * POST /prescriptions/extract — the upload card hides itself if the
 * server has no ANTHROPIC_API_KEY configured.
 * Printable A4 letterhead sheet (logo, ruby rule, Rx table, signature space).
 * Design: Cloud font, Sapphire Deep primary, bilingual EN/TH throughout.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';

const API = '/api/v1/pharmacy';
const PATIENT_API = '/api/v1/patients';

// ── Design Tokens ────────────────────────────────────────
const C = {
  sapphire:     '#0F52BA',
  sapphireDeep: '#151667',
  sapphireMuted:'#E8EEFA',
  emerald:      '#009473',
  emeraldMuted: '#E0F5EF',
  ruby:         '#E0115F',
  rubyDark:     '#A00040',
  rubyMuted:    '#FCE4EE',
  gold:         '#C5A044',
  gray900:      '#111827',
  gray500:      '#6B7280',
  gray200:      '#E5E7EB',
  gray50:       '#F9FAFB',
  white:        '#FFFFFF',
};

// ── Bilingual labels ─────────────────────────────────────
const T = {
  title:          { en: 'Prescription Writer',        th: 'สร้างใบสั่งยา' },
  fillFromDoc:    { en: 'Fill from a document',       th: 'ดึงข้อมูลจากเอกสาร' },
  fillHint:       { en: 'Upload a photo or PDF (JPEG, PNG, HEIC, PDF) of a certificate, previous prescription, or note — details prefill automatically and stay editable.',
                    th: 'อัปโหลดรูปถ่ายหรือ PDF (รองรับ HEIC จาก iPhone) ระบบจะดึงข้อมูลมาเติมให้อัตโนมัติ แก้ไขได้ทุกช่อง' },
  extracting:     { en: 'Reading the document…',      th: 'กำลังอ่านเอกสาร…' },
  patient:        { en: 'Patient',                    th: 'ผู้ป่วย' },
  searchPatient:  { en: 'Search by HN or name',       th: 'ค้นหาด้วย HN หรือชื่อ' },
  diagnosis:      { en: 'Diagnosis',                  th: 'การวินิจฉัย' },
  diagnosisTh:    { en: 'Diagnosis (Thai)',           th: 'การวินิจฉัย (ไทย)' },
  medications:    { en: 'Medications',                th: 'รายการยา' },
  addDrug:        { en: 'Add medication',             th: 'เพิ่มยา' },
  searchDrug:     { en: 'Search the drug catalogue',  th: 'ค้นหายาในคลัง' },
  perDose:        { en: 'Per dose',                   th: 'ครั้งละ' },
  timesPerDay:    { en: 'Times/day',                  th: 'ครั้ง/วัน' },
  days:           { en: 'Days',                       th: 'จำนวนวัน' },
  route:          { en: 'Route',                      th: 'วิธีใช้' },
  instruction:    { en: 'Instruction',                th: 'คำแนะนำ' },
  sig:            { en: 'Sig (auto — type to override)', th: 'วิธีใช้ยา (อัตโนมัติ — พิมพ์เพื่อแก้)' },
  quantity:       { en: 'Quantity',                   th: 'จำนวนจ่าย' },
  note:           { en: 'Note on prescription',       th: 'หมายเหตุบนใบสั่งยา' },
  save:           { en: 'Save prescription',          th: 'บันทึกใบสั่งยา' },
  saveAndPrint:   { en: 'Save & print',               th: 'บันทึกและพิมพ์' },
  print:          { en: 'Print',                      th: 'พิมพ์' },
  newRx:          { en: 'New prescription',           th: 'ใบสั่งยาใหม่' },
  remove:         { en: 'Remove',                     th: 'ลบ' },
  age:            { en: 'Age',                        th: 'อายุ' },
  hn:             { en: 'HN',                         th: 'HN' },
  passportId:     { en: 'Passport / ID no.',          th: 'เลขบัตร / พาสปอร์ต' },
  patientName:    { en: 'Patient name',               th: 'ชื่อผู้ป่วย' },
  signature:      { en: "Prescriber's Signature",     th: 'ลายมือชื่อผู้สั่งยา' },
  prescriber:     { en: 'Prescriber',                 th: 'ผู้สั่งยา' },
  license:        { en: 'Medical License No.',        th: 'ใบอนุญาตประกอบวิชาชีพเวชกรรมเลขที่' },
  validity:       { en: 'This prescription is valid only when signed by the prescriber.',
                    th: 'ใบสั่งยานี้มีผลเมื่อลงนามโดยผู้สั่งยาเท่านั้น' },
};
const ROUTES = ['oral', 'vaginal', 'sublingual', 'subcutaneous', 'intramuscular', 'topical'];
const ROUTE_TH = { oral: 'รับประทาน', vaginal: 'เหน็บช่องคลอด', sublingual: 'อมใต้ลิ้น', subcutaneous: 'ฉีดใต้ผิวหนัง', intramuscular: 'ฉีดเข้ากล้ามเนื้อ', topical: 'ทาภายนอก' };
const ROUTE_EN = { oral: ['Take', 'orally'], vaginal: ['Insert', 'vaginally'], sublingual: ['Place', 'under the tongue'], subcutaneous: ['Inject', 'subcutaneously'], intramuscular: ['Inject', 'intramuscularly'], topical: ['Apply', 'topically'] };

const bi = (k) => `${T[k].en} / ${T[k].th}`;

// ── Sig / quantity helpers (mirror the backend logic) ────
const freqWord = (n) => ({ 1: 'once daily', 2: 'twice daily', 3: 'three times daily', 4: 'four times daily' }[n] || `${n} times daily`);
const fmtDose = (x) => (Number.isInteger(Number(x)) ? String(Number(x)) : String(x));

function sigEn(it) {
  const [verb, adverb] = ROUTE_EN[it.route] || ROUTE_EN.oral;
  let u = it.unit || 'unit';
  const d = Number(it.dose_per_time) || 0;
  if (d !== 1 && !u.endsWith('s')) u += 's';
  if (d === 1 && u.endsWith('s')) u = u.slice(0, -1);
  const base = `${verb} ${fmtDose(d)} ${u} ${adverb} ${freqWord(Number(it.times_per_day) || 0)}`;
  return it.instruction_en ? `${base} ${it.instruction_en}` : base;
}
function sigTh(it) {
  const verb = ROUTE_TH[it.route] || ROUTE_TH.oral;
  const base = `${verb}ครั้งละ ${fmtDose(Number(it.dose_per_time) || 0)} ${it.unit_th || 'หน่วย'} วันละ ${Number(it.times_per_day) || 0} ครั้ง`;
  return it.instruction_th ? `${base} ${it.instruction_th}` : base;
}
const needed = (it) => Math.ceil((Number(it.dose_per_time) || 0) * (Number(it.times_per_day) || 0) * (Number(it.duration_days) || 0));
function computedQty(it) {
  const n = needed(it);
  const p = Number(it.pack_size) || 0;
  return p > 0 && n > 0 ? Math.ceil(n / p) * p : n;
}
const finalQty = (it) => (it.quantity_override ? Number(it.quantity_override) : computedQty(it));

let _uid = 1;
const nextId = () => `it${Date.now()}_${_uid++}`;

// ── Shared inputs ────────────────────────────────────────
const inputStyle = {
  fontFamily: 'inherit', fontSize: 14, padding: '8px 10px', width: '100%',
  border: `1px solid ${C.gray200}`, borderRadius: 6, background: C.white, color: C.gray900,
};
function Fld({ label, w, children }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 3, flex: w ? `0 0 ${w}` : '1 1 140px', minWidth: 0, marginBottom: 8 }}>
      <span style={{ fontSize: 10.5, letterSpacing: '0.04em', color: C.gray500, textTransform: 'uppercase' }}>{label}</span>
      {children}
    </label>
  );
}
function Btn({ kind = 'primary', style, ...props }) {
  const base = {
    fontFamily: 'inherit', fontSize: 14, fontWeight: 600, padding: '10px 16px',
    borderRadius: 6, cursor: 'pointer', border: '1px solid transparent',
  };
  const kinds = {
    primary: { background: C.sapphireDeep, color: C.white },
    ruby:    { background: C.ruby, color: C.white },
    ghost:   { background: C.white, color: C.gray900, borderColor: C.gray200 },
  };
  return <button style={{ ...base, ...kinds[kind], ...style }} {...props} />;
}

// ── Printable A4 sheet / ใบสั่งยา A4 ─────────────────────
function PrintSheet({ doc }) {
  if (!doc) return null;
  const p = doc.patient || {};
  const label = (en, th) => (
    <div style={{ fontSize: '9pt', color: '#999', letterSpacing: '0.02em' }}>{en}</div>
  );
  return (
    <div className="rx-sheet" style={{
      width: '210mm', minHeight: '296mm', background: '#fff', padding: '20mm',
      position: 'relative', color: C.gray900, fontFamily: "'Cloud', sans-serif",
      boxShadow: '0 2px 14px rgba(0,0,0,0.12)',
    }}>
      <div style={{ textAlign: 'center' }}>
        <img src="/logo.png" alt="" style={{ width: '22mm', height: '22mm', objectFit: 'contain' }} />
        <div style={{ fontWeight: 700, fontSize: '15pt', marginTop: '2mm' }}>{doc.clinic.name}</div>
        <div style={{ fontSize: '9pt', color: '#555', marginTop: '1.2mm' }}>{doc.clinic.address}</div>
        <div style={{ fontSize: '9pt', color: '#555', marginTop: '1.2mm' }}>
          Hospital license number: {doc.clinic.hospital_license} &nbsp;|&nbsp; Tel. {doc.clinic.tel}
        </div>
      </div>
      <div style={{ borderTop: `1.5pt solid ${C.ruby}`, marginTop: '5mm' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '7mm' }}>
        <div style={{ fontWeight: 600, fontSize: '17pt' }}>Prescription / ใบสั่งยา</div>
        <div style={{ fontSize: '10.5pt', color: '#555' }}>
          {doc.rx_number} &nbsp;·&nbsp; {doc.date_en}
        </div>
      </div>
      <div style={{ display: 'flex', marginTop: '6mm' }}>
        <div style={{ width: '12%' }}>{label('HN')}<div style={{ fontWeight: 600, fontSize: '10.5pt', marginTop: '1.6mm' }}>{p.hn || '—'}</div></div>
        <div style={{ width: '36%' }}>{label('PATIENT NAME')}<div style={{ fontWeight: 600, fontSize: '10.5pt', marginTop: '1.6mm' }}>{p.name_en || '—'}{p.name_th ? <span style={{ fontWeight: 400, color: '#555' }}> / {p.name_th}</span> : null}</div></div>
        <div style={{ width: '30%' }}>{label('AGE')}<div style={{ fontWeight: 600, fontSize: '10.5pt', marginTop: '1.6mm' }}>{p.age_en || '—'}</div></div>
        <div style={{ width: '22%' }}>{label('PASSPORT / ID NO.')}<div style={{ fontWeight: 600, fontSize: '10.5pt', marginTop: '1.6mm' }}>{p.id_number || '—'}</div></div>
      </div>
      {(doc.diagnosis_en || doc.diagnosis_th) && (
        <div style={{ marginTop: '6mm' }}>
          {label('DIAGNOSIS')}
          <div style={{ fontSize: '10.5pt', marginTop: '1.6mm' }}>{doc.diagnosis_en}</div>
          {doc.diagnosis_th && <div style={{ fontSize: '10.5pt', color: '#555', marginTop: '1mm' }}>{doc.diagnosis_th}</div>}
        </div>
      )}
      <div style={{ borderTop: '0.6pt solid #ddd', marginTop: '7mm' }} />
      <div style={{ fontWeight: 700, fontSize: '26pt', color: C.ruby, margin: '5mm 0 3mm', lineHeight: 1 }}>Rx</div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ fontWeight: 600, fontSize: '8.5pt', color: '#555', background: '#f7f7f7', padding: '2.4mm 3mm', textAlign: 'left', borderTop: '0.6pt solid #ddd', letterSpacing: '0.03em' }}>
              MEDICATION &amp; DIRECTIONS / รายการยาและวิธีใช้
            </th>
            <th style={{ fontWeight: 600, fontSize: '8.5pt', color: '#555', background: '#f7f7f7', padding: '2.4mm 3mm', width: '52mm', textAlign: 'center', borderTop: '0.6pt solid #ddd', borderLeft: '0.6pt solid #ddd', letterSpacing: '0.03em' }}>
              QUANTITY / จำนวน
            </th>
          </tr>
        </thead>
        <tbody>
          {doc.items.map((it) => (
            <tr key={it.no}>
              <td style={{ borderBottom: '0.6pt solid #ddd', padding: '4mm 3mm', verticalAlign: 'middle' }}>
                <div style={{ fontWeight: 600, fontSize: '12pt' }}>{it.no}.&nbsp;&nbsp;{it.name_en}</div>
                {it.generic && <div style={{ fontSize: '9.5pt', color: '#555', margin: '1.4mm 0 0 6mm' }}>({it.generic})</div>}
                <div style={{ fontSize: '10.5pt', margin: '1.8mm 0 0 6mm' }}>Sig:&nbsp; {it.sig_en}</div>
                {it.sig_th && <div style={{ fontSize: '10.5pt', color: '#555', margin: '1.2mm 0 0 6mm' }}>{it.sig_th}</div>}
              </td>
              <td style={{ borderBottom: '0.6pt solid #ddd', borderLeft: '0.6pt solid #ddd', padding: '4mm 3mm', textAlign: 'center', verticalAlign: 'middle' }}>
                <div style={{ fontWeight: 700, fontSize: '13pt' }}>{it.quantity} {it.unit_en}</div>
                {it.unit_th && <div style={{ fontSize: '9pt', color: '#555', marginTop: '1mm' }}>{it.quantity} {it.unit_th}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(doc.notes || doc.notes_th) && (
        <div style={{ fontSize: '9.5pt', color: '#555', marginTop: '6mm' }}>
          {doc.notes}{doc.notes && doc.notes_th ? ' / ' : ''}{doc.notes_th}
        </div>
      )}
      <div style={{ position: 'absolute', left: '20mm', right: '20mm', bottom: '30mm' }}>
        <div style={{ borderTop: '0.6pt solid #ddd', marginBottom: '10mm' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            {label('PRESCRIBER')}
            <div style={{ fontSize: '10pt', marginTop: '1.6mm' }}>{doc.clinic.name}</div>
            <div style={{ fontSize: '9.5pt', color: '#555', marginTop: '1.2mm' }}>{doc.clinic.tagline_en}</div>
          </div>
          <div style={{ width: '62mm', textAlign: 'center' }}>
            <div style={{ borderBottom: `0.8pt solid ${C.gray900}`, height: '12mm', marginBottom: '1.6mm' }} />
            <div style={{ fontSize: '9pt', color: '#999' }}>{T.signature.en} / {T.signature.th}</div>
            <div style={{ fontWeight: 600, fontSize: '10.5pt', marginTop: '1.6mm' }}>{doc.prescriber.name || ''}</div>
            {doc.prescriber.license_number && (
              <div style={{ fontSize: '9.5pt', color: '#555', marginTop: '1.2mm' }}>
                {T.license.en} {doc.prescriber.license_number}
              </div>
            )}
          </div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: '14mm', textAlign: 'center', fontSize: '8pt', color: '#999' }}>
        {T.validity.en} / {T.validity.th}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────
export default function PrescriptionWriter() {
  const [patientQuery, setPatientQuery] = useState('');
  const [patientResults, setPatientResults] = useState([]);
  const [patient, setPatient] = useState(null);
  const [diagnosisEn, setDiagnosisEn] = useState('');
  const [diagnosisTh, setDiagnosisTh] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState([]);
  const [drugQuery, setDrugQuery] = useState('');
  const [drugResults, setDrugResults] = useState([]);
  const [extractAvailable, setExtractAvailable] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const [saving, setSaving] = useState(false);
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  // Patient search
  useEffect(() => {
    if (patientQuery.length < 2) { setPatientResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`${PATIENT_API}?search=${encodeURIComponent(patientQuery)}&per_page=8`);
        const d = await r.json();
        setPatientResults(d.patients || d.items || []);
      } catch (e) { /* silent */ }
    }, 300);
    return () => clearTimeout(t);
  }, [patientQuery]);

  // Drug search
  useEffect(() => {
    if (drugQuery.length < 2) { setDrugResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`${API}/drugs?search=${encodeURIComponent(drugQuery)}&per_page=8`);
        const d = await r.json();
        setDrugResults(d.drugs || d.items || []);
      } catch (e) { /* silent */ }
    }, 300);
    return () => clearTimeout(t);
  }, [drugQuery]);

  const addDrug = (drug) => {
    setItems((xs) => [...xs, {
      id: nextId(),
      drug_id: drug.id,
      display_name: [drug.brand_name || drug.generic_name, drug.strength, (drug.form || '').replace('_', ' ')].filter(Boolean).join(' '),
      generic: drug.generic_name,
      unit: drug.unit || 'tablet',
      unit_th: drug.unit_th || '',
      pack_size: drug.pack_size,
      route: 'oral',
      dose_per_time: 1,
      times_per_day: 2,
      duration_days: 14,
      instruction_en: '',
      instruction_th: '',
      sig_en_override: '',
      sig_th_override: '',
      quantity_override: '',
    }]);
    setDrugQuery('');
    setDrugResults([]);
  };

  const upItem = (id, k, v) => setItems((xs) => xs.map((x) => {
    if (x.id !== id) return x;
    const next = { ...x, [k]: v };
    // structural changes regenerate the auto sig
    if (['dose_per_time', 'times_per_day', 'route', 'instruction_en', 'instruction_th'].includes(k)) {
      next.sig_en_override = '';
      next.sig_th_override = '';
    }
    return next;
  }));
  const removeItem = (id) => setItems((xs) => xs.filter((x) => x.id !== id));

  // Document extraction (accepts HEIC — converted server-side)
  const handleFile = async (file) => {
    if (!file) return;
    setError('');
    setExtracting(true);
    setExtracted(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API}/prescriptions/extract`, { method: 'POST', body: fd });
      if (r.status === 503) { setExtractAvailable(false); return; }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setExtracted(d);
      if (d.diagnosis) setDiagnosisEn(d.diagnosis);
      if (d.hn && !patient) setPatientQuery(d.hn);
      else if (d.patient_name && !patient) setPatientQuery(d.patient_name);
      const meds = (d.medications || []).filter((m) => m.drug_id).map((m) => ({
        id: nextId(),
        drug_id: m.drug_id,
        display_name: m.catalogue_name || m.name,
        generic: null,
        unit: m.unit || 'tablet',
        unit_th: m.unit_th || '',
        pack_size: m.pack_size,
        route: m.route || 'oral',
        dose_per_time: m.dose_per_time || 1,
        times_per_day: m.times_per_day || 2,
        duration_days: m.duration_days || 14,
        instruction_en: m.instruction || '',
        instruction_th: '',
        sig_en_override: '',
        sig_th_override: '',
        quantity_override: '',
      }));
      if (meds.length) setItems(meds);
      const unmatched = (d.medications || []).filter((m) => !m.drug_id);
      if (unmatched.length) {
        setError(`Not in catalogue — add manually / ไม่พบในคลังยา: ${unmatched.map((m) => m.name).join(', ')}`);
      }
    } catch (e) {
      setError('Extraction failed — enter details manually / ดึงข้อมูลไม่สำเร็จ กรุณากรอกเอง');
    } finally {
      setExtracting(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const save = async (thenPrint) => {
    setError('');
    if (!patient) { setError('Select a patient / กรุณาเลือกผู้ป่วย'); return; }
    if (!items.length) { setError('Add at least one medication / เพิ่มยาอย่างน้อย 1 รายการ'); return; }
    setSaving(true);
    try {
      const payload = {
        patient_id: patient.id,
        diagnosis_en: diagnosisEn || null,
        diagnosis_th: diagnosisTh || null,
        notes: notes || null,
        items: items.map((it) => ({
          drug_id: it.drug_id,
          dose_per_time: Number(it.dose_per_time),
          times_per_day: Number(it.times_per_day),
          duration_days: Number(it.duration_days),
          route: it.route,
          instruction_en: it.instruction_en || null,
          instruction_th: it.instruction_th || null,
          sig_en_override: it.sig_en_override || null,
          sig_th_override: it.sig_th_override || null,
          quantity_override: it.quantity_override ? Number(it.quantity_override) : null,
        })),
      };
      const r = await fetch(`${API}/prescriptions/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const created = await r.json();
      const dr = await fetch(`${API}/prescriptions/${created.id}/document`);
      const document_ = await dr.json();
      setDoc(document_);
      if (thenPrint) setTimeout(() => window.print(), 300);
    } catch (e) {
      setError('Save failed / บันทึกไม่สำเร็จ');
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    setPatient(null); setPatientQuery(''); setDiagnosisEn(''); setDiagnosisTh('');
    setNotes(''); setItems([]); setDoc(null); setExtracted(null); setError('');
  };

  return (
    <div style={{ fontFamily: "'Cloud', sans-serif", background: C.gray50, minHeight: '100vh' }}>
      <style>{`
        @media print {
          .rx-no-print { display: none !important; }
          .rx-print-area { display: block !important; }
          .rx-sheet { box-shadow: none !important; margin: 0 !important; }
          @page { size: A4; margin: 0; }
          html, body { margin: 0; padding: 0; background: #fff; }
        }
        .rx-print-area { display: none; }
      `}</style>

      {/* ── Editor (hidden on print) ─────────────────────── */}
      <div className="rx-no-print" style={{ maxWidth: 860, margin: '0 auto', padding: '16px 14px 60px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: C.gray900, margin: 0 }}>{bi('title')}</h1>
          {doc && <Btn kind="ghost" onClick={reset}>{bi('newRx')}</Btn>}
        </div>

        {/* Extraction upload */}
        {extractAvailable && !doc && (
          <section style={{ background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14.5, marginBottom: 6 }}>{bi('fillFromDoc')}</div>
            <p style={{ fontSize: 12, color: C.gray500, margin: '0 0 10px', lineHeight: 1.5 }}>{T.fillHint.en}<br />{T.fillHint.th}</p>
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.heic,.heif,application/pdf"
              disabled={extracting}
              onChange={(e) => handleFile(e.target.files && e.target.files[0])}
              style={{ ...inputStyle, padding: '16px 10px', borderStyle: 'dashed', background: C.gray50 }}
            />
            {extracting && <div style={{ marginTop: 8, fontSize: 13, color: C.sapphire }}>{bi('extracting')}</div>}
            {extracted && extracted.patient_name && (
              <div style={{ marginTop: 8, fontSize: 12.5, color: C.emerald }}>
                ✓ {extracted.patient_name}{extracted.hn ? ` · HN ${extracted.hn}` : ''} · {(extracted.medications || []).length} medication(s)
              </div>
            )}
          </section>
        )}

        {/* Patient */}
        {!doc && (
          <section style={{ background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14.5, marginBottom: 8 }}>{bi('patient')}</div>
            {patient ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: C.sapphireMuted, borderRadius: 6, padding: '10px 12px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{[patient.prefix_en, patient.first_name_en, patient.last_name_en].filter(Boolean).join(' ')}</div>
                  <div style={{ fontSize: 12, color: C.gray500 }}>{patient.hn_number}{patient.id_number ? ` · ${patient.id_number}` : ''}</div>
                </div>
                <Btn kind="ghost" onClick={() => setPatient(null)}>✕</Btn>
              </div>
            ) : (
              <>
                <input style={inputStyle} placeholder={bi('searchPatient')} value={patientQuery} onChange={(e) => setPatientQuery(e.target.value)} />
                {patientResults.map((p) => (
                  <button key={p.id} onClick={() => { setPatient(p); setPatientResults([]); setPatientQuery(''); }}
                    style={{ display: 'block', width: '100%', textAlign: 'left', background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 6, padding: '9px 12px', marginTop: 6, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14 }}>
                    <b>{[p.prefix_en, p.first_name_en, p.last_name_en].filter(Boolean).join(' ')}</b>
                    <span style={{ color: C.gray500, fontSize: 12.5 }}> — {p.hn_number}</span>
                  </button>
                ))}
              </>
            )}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              <Fld label={bi('diagnosis')}><textarea rows={2} style={{ ...inputStyle, resize: 'vertical' }} value={diagnosisEn} onChange={(e) => setDiagnosisEn(e.target.value)} /></Fld>
              <Fld label={bi('diagnosisTh')}><textarea rows={2} style={{ ...inputStyle, resize: 'vertical' }} value={diagnosisTh} onChange={(e) => setDiagnosisTh(e.target.value)} /></Fld>
            </div>
          </section>
        )}

        {/* Medications */}
        {!doc && (
          <section style={{ background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14.5, marginBottom: 8 }}>{bi('medications')}</div>
            <input style={inputStyle} placeholder={bi('searchDrug')} value={drugQuery} onChange={(e) => setDrugQuery(e.target.value)} />
            {drugResults.map((d) => (
              <button key={d.id} onClick={() => addDrug(d)}
                style={{ display: 'block', width: '100%', textAlign: 'left', background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 6, padding: '9px 12px', marginTop: 6, cursor: 'pointer', fontFamily: 'inherit', fontSize: 14 }}>
                <b>{[d.brand_name || d.generic_name, d.strength].filter(Boolean).join(' ')}</b>
                <span style={{ color: C.gray500, fontSize: 12.5 }}>
                  {' '}— {d.generic_name}{d.pack_size ? ` · pack of ${d.pack_size}` : ''} · stock {d.current_stock}
                </span>
              </button>
            ))}

            {items.map((it, i) => (
              <div key={it.id} style={{ border: `1px solid ${C.gray200}`, borderRadius: 8, padding: '10px 10px 4px', marginTop: 12, background: C.gray50 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontWeight: 700, color: C.ruby, width: 18, textAlign: 'center' }}>{i + 1}</span>
                  <div style={{ fontWeight: 600, flex: 1 }}>{it.display_name}</div>
                  <button onClick={() => removeItem(it.id)} title={bi('remove')} style={{ border: 'none', background: 'none', color: C.gray500, cursor: 'pointer', fontSize: 14 }}>✕</button>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Fld label={bi('perDose')} w="76px"><input type="number" min="0" step="0.5" style={inputStyle} value={it.dose_per_time} onChange={(e) => upItem(it.id, 'dose_per_time', e.target.value)} /></Fld>
                  <Fld label={bi('timesPerDay')} w="76px"><input type="number" min="0" style={inputStyle} value={it.times_per_day} onChange={(e) => upItem(it.id, 'times_per_day', e.target.value)} /></Fld>
                  <Fld label={bi('days')} w="76px"><input type="number" min="0" style={inputStyle} value={it.duration_days} onChange={(e) => upItem(it.id, 'duration_days', e.target.value)} /></Fld>
                  <Fld label={bi('route')} w="140px">
                    <select style={inputStyle} value={it.route} onChange={(e) => upItem(it.id, 'route', e.target.value)}>
                      {ROUTES.map((r) => <option key={r} value={r}>{r} / {ROUTE_TH[r]}</option>)}
                    </select>
                  </Fld>
                  <Fld label={bi('instruction')}><input style={inputStyle} value={it.instruction_en} onChange={(e) => upItem(it.id, 'instruction_en', e.target.value)} placeholder="after meals" /></Fld>
                  <Fld label="คำแนะนำ (ไทย)"><input style={inputStyle} value={it.instruction_th} onChange={(e) => upItem(it.id, 'instruction_th', e.target.value)} placeholder="หลังอาหาร" /></Fld>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Fld label={bi('sig')}>
                    <input style={inputStyle} value={it.sig_en_override || sigEn(it)} onChange={(e) => upItem(it.id, 'sig_en_override', e.target.value)} />
                  </Fld>
                  <Fld label="วิธีใช้ (ไทย)">
                    <input style={inputStyle} value={it.sig_th_override || sigTh(it)} onChange={(e) => upItem(it.id, 'sig_th_override', e.target.value)} />
                  </Fld>
                  <Fld label={bi('quantity')} w="110px">
                    <input type="number" min="0" style={{ ...inputStyle, fontWeight: 700 }} value={it.quantity_override !== '' ? it.quantity_override : finalQty(it)} onChange={(e) => upItem(it.id, 'quantity_override', e.target.value)} />
                  </Fld>
                </div>
                <div style={{ fontSize: 11.5, color: C.gray500, padding: '0 2px 8px' }}>
                  Need {needed(it)} {it.unit}{Number(it.pack_size) > 0 && needed(it) > 0 ? ` → ${Math.ceil(needed(it) / Number(it.pack_size))} × pack of ${it.pack_size} = ${computedQty(it)}` : ''}
                  {it.quantity_override !== '' && it.quantity_override != null && it.quantity_override !== undefined && String(it.quantity_override).length > 0 && (
                    <button onClick={() => upItem(it.id, 'quantity_override', '')} style={{ border: 'none', background: 'none', color: C.ruby, fontSize: 11.5, cursor: 'pointer', textDecoration: 'underline', marginLeft: 8, padding: 0 }}>reset qty</button>
                  )}
                </div>
              </div>
            ))}
          </section>
        )}

        {/* Note + actions */}
        {!doc && (
          <>
            <section style={{ background: C.white, border: `1px solid ${C.gray200}`, borderRadius: 10, padding: 14, marginBottom: 12 }}>
              <Fld label={bi('note')}>
                <input style={inputStyle} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Continue both medications until 12 weeks of pregnancy." />
              </Fld>
            </section>
            {error && <div style={{ color: C.rubyDark, fontSize: 13, marginBottom: 10 }}>{error}</div>}
            <div style={{ display: 'flex', gap: 10 }}>
              <Btn kind="ghost" style={{ flex: 1 }} disabled={saving} onClick={() => save(false)}>{bi('save')}</Btn>
              <Btn kind="primary" style={{ flex: 2, padding: 13 }} disabled={saving} onClick={() => save(true)}>{saving ? '…' : bi('saveAndPrint')}</Btn>
            </div>
          </>
        )}

        {/* Saved: on-screen preview */}
        {doc && (
          <>
            {error && <div style={{ color: C.rubyDark, fontSize: 13, marginBottom: 10 }}>{error}</div>}
            <div style={{ overflowX: 'auto', marginBottom: 14 }}>
              <PrintSheet doc={doc} />
            </div>
            <Btn kind="primary" style={{ width: '100%', padding: 13 }} onClick={() => window.print()}>{bi('print')}</Btn>
          </>
        )}
      </div>

      {/* ── Print-only sheet ─────────────────────────────── */}
      <div className="rx-print-area">
        <PrintSheet doc={doc} />
      </div>
    </div>
  );
}
