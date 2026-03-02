/**
 * FCMS Module 2 - Lab Management Dashboard
 * Main dashboard showing all three sub-labs
 */

import React, { useState, useEffect } from 'react';

const API_BASE = '/api/v1/lab';

// ── Status badge component ──────────────────────────
function StatusBadge({ status }) {
  const styles = {
    pending:    { bg: '#FEF3C7', color: '#92400E', label: '⏳ Pending' },
    collected:  { bg: '#E0F5EF', color: '#006B54', label: '📥 Collected' },
    processing: { bg: '#E8EEFA', color: '#0F52BA', label: '🔬 Processing' },
    resulted:   { bg: '#E8EEFA', color: '#0F52BA', label: '📊 Resulted' },
    verified:   { bg: '#E0F5EF', color: '#006B54', label: '✓ Verified' },
    cancelled:  { bg: '#FCE4EE', color: '#A00040', label: '✕ Cancelled' },
  };
  const s = styles[status] || styles.pending;
  return (
    <span style={{
      background: s.bg, color: s.color,
      padding: '3px 10px', borderRadius: 99,
      fontSize: 11, fontWeight: 600,
    }}>{s.label}</span>
  );
}

// ── Result flag component ───────────────────────────
function ResultFlag({ flag }) {
  const colors = {
    N:  '#009473',
    L:  '#0F52BA',
    H:  '#E0115F',
    LL: '#A00040',
    HH: '#A00040',
    A:  '#E0115F',
  };
  const color = colors[flag] || '#6B7280';
  const pulse = flag === 'LL' || flag === 'HH';
  return (
    <span style={{
      color, fontWeight: 700, fontSize: 13,
      animation: pulse ? 'pulse 1.5s infinite' : 'none',
    }}>{flag || '—'}</span>
  );
}

// ── Stat Card ───────────────────────────────────────
function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 14, padding: 20,
      border: '1px solid #E5E7EB', boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 700, color: color || '#111827', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, fontWeight: 300, color: '#6B7280', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ── Tab component ───────────────────────────────────
function LabTabs({ active, onChange }) {
  const tabs = [
    { id: 'general',    label: '🔬 General Lab',    color: '#0F52BA' },
    { id: 'embryology', label: '🧬 Embryology Lab', color: '#50C878' },
    { id: 'andrology',  label: '🔬 Andrology Lab',  color: '#4A7FD4' },
  ];
  return (
    <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
            fontFamily: 'Cloud, sans-serif', fontSize: 13, fontWeight: active === t.id ? 700 : 400,
            background: active === t.id ? t.color : '#F3F4F6',
            color: active === t.id ? '#fff' : '#374151',
            transition: 'all 0.2s',
          }}
        >{t.label}</button>
      ))}
    </div>
  );
}

// ── General Lab Orders Table ────────────────────────
function GeneralLabView({ orders }) {
  return (
    <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
      <div style={{ padding: '18px 24px', borderBottom: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>Lab Orders</span>
        <button style={{ background: '#0F52BA', color: '#fff', padding: '8px 16px', borderRadius: 8, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
          + New Order
        </button>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {['Order No.', 'Patient', 'Tests', 'Priority', 'Status', 'Flag', 'Ordered'].map(h => (
              <th key={h} style={{ background: '#151667', color: '#fff', fontWeight: 600, padding: '11px 16px', textAlign: 'left', fontSize: 12 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((o, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
              <td style={{ padding: '12px 16px', fontWeight: 600 }}>{o.order_number}</td>
              <td style={{ padding: '12px 16px' }}>{o.patient_name}</td>
              <td style={{ padding: '12px 16px' }}>{o.tests}</td>
              <td style={{ padding: '12px 16px' }}>
                {o.priority === 'stat'
                  ? <span style={{ color: '#E0115F', fontWeight: 600 }}>STAT</span>
                  : o.priority}
              </td>
              <td style={{ padding: '12px 16px' }}><StatusBadge status={o.status} /></td>
              <td style={{ padding: '12px 16px' }}><ResultFlag flag={o.flag} /></td>
              <td style={{ padding: '12px 16px', color: '#6B7280', fontSize: 12 }}>{o.ordered_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Embryology View ─────────────────────────────────
function EmbryologyView({ embryos }) {
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        <StatCard label="Active Cycles" value="4" sub="2 IVF · 1 ICSI · 1 FET" color="#009473" />
        <StatCard label="Embryos in Culture" value="7" sub="Day 3: 4 · Day 5: 3" color="#50C878" />
        <StatCard label="Frozen Embryos" value="23" sub="Across 8 patients" color="#0F52BA" />
      </div>

      <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 15, fontWeight: 700 }}>Embryo Tracker</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={{ background: '#009473', color: '#fff', padding: '8px 16px', borderRadius: 8, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>+ New Cycle</button>
            <button style={{ background: 'transparent', color: '#0F52BA', padding: '8px 16px', borderRadius: 8, border: '1.5px solid #0F52BA', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Export</button>
          </div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {['Embryo ID', 'Patient', 'Day', 'Grade', 'Suitable', 'PGT-A', 'Disposition'].map(h => (
                <th key={h} style={{ background: '#151667', color: '#fff', fontWeight: 600, padding: '11px 16px', textAlign: 'left', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {embryos.map((e, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                <td style={{ padding: '12px 16px', fontWeight: 600 }}>{e.embryo_code}</td>
                <td style={{ padding: '12px 16px' }}>{e.patient_name}</td>
                <td style={{ padding: '12px 16px' }}>Day {e.current_day}</td>
                <td style={{ padding: '12px 16px', fontWeight: 600, color: '#009473' }}>{e.grade}</td>
                <td style={{ padding: '12px 16px' }}>{e.suitable ? '✓' : '—'}</td>
                <td style={{ padding: '12px 16px' }}>{e.pgta || '—'}</td>
                <td style={{ padding: '12px 16px' }}>
                  <StatusBadge status={e.disposition === 'frozen' ? 'verified' : e.disposition === 'fresh_transfer' ? 'resulted' : 'pending'} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Andrology View ──────────────────────────────────
function AndrologyView({ analyses }) {
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        <StatCard label="Today's SA" value="3" sub="2 completed · 1 pending" color="#4A7FD4" />
        <StatCard label="Frozen Samples" value="15" sub="Across 9 patients" color="#0F52BA" />
        <StatCard label="Preps Today" value="2" sub="1 IUI · 1 ICSI" color="#009473" />
      </div>

      <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 15, fontWeight: 700 }}>Semen Analysis — WHO 2021</span>
          <button style={{ background: '#0F52BA', color: '#fff', padding: '8px 16px', borderRadius: 8, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>+ New Analysis</button>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {['SA No.', 'Patient', 'Vol (mL)', 'Conc (M/mL)', 'Motility %', 'Morph %', 'WHO Ref', 'Diagnosis'].map(h => (
                <th key={h} style={{ background: '#151667', color: '#fff', fontWeight: 600, padding: '11px 16px', textAlign: 'left', fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {analyses.map((a, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                <td style={{ padding: '12px 16px', fontWeight: 600 }}>{a.analysis_number}</td>
                <td style={{ padding: '12px 16px' }}>{a.patient_name}</td>
                <td style={{ padding: '12px 16px' }}>{a.volume_ml}</td>
                <td style={{ padding: '12px 16px' }}>{a.concentration}</td>
                <td style={{ padding: '12px 16px' }}>{a.motility}%</td>
                <td style={{ padding: '12px 16px' }}>{a.morphology}%</td>
                <td style={{ padding: '12px 16px' }}>
                  {a.who_met
                    ? <span style={{ color: '#009473', fontWeight: 700 }}>✓ Met</span>
                    : <span style={{ color: '#E0115F', fontWeight: 700 }}>✕ Below</span>
                  }
                </td>
                <td style={{ padding: '12px 16px', fontSize: 12 }}>{a.diagnosis}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── MAIN DASHBOARD ──────────────────────────────────
export default function LabDashboard() {
  const [activeTab, setActiveTab] = useState('general');

  // Demo data — replace with API calls
  const sampleOrders = [
    { order_number: 'LO-2026-0042', patient_name: 'Nanthida W.', tests: 'AMH, FSH, LH, E2', priority: 'routine', status: 'verified', flag: 'N', ordered_at: '02 Mar 10:30' },
    { order_number: 'LO-2026-0041', patient_name: 'Supaporn K.', tests: 'CBC, Thyroid Panel', priority: 'stat', status: 'processing', flag: null, ordered_at: '02 Mar 09:15' },
    { order_number: 'LO-2026-0040', patient_name: 'Ratana P.', tests: 'Beta-hCG', priority: 'urgent', status: 'resulted', flag: 'H', ordered_at: '01 Mar 14:20' },
    { order_number: 'LO-2026-0039', patient_name: 'Kannika S.', tests: 'HIV, HBsAg, VDRL', priority: 'routine', status: 'verified', flag: 'N', ordered_at: '01 Mar 11:00' },
  ];

  const sampleEmbryos = [
    { embryo_code: 'EMB-2026-007', patient_name: 'Malee T.', current_day: 5, grade: '4AA', suitable: true, pgta: 'Euploid', disposition: 'frozen' },
    { embryo_code: 'EMB-2026-006', patient_name: 'Malee T.', current_day: 5, grade: '3BB', suitable: true, pgta: 'Pending', disposition: 'pending' },
    { embryo_code: 'EMB-2026-005', patient_name: 'Siriporn J.', current_day: 3, grade: '8-cell G1', suitable: true, pgta: null, disposition: 'pending' },
    { embryo_code: 'EMB-2026-004', patient_name: 'Siriporn J.', current_day: 3, grade: '6-cell G2', suitable: false, pgta: null, disposition: 'pending' },
  ];

  const sampleAnalyses = [
    { analysis_number: 'SA-2026-012', patient_name: 'Somchai R.', volume_ml: 3.2, concentration: 45, motility: 58, morphology: 6, who_met: true, diagnosis: 'Normozoospermia' },
    { analysis_number: 'SA-2026-011', patient_name: 'Prawit N.', volume_ml: 1.8, concentration: 12, motility: 35, morphology: 3, who_met: false, diagnosis: 'Oligoasthenoteratozoospermia' },
    { analysis_number: 'SA-2026-010', patient_name: 'Wichai K.', volume_ml: 2.5, concentration: 28, motility: 50, morphology: 5, who_met: true, diagnosis: 'Normozoospermia' },
  ];

  return (
    <div style={{ fontFamily: 'Cloud, sans-serif' }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <StatCard label="Orders Today" value="18" sub="12 resulted · 6 pending" color="#0F52BA" />
        <StatCard label="Critical Results" value="2" sub="⚠ Requires review" color="#E0115F" />
        <StatCard label="Pending Verification" value="5" sub="3 general · 2 andrology" color="#F59E0B" />
        <StatCard label="Avg TAT" value="3.2h" sub="Target: 4h ✓" color="#009473" />
      </div>

      {/* Tabs */}
      <LabTabs active={activeTab} onChange={setActiveTab} />

      {/* Tab Content */}
      {activeTab === 'general' && <GeneralLabView orders={sampleOrders} />}
      {activeTab === 'embryology' && <EmbryologyView embryos={sampleEmbryos} />}
      {activeTab === 'andrology' && <AndrologyView analyses={sampleAnalyses} />}
    </div>
  );
}
