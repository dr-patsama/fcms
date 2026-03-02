/**
 * FCMS Module 2 - Data Import Page
 * Upload Excel/CSV for inventory and patient history
 */

import React, { useState, useRef } from 'react';

const API_BASE = '/api/v1/lab';

export default function ImportPage() {
  const [importType, setImportType] = useState('inventory');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const endpoint = importType === 'inventory'
        ? `${API_BASE}/import/inventory`
        : `${API_BASE}/import/patients`;

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      });

      if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async (type) => {
    const res = await fetch(`${API_BASE}/import/template/${type}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = type === 'inventory'
      ? 'FCMS_Inventory_Import_Template.xlsx'
      : 'FCMS_Patient_Import_Template.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ fontFamily: 'Cloud, sans-serif', maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>📥 Data Import</h2>
      <p style={{ color: '#6B7280', fontSize: 14, marginBottom: 24 }}>
        Import inventory or patient history from Excel (.xlsx) or CSV (.csv) files.
      </p>

      {/* Import Type Selection */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[
          { id: 'inventory', label: '📦 Inventory / Supplies', desc: 'Pharmacy stock, lab supplies, medical equipment' },
          { id: 'patients',  label: '👤 Patient History',      desc: 'Client records, diagnoses, treatment notes' },
        ].map(t => (
          <div
            key={t.id}
            onClick={() => { setImportType(t.id); setResult(null); setFile(null); }}
            style={{
              flex: 1, padding: 20, borderRadius: 14, cursor: 'pointer',
              border: importType === t.id ? '2px solid #0F52BA' : '1px solid #E5E7EB',
              background: importType === t.id ? '#E8EEFA' : '#fff',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>{t.label}</div>
            <div style={{ fontSize: 12, color: '#6B7280' }}>{t.desc}</div>
          </div>
        ))}
      </div>

      {/* Download Template */}
      <div style={{
        background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: 10,
        padding: 16, marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>📋 Need a template?</div>
          <div style={{ fontSize: 12, color: '#6B7280' }}>Download our pre-formatted Excel template with all required columns</div>
        </div>
        <button
          onClick={() => downloadTemplate(importType === 'patients' ? 'patient' : 'inventory')}
          style={{
            background: 'transparent', color: '#0F52BA', border: '1.5px solid #0F52BA',
            padding: '8px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}
        >Download Template</button>
      </div>

      {/* File Upload */}
      <div
        onClick={() => fileRef.current?.click()}
        style={{
          border: '2px dashed #D1D5DB', borderRadius: 14, padding: 40,
          textAlign: 'center', cursor: 'pointer', marginBottom: 16,
          background: file ? '#E0F5EF' : '#fff',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xls,.csv,.tsv"
          style={{ display: 'none' }}
          onChange={(e) => { setFile(e.target.files[0]); setResult(null); }}
        />
        {file ? (
          <>
            <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#006B54' }}>{file.name}</div>
            <div style={{ fontSize: 12, color: '#6B7280' }}>{(file.size / 1024).toFixed(1)} KB · Click to change</div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 28, marginBottom: 8 }}>📁</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Click to select file</div>
            <div style={{ fontSize: 12, color: '#6B7280' }}>Accepts .xlsx, .xls, .csv, .tsv</div>
          </>
        )}
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || loading}
        style={{
          width: '100%', padding: 14, borderRadius: 10, border: 'none',
          fontSize: 15, fontWeight: 700, cursor: file && !loading ? 'pointer' : 'not-allowed',
          background: file && !loading ? '#0F52BA' : '#D1D5DB',
          color: '#fff', transition: 'all 0.2s', marginBottom: 24,
        }}
      >
        {loading ? '⏳ Importing...' : `Import ${importType === 'inventory' ? 'Inventory' : 'Patient History'}`}
      </button>

      {/* Error */}
      {error && (
        <div style={{
          background: '#FCE4EE', border: '1px solid #E0115F', borderRadius: 10,
          padding: 16, marginBottom: 16, color: '#A00040', fontSize: 13,
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div style={{
          background: '#fff', border: '1px solid #E5E7EB', borderRadius: 14,
          padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
        }}>
          <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 16, color: result.errors.length > 0 ? '#F59E0B' : '#009473' }}>
            {result.errors.length > 0 ? '⚠ Import completed with warnings' : '✅ Import successful'}
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
            <div style={{ textAlign: 'center', padding: 12, background: '#F9FAFB', borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{result.total_rows}</div>
              <div style={{ fontSize: 11, color: '#6B7280' }}>Total Rows</div>
            </div>
            <div style={{ textAlign: 'center', padding: 12, background: '#E0F5EF', borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#009473' }}>{result.imported}</div>
              <div style={{ fontSize: 11, color: '#006B54' }}>Imported</div>
            </div>
            <div style={{ textAlign: 'center', padding: 12, background: result.updated ? '#E8EEFA' : '#F9FAFB', borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#0F52BA' }}>{result.updated || 0}</div>
              <div style={{ fontSize: 11, color: '#6B7280' }}>Updated</div>
            </div>
            <div style={{ textAlign: 'center', padding: 12, background: result.skipped > 0 ? '#FEF3C7' : '#F9FAFB', borderRadius: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: result.skipped > 0 ? '#92400E' : '#6B7280' }}>{result.skipped}</div>
              <div style={{ fontSize: 11, color: '#6B7280' }}>Skipped</div>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, color: '#E0115F' }}>Errors ({result.errors.length})</div>
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {result.errors.map((err, i) => (
                  <div key={i} style={{ fontSize: 12, padding: '6px 0', borderBottom: '1px solid #F3F4F6', color: '#374151' }}>
                    <span style={{ fontWeight: 600 }}>Row {err.row}:</span> {err.error}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
