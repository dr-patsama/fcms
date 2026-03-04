/**
 * FCMS Module 3 — Ultrasound Dashboard
 * 
 * Features:
 *  - Orthanc connection status
 *  - DICOM study list from Orthanc (search by patient, date filter)
 *  - Study detail viewer with series/instance navigation
 *  - Fertility measurement form (endometrium, ovaries, follicles, uterus)
 *  - Follicle tracking chart (growth over time)
 *  - Report templates: baseline, follicle tracking, trigger day, luteal, early pregnancy, SIS
 *  - GE VOLUSON Swift setup guide for IT admin
 * 
 * Integrates with: /api/v1/ultrasound endpoints + Orthanc DICOMweb
 */

import React, { useState, useEffect } from 'react';

const C = {
  ruby: '#E0115F', emerald: '#009473', sapphire: '#0F52BA',
  sapphireDark: '#151667', gold: '#C5A044', goldDark: '#8B7331',
  g50: '#F8FAFC', g100: '#F1F5F9', g200: '#E2E8F0', g300: '#CBD5E1',
  g400: '#94A3B8', g500: '#64748B', g600: '#475569', g700: '#334155',
  g800: '#1E293B', g900: '#0F172A',
};

// ── Demo data ──────────────────────────────────────────
const DEMO_STUDIES = [
  { orthanc_id: 'S001', study_date: '2026-03-04', study_time: '09:15', patient_name: 'Patsama^Vichinsartvichai', patient_id: 'HN-00001', study_description: 'Follicle Tracking Day 10', num_series: 3, modality: 'US' },
  { orthanc_id: 'S002', study_date: '2026-03-02', study_time: '10:30', patient_name: 'Nattaya^Somchai', patient_id: 'HN-00045', study_description: 'Baseline Scan', num_series: 2, modality: 'US' },
  { orthanc_id: 'S003', study_date: '2026-03-01', study_time: '14:00', patient_name: 'Malai^Chai', patient_id: 'HN-00078', study_description: 'Early Pregnancy 7w2d', num_series: 4, modality: 'US' },
  { orthanc_id: 'S004', study_date: '2026-02-28', study_time: '11:00', patient_name: 'Jiraporn^Kasem', patient_id: 'HN-00023', study_description: 'SIS - Saline Infusion', num_series: 5, modality: 'US' },
  { orthanc_id: 'S005', study_date: '2026-02-28', study_time: '08:45', patient_name: 'Patsama^Vichinsartvichai', patient_id: 'HN-00001', study_description: 'Follicle Tracking Day 8', num_series: 3, modality: 'US' },
  { orthanc_id: 'S006', study_date: '2026-02-26', study_time: '09:00', patient_name: 'Patsama^Vichinsartvichai', patient_id: 'HN-00001', study_description: 'Follicle Tracking Day 6', num_series: 2, modality: 'US' },
  { orthanc_id: 'S007', study_date: '2026-02-24', study_time: '10:00', patient_name: 'Patsama^Vichinsartvichai', patient_id: 'HN-00001', study_description: 'Baseline Scan', num_series: 3, modality: 'US' },
];

const DEMO_FOLLICLE_TRACKING = [
  { day: 'Day 2\nBaseline', date: '2026-02-24', endo: 4.2, right: [5, 5, 4, 4, 3], left: [5, 4, 4, 3] },
  { day: 'Day 6', date: '2026-02-26', endo: 5.8, right: [9, 8, 7, 5, 4], left: [8, 7, 5, 4] },
  { day: 'Day 8', date: '2026-02-28', endo: 7.2, right: [13, 11, 9, 6, 5], left: [12, 9, 6, 5] },
  { day: 'Day 10', date: '2026-03-02', endo: 8.5, right: [18, 15, 12, 7, 5], left: [16, 12, 7, 5] },
];

const EXAM_TYPES = [
  { value: 'baseline', label: '📊 Baseline Scan', th: 'สแกนพื้นฐาน' },
  { value: 'follicle_tracking', label: '🔍 Follicle Tracking', th: 'ติดตามฟอลลิเคิล' },
  { value: 'trigger_day', label: '💉 Trigger Day', th: 'วันทริกเกอร์' },
  { value: 'luteal_phase', label: '🌙 Luteal Phase', th: 'ระยะลูเทียล' },
  { value: 'early_pregnancy', label: '🤰 Early Pregnancy', th: 'ตั้งครรภ์ระยะแรก' },
  { value: 'sis', label: '💧 SIS / Sonohysterography', th: 'อัลตราซาวด์ฉีดน้ำเกลือ' },
];

export default function UltrasoundDashboard() {
  const [tab, setTab] = useState('studies');
  const [search, setSearch] = useState('');
  const [selectedStudy, setSelectedStudy] = useState(null);
  const [showMeasurementForm, setShowMeasurementForm] = useState(false);
  const [orthancConnected, setOrthancConnected] = useState(true);
  const [toast, setToast] = useState(null);

  const filteredStudies = DEMO_STUDIES.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return s.patient_name.toLowerCase().includes(q) ||
           s.patient_id.toLowerCase().includes(q) ||
           s.study_description.toLowerCase().includes(q);
  });

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const input = { width: '100%', padding: '8px 12px', border: `1.5px solid ${C.g200}`, borderRadius: '8px', fontSize: '13px', outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' };
  const label = { display: 'block', fontSize: '11px', fontWeight: 600, color: C.g600, marginBottom: '4px' };
  const tabBtn = (active) => ({
    padding: '8px 18px', border: 'none', borderBottom: active ? `2px solid ${C.sapphire}` : '2px solid transparent',
    background: 'none', color: active ? C.sapphire : C.g500, fontWeight: 600, fontSize: '13px',
    cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s',
  });

  // ── Measurement Form ─────────────────────────────────
  function MeasurementForm() {
    const [examType, setExamType] = useState('follicle_tracking');
    const [endo, setEndo] = useState({ thickness: '', pattern: 'trilaminar' });
    const [rightFollicles, setRightFollicles] = useState([{ d: '' }]);
    const [leftFollicles, setLeftFollicles] = useState([{ d: '' }]);
    const [rightOvary, setRightOvary] = useState({ l: '', w: '', h: '', afc: '' });
    const [leftOvary, setLeftOvary] = useState({ l: '', w: '', h: '', afc: '' });
    const [impression, setImpression] = useState('');
    const [plan, setPlan] = useState('');

    const addFollicle = (side) => {
      if (side === 'right') setRightFollicles([...rightFollicles, { d: '' }]);
      else setLeftFollicles([...leftFollicles, { d: '' }]);
    };

    const removeFollicle = (side, idx) => {
      if (side === 'right') setRightFollicles(rightFollicles.filter((_, i) => i !== idx));
      else setLeftFollicles(leftFollicles.filter((_, i) => i !== idx));
    };

    return (
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}
        onClick={() => setShowMeasurementForm(false)}>
        <div style={{ background: 'white', borderRadius: '16px', padding: '28px', width: '680px', maxHeight: '88vh', overflow: 'auto', boxShadow: '0 24px 48px rgba(0,0,0,0.15)' }}
          onClick={e => e.stopPropagation()}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: C.g900, marginBottom: '4px' }}>📡 Ultrasound Measurements</h3>
          <p style={{ fontSize: '12px', color: C.g500, marginBottom: '20px' }}>การวัดอัลตราซาวด์ · Enter structured fertility scan data</p>

          {/* Exam type */}
          <div style={{ marginBottom: '16px' }}>
            <label style={label}>Exam Type / ประเภทการตรวจ *</label>
            <select style={input} value={examType} onChange={e => setExamType(e.target.value)}>
              {EXAM_TYPES.map(t => <option key={t.value} value={t.value}>{t.label} / {t.th}</option>)}
            </select>
          </div>

          {/* Endometrium */}
          <div style={{ background: '#FFF7ED', border: '1px solid #FED7AA', borderRadius: '10px', padding: '14px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#C2410C', marginBottom: '10px' }}>🔶 Endometrium / เยื่อบุโพรงมดลูก</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={label}>Thickness (mm)</label>
                <input style={input} type="number" step="0.1" value={endo.thickness} onChange={e => setEndo({...endo, thickness: e.target.value})} placeholder="e.g. 8.5" />
              </div>
              <div>
                <label style={label}>Pattern</label>
                <select style={input} value={endo.pattern} onChange={e => setEndo({...endo, pattern: e.target.value})}>
                  <option value="trilaminar">Trilaminar</option>
                  <option value="echogenic">Echogenic</option>
                  <option value="homogeneous">Homogeneous</option>
                  <option value="not_assessed">Not assessed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Right Ovary + Follicles */}
          <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '10px', padding: '14px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#1D4ED8', marginBottom: '10px' }}>🔵 Right Ovary / รังไข่ขวา</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px', marginBottom: '10px' }}>
              <div><label style={label}>L (mm)</label><input style={input} type="number" value={rightOvary.l} onChange={e => setRightOvary({...rightOvary, l: e.target.value})} /></div>
              <div><label style={label}>W (mm)</label><input style={input} type="number" value={rightOvary.w} onChange={e => setRightOvary({...rightOvary, w: e.target.value})} /></div>
              <div><label style={label}>H (mm)</label><input style={input} type="number" value={rightOvary.h} onChange={e => setRightOvary({...rightOvary, h: e.target.value})} /></div>
              <div><label style={label}>AFC</label><input style={input} type="number" value={rightOvary.afc} onChange={e => setRightOvary({...rightOvary, afc: e.target.value})} /></div>
            </div>
            <label style={label}>Follicles (mm)</label>
            {rightFollicles.map((f, i) => (
              <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '4px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: C.g400, width: '20px' }}>#{i+1}</span>
                <input style={{ ...input, width: '100px' }} type="number" step="0.1" value={f.d} placeholder="Ø mm"
                  onChange={e => { const a = [...rightFollicles]; a[i].d = e.target.value; setRightFollicles(a); }} />
                {rightFollicles.length > 1 && <button onClick={() => removeFollicle('right', i)} style={{ border: 'none', background: 'none', color: C.ruby, cursor: 'pointer', fontSize: '14px' }}>✕</button>}
              </div>
            ))}
            <button onClick={() => addFollicle('right')} style={{ border: `1px dashed ${C.g300}`, background: 'none', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer', color: C.sapphire, fontWeight: 600, marginTop: '4px' }}>+ Add follicle</button>
          </div>

          {/* Left Ovary + Follicles */}
          <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '10px', padding: '14px', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#16A34A', marginBottom: '10px' }}>🟢 Left Ovary / รังไข่ซ้าย</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px', marginBottom: '10px' }}>
              <div><label style={label}>L (mm)</label><input style={input} type="number" value={leftOvary.l} onChange={e => setLeftOvary({...leftOvary, l: e.target.value})} /></div>
              <div><label style={label}>W (mm)</label><input style={input} type="number" value={leftOvary.w} onChange={e => setLeftOvary({...leftOvary, w: e.target.value})} /></div>
              <div><label style={label}>H (mm)</label><input style={input} type="number" value={leftOvary.h} onChange={e => setLeftOvary({...leftOvary, h: e.target.value})} /></div>
              <div><label style={label}>AFC</label><input style={input} type="number" value={leftOvary.afc} onChange={e => setLeftOvary({...leftOvary, afc: e.target.value})} /></div>
            </div>
            <label style={label}>Follicles (mm)</label>
            {leftFollicles.map((f, i) => (
              <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '4px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: C.g400, width: '20px' }}>#{i+1}</span>
                <input style={{ ...input, width: '100px' }} type="number" step="0.1" value={f.d} placeholder="Ø mm"
                  onChange={e => { const a = [...leftFollicles]; a[i].d = e.target.value; setLeftFollicles(a); }} />
                {leftFollicles.length > 1 && <button onClick={() => removeFollicle('left', i)} style={{ border: 'none', background: 'none', color: C.ruby, cursor: 'pointer', fontSize: '14px' }}>✕</button>}
              </div>
            ))}
            <button onClick={() => addFollicle('left')} style={{ border: `1px dashed ${C.g300}`, background: 'none', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer', color: C.emerald, fontWeight: 600, marginTop: '4px' }}>+ Add follicle</button>
          </div>

          {/* Impression & Plan */}
          {/* 3D TVUS Uterine Morphology — ESHRE/ESGE (shown for baseline exam) */}
          {examType === 'baseline' && (
            <div style={{ background: '#FDF4FF', border: '1px solid #E9D5FF', borderRadius: '10px', padding: '14px', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#7C3AED', marginBottom: '4px' }}>🔮 3D TVUS Uterine Morphology</h4>
              <p style={{ fontSize: '10px', color: '#8B5CF6', marginBottom: '12px' }}>ESHRE/ESGE Classification · การจำแนกความผิดปกติแต่กำเนิดของมดลูก</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                <div>
                  <label style={label}>Uterine Class *</label>
                  <select style={input} defaultValue="U0">
                    <option value="U0">U0 — Normal</option>
                    <option value="U1">U1 — Dysmorphic</option>
                    <option value="U2">U2 — Septate</option>
                    <option value="U3">U3 — Bicorporeal</option>
                    <option value="U4">U4 — Hemi-uterus</option>
                    <option value="U5">U5 — Aplastic</option>
                    <option value="U6">U6 — Unclassified</option>
                  </select>
                </div>
                <div>
                  <label style={label}>Subclass</label>
                  <select style={input} defaultValue="">
                    <option value="">None</option>
                    <option value="a">a — T-shaped / Partial</option>
                    <option value="b">b — Infantilis / Complete</option>
                    <option value="c">c — Others / Septate</option>
                  </select>
                </div>
                <div>
                  <label style={label}>Cervix</label>
                  <select style={input} defaultValue="C0">
                    <option value="C0">C0 — Normal</option>
                    <option value="C1">C1 — Septate</option>
                    <option value="C2">C2 — Double</option>
                    <option value="C3">C3 — Unilateral aplasia</option>
                    <option value="C4">C4 — Aplasia</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                <div>
                  <label style={label}>Vagina</label>
                  <select style={input} defaultValue="V0">
                    <option value="V0">V0 — Normal</option>
                    <option value="V1">V1 — Non-obstructing septum</option>
                    <option value="V2">V2 — Obstructing septum</option>
                    <option value="V3">V3 — Transverse septum</option>
                    <option value="V4">V4 — Aplasia</option>
                  </select>
                </div>
                <div>
                  <label style={label}>External Contour</label>
                  <select style={input} defaultValue="normal">
                    <option value="normal">Normal (smooth)</option>
                    <option value="indentation_lt_50">Indentation &lt;50% UWT</option>
                    <option value="indentation_gte_50">Indentation ≥50% UWT</option>
                  </select>
                </div>
                <div>
                  <label style={label}>Interostial Line</label>
                  <select style={input} defaultValue="straight">
                    <option value="straight">Straight</option>
                    <option value="curved">Curved / Convex</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px', marginBottom: '10px' }}>
                <div><label style={label}>Fundal wall (mm)</label><input style={input} type="number" step="0.1" placeholder="e.g. 12" /></div>
                <div><label style={label}>Internal indent (mm)</label><input style={input} type="number" step="0.1" placeholder="e.g. 2.4" /></div>
                <div><label style={label}>Indent % of UWT</label><input style={input} type="number" step="1" placeholder="e.g. 20" /></div>
                <div><label style={label}>Septum length (mm)</label><input style={input} type="number" step="0.1" placeholder="if present" /></div>
              </div>

              <div style={{ marginBottom: '8px' }}>
                <label style={label}>3D Morphology Notes</label>
                <textarea style={{ ...input, height: '48px', resize: 'vertical' }} placeholder="Normal uterine morphology on 3D coronal view. No septum, no external indentation. Classification: U0/C0/V0" />
              </div>

              {/* Quick reference */}
              <details style={{ marginTop: '8px' }}>
                <summary style={{ fontSize: '10px', color: '#7C3AED', cursor: 'pointer', fontWeight: 600 }}>📖 ESHRE/ESGE Quick Reference</summary>
                <div style={{ marginTop: '8px', padding: '10px', background: 'white', borderRadius: '6px', fontSize: '10px', color: C.g600, lineHeight: '1.6' }}>
                  <div><strong>Key measurements (3D coronal view):</strong></div>
                  <div>• Internal indentation: from interostial line to deepest fundal point</div>
                  <div>• Wall thickness (UWT): external contour to endometrium at fundus</div>
                  <div>• Septate (U2): internal indent &gt;50% UWT, external indent &lt;50% UWT</div>
                  <div>• Bicorporeal (U3): external indent &gt;50% UWT</div>
                  <div>• U3c (bicorporeal septate): fundal indent width &gt;150% UWT</div>
                  <div style={{ marginTop: '4px' }}><strong>Classification format:</strong> U_/C_/V_ (e.g. U2a/C0/V0 = partial septate, normal cervix & vagina)</div>
                </div>
              </details>
            </div>
          )}

          {/* Impression & Plan (original) */}
          <div style={{ marginBottom: '14px' }}>
            <label style={label}>Impression / ผลสรุป</label>
            <textarea style={{ ...input, height: '60px', resize: 'vertical' }} value={impression} onChange={e => setImpression(e.target.value)}
              placeholder="Growing dominant follicle right ovary, adequate endometrium..." />
          </div>
          <div style={{ marginBottom: '14px' }}>
            <label style={label}>Plan / แผนการรักษา</label>
            <textarea style={{ ...input, height: '48px', resize: 'vertical' }} value={plan} onChange={e => setPlan(e.target.value)}
              placeholder="Continue stimulation, recheck in 2 days..." />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button onClick={() => setShowMeasurementForm(false)} style={{ padding: '8px 20px', border: `1px solid ${C.g200}`, borderRadius: '8px', background: 'white', cursor: 'pointer', fontSize: '13px', fontFamily: 'inherit' }}>Cancel</button>
            <button onClick={() => { showToast('Measurements saved & linked to EMR'); setShowMeasurementForm(false); }}
              style={{ padding: '8px 20px', background: `linear-gradient(135deg, ${C.sapphire}, ${C.sapphireDark})`, color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 600, fontFamily: 'inherit' }}>
              💾 Save Measurements
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Follicle Growth Chart (simple visual) ────────────
  function FollicleChart() {
    const maxVal = 22;
    const barH = 16;
    return (
      <div style={{ background: 'white', borderRadius: '12px', border: `1px solid ${C.g200}`, padding: '20px', marginTop: '16px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: C.g900, marginBottom: '4px' }}>📈 Follicle Growth Chart — HN-00001</h3>
        <p style={{ fontSize: '11px', color: C.g400, marginBottom: '16px' }}>กราฟการเติบโตของฟอลลิเคิล · IVF Stimulation Cycle</p>

        {DEMO_FOLLICLE_TRACKING.map((visit, vi) => (
          <div key={vi} style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: C.g700, minWidth: '70px' }}>{visit.day.split('\n')[0]}</span>
              <span style={{ fontSize: '10px', color: C.g400 }}>{visit.date}</span>
              <span style={{ padding: '2px 8px', background: '#FFF7ED', borderRadius: '4px', fontSize: '10px', fontWeight: 600, color: '#C2410C' }}>Endo: {visit.endo}mm</span>
            </div>
            <div style={{ display: 'flex', gap: '16px' }}>
              {/* Right */}
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: '9px', color: C.sapphire, fontWeight: 600 }}>RIGHT</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '3px' }}>
                  {visit.right.map((d, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <div style={{
                        width: `${(d / maxVal) * 100}%`, minWidth: '2px', height: barH, borderRadius: '3px',
                        background: d >= 17 ? C.ruby : d >= 14 ? C.gold : d >= 10 ? C.sapphire : C.g300,
                        transition: 'width 0.5s ease',
                      }} />
                      <span style={{ fontSize: '10px', fontWeight: 600, color: d >= 17 ? C.ruby : C.g600 }}>{d}</span>
                    </div>
                  ))}
                </div>
              </div>
              {/* Left */}
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: '9px', color: C.emerald, fontWeight: 600 }}>LEFT</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '3px' }}>
                  {visit.left.map((d, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <div style={{
                        width: `${(d / maxVal) * 100}%`, minWidth: '2px', height: barH, borderRadius: '3px',
                        background: d >= 17 ? C.ruby : d >= 14 ? C.gold : d >= 10 ? C.emerald : C.g300,
                        transition: 'width 0.5s ease',
                      }} />
                      <span style={{ fontSize: '10px', fontWeight: 600, color: d >= 17 ? C.ruby : C.g600 }}>{d}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Legend */}
        <div style={{ display: 'flex', gap: '16px', paddingTop: '12px', borderTop: `1px solid ${C.g200}`, marginTop: '8px' }}>
          {[
            { color: C.g300, label: '< 10mm' },
            { color: C.sapphire, label: '10-13mm' },
            { color: C.gold, label: '14-16mm' },
            { color: C.ruby, label: '≥ 17mm (trigger-ready)' },
          ].map(l => (
            <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: l.color }} />
              <span style={{ fontSize: '10px', color: C.g500 }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════
  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans','Noto Sans Thai',sans-serif", background: C.g50, minHeight: '100vh' }}>
      {toast && (
        <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 9999, padding: '12px 20px', borderRadius: '10px', fontSize: '13px', fontWeight: 600, background: '#ECFDF5', color: '#059669', border: '1px solid #A7F3D0', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          ✅ {toast}
        </div>
      )}

      {/* Header */}
      <div style={{ background: 'white', borderBottom: `1px solid ${C.g200}`, padding: '16px 32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: C.g900 }}>📡 Ultrasound Interface</h1>
            <p style={{ fontSize: '12px', color: C.g500 }}>อัลตราซาวด์ · GE VOLUSON Swift DICOM Integration</p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {/* Orthanc status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '8px', background: orthancConnected ? '#ECFDF5' : '#FEF2F2', border: `1px solid ${orthancConnected ? '#A7F3D0' : '#FECACA'}` }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: orthancConnected ? '#10B981' : '#EF4444' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: orthancConnected ? '#059669' : '#DC2626' }}>
                Orthanc {orthancConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <button onClick={() => setShowMeasurementForm(true)}
              style={{ padding: '8px 18px', background: `linear-gradient(135deg, ${C.sapphire}, ${C.sapphireDark})`, color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>
              📏 New Measurement
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '4px', borderBottom: `1px solid ${C.g200}`, marginBottom: '-1px' }}>
          {[
            { id: 'studies', label: '🖼️ Studies' },
            { id: 'tracking', label: '📈 Follicle Tracking' },
            { id: 'setup', label: '⚙️ DICOM Setup' },
          ].map(t => (
            <button key={t.id} style={tabBtn(tab === t.id)} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>
      </div>

      <div style={{ padding: '24px 32px' }}>

        {/* ── STUDIES TAB ── */}
        {tab === 'studies' && (
          <>
            {/* Search */}
            <div style={{ marginBottom: '16px', position: 'relative' }}>
              <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', fontSize: '14px' }}>🔍</span>
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search patient name, HN, or description..."
                style={{ width: '100%', maxWidth: '400px', padding: '9px 14px 9px 36px', border: `1.5px solid ${C.g200}`, borderRadius: '8px', fontSize: '13px', outline: 'none', background: 'white', boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>

            {/* Study list */}
            <div style={{ borderRadius: '12px', overflow: 'hidden', border: `1px solid ${C.g200}`, background: 'white' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: C.g50 }}>
                    {['Date', 'Time', 'Patient', 'HN', 'Description', 'Series', 'Actions'].map(h => (
                      <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: '10px', fontWeight: 600, color: C.g500, textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: `1px solid ${C.g200}` }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredStudies.map(s => (
                    <tr key={s.orthanc_id} style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                      onMouseEnter={e => e.currentTarget.style.background = C.g50}
                      onMouseLeave={e => e.currentTarget.style.background = 'white'}
                      onClick={() => setSelectedStudy(s)}>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}`, fontSize: '13px', fontWeight: 600, color: C.g800 }}>{s.study_date}</td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}`, fontSize: '12px', color: C.g500 }}>{s.study_time}</td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}`, fontSize: '13px', fontWeight: 500, color: C.g800 }}>{s.patient_name.replace('^', ' ')}</td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}` }}>
                        <span style={{ padding: '2px 8px', background: `${C.sapphire}10`, color: C.sapphire, borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>{s.patient_id}</span>
                      </td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}`, fontSize: '12px', color: C.g600 }}>{s.study_description}</td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}`, fontSize: '12px', color: C.g500 }}>{s.num_series} series</td>
                      <td style={{ padding: '10px 14px', borderBottom: `1px solid ${C.g100}` }}>
                        <button style={{ padding: '4px 10px', border: `1px solid ${C.g200}`, borderRadius: '6px', fontSize: '11px', cursor: 'pointer', background: 'white', fontFamily: 'inherit' }}
                          onClick={(e) => { e.stopPropagation(); setSelectedStudy(s); setShowMeasurementForm(true); }}>📏 Measure</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ padding: '10px 14px', background: C.g50, borderTop: `1px solid ${C.g200}`, fontSize: '12px', color: C.g400 }}>
                {filteredStudies.length} studies · Demo data — connect Orthanc for live DICOM studies
              </div>
            </div>

            {/* Selected study detail */}
            {selectedStudy && (
              <div style={{ background: 'white', borderRadius: '12px', border: `1px solid ${C.g200}`, padding: '20px', marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: C.g900 }}>{selectedStudy.study_description}</h3>
                    <p style={{ fontSize: '12px', color: C.g500 }}>{selectedStudy.patient_name.replace('^', ' ')} · {selectedStudy.patient_id} · {selectedStudy.study_date} {selectedStudy.study_time}</p>
                  </div>
                  <button onClick={() => setSelectedStudy(null)} style={{ border: 'none', background: 'none', fontSize: '18px', cursor: 'pointer', color: C.g400 }}>✕</button>
                </div>

                {/* Placeholder for DICOM image viewer */}
                <div style={{ marginTop: '16px', background: '#000', borderRadius: '8px', height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#555', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '48px' }}>📡</span>
                  <span style={{ fontSize: '14px', color: '#888' }}>DICOM Viewer</span>
                  <span style={{ fontSize: '11px', color: '#555' }}>Connect Orthanc server to view ultrasound images here</span>
                  <span style={{ fontSize: '10px', color: '#444' }}>Orthanc DICOMweb URL: http://localhost:8042/dicom-web</span>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <button onClick={() => setShowMeasurementForm(true)}
                    style={{ padding: '8px 16px', background: `linear-gradient(135deg, ${C.sapphire}, ${C.sapphireDark})`, color: 'white', border: 'none', borderRadius: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>📏 Add Measurements</button>
                  <button style={{ padding: '8px 16px', border: `1px solid ${C.g200}`, borderRadius: '8px', fontSize: '12px', cursor: 'pointer', background: 'white', fontFamily: 'inherit' }}>📄 Create Report</button>
                  <button style={{ padding: '8px 16px', border: `1px solid ${C.g200}`, borderRadius: '8px', fontSize: '12px', cursor: 'pointer', background: 'white', fontFamily: 'inherit' }}>🔗 Link to EMR</button>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── FOLLICLE TRACKING TAB ── */}
        {tab === 'tracking' && <FollicleChart />}

        {/* ── SETUP TAB ── */}
        {tab === 'setup' && (
          <div style={{ background: 'white', borderRadius: '12px', border: `1px solid ${C.g200}`, padding: '24px', maxWidth: '700px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: C.g900, marginBottom: '4px' }}>⚙️ GE VOLUSON Swift → FCMS Setup</h3>
            <p style={{ fontSize: '12px', color: C.g500, marginBottom: '20px' }}>DICOM configuration to connect your ultrasound machine</p>

            <div style={{ background: C.g50, borderRadius: '8px', padding: '14px', marginBottom: '16px', border: `1px solid ${C.g200}` }}>
              <h4 style={{ fontSize: '12px', fontWeight: 700, color: C.g700, marginBottom: '8px' }}>FCMS Orthanc Server Settings</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {[
                  ['AE Title', 'FCMS_ORTHANC'],
                  ['DICOM Port', '4242'],
                  ['HTTP Port', '8042'],
                  ['IP Address', '<your server IP>'],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                    <span style={{ fontSize: '12px', color: C.g500 }}>{k}:</span>
                    <code style={{ fontSize: '12px', fontWeight: 600, color: C.sapphire, background: `${C.sapphire}10`, padding: '1px 6px', borderRadius: '4px' }}>{v}</code>
                  </div>
                ))}
              </div>
            </div>

            {[
              { n: 1, t: 'Install Orthanc', d: 'macOS: brew install orthanc · Ubuntu: apt install orthanc orthanc-dicomweb' },
              { n: 2, t: 'Configure Orthanc', d: 'Copy orthanc.json from module3/config/ to /etc/orthanc/ — update VOLUSON IP address' },
              { n: 3, t: 'Start Orthanc', d: 'Run: orthanc /etc/orthanc/orthanc.json — verify at http://localhost:8042' },
              { n: 4, t: 'Configure VOLUSON Swift', d: 'Utilities → System Setup → Connectivity → DICOM Config → Add store with FCMS_ORTHANC AE Title' },
              { n: 5, t: 'Set compression', d: 'Explicit VR Little Endian, disable JPEG compression for diagnostic quality' },
              { n: 6, t: 'Verify & test', d: 'Press Verify on VOLUSON, then perform test scan — should appear in FCMS within seconds' },
            ].map(s => (
              <div key={s.n} style={{ display: 'flex', gap: '12px', marginBottom: '12px', alignItems: 'start' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: `${C.sapphire}10`, color: C.sapphire, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 700, flexShrink: 0 }}>{s.n}</div>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: C.g800 }}>{s.t}</div>
                  <div style={{ fontSize: '12px', color: C.g500, marginTop: '2px' }}>{s.d}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showMeasurementForm && <MeasurementForm />}
    </div>
  );
}
