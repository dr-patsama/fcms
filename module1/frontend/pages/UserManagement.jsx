/**
 * FCMS — User Management Page
 * Admin panel for managing all staff accounts.
 * 
 * Features:
 *  - List all users with search, role filter, status filter
 *  - Create new user with role assignment
 *  - Edit user details, change role
 *  - Reset password, toggle active, unlock, reset MFA
 *  - View user activity log
 *  - Dashboard stats (total, active, by role)
 * 
 * Integrates with: /api/v1/users endpoints
 * Access: admin, it_admin roles only
 */

import React, { useState, useEffect, useCallback } from 'react';

// ── Role metadata ──────────────────────────────────────────
const ROLE_INFO = {
  admin:           { en: 'System Admin',     th: 'ผู้ดูแลระบบ',          color: '#E0115F', icon: '🔑' },
  physician:       { en: 'Physician',        th: 'แพทย์',               color: '#0F52BA', icon: '⚕️' },
  embryologist:    { en: 'Embryologist',      th: 'นักวิทยาศาสตร์ตัวอ่อน', color: '#009473', icon: '🔬' },
  lab_supervisor:  { en: 'Lab Supervisor',    th: 'หัวหน้าห้องปฏิบัติการ', color: '#059669', icon: '🧫' },
  lab_technician:  { en: 'Lab Technician',    th: 'เจ้าหน้าที่แล็บ',      color: '#6B7280', icon: '🧪' },
  nurse:           { en: 'Nurse',            th: 'พยาบาล',              color: '#50C878', icon: '💉' },
  sonographer:     { en: 'Sonographer',       th: 'นักอัลตราซาวด์',      color: '#7C3AED', icon: '📡' },
  pharmacist:      { en: 'Pharmacist',        th: 'เภสัชกร',            color: '#C5A044', icon: '💊' },
  pharmacy_staff:  { en: 'Pharmacy Staff',    th: 'เจ้าหน้าที่เภสัช',    color: '#D97706', icon: '🏪' },
  supply_manager:  { en: 'Supply Manager',    th: 'ผู้จัดการพัสดุ',      color: '#8B5CF6', icon: '📦' },
  receptionist:    { en: 'Receptionist',      th: 'พนักงานต้อนรับ',      color: '#F59E0B', icon: '🖥️' },
  billing_staff:   { en: 'Billing Staff',     th: 'เจ้าหน้าที่การเงิน',   color: '#EF4444', icon: '💰' },
  marketing_staff: { en: 'Marketing',         th: 'การตลาด',            color: '#EC4899', icon: '📣' },
  it_admin:        { en: 'IT Admin',          th: 'ผู้ดูแล IT',          color: '#6366F1', icon: '🖧' },
  patient:         { en: 'Patient',           th: 'ผู้ป่วย',             color: '#94A3B8', icon: '👤' },
};

const API_BASE = '/api/v1/users';

// ── API helper ─────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = sessionStorage.getItem('fcms_token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

// ── Badge component ────────────────────────────────────────
function RoleBadge({ role }) {
  const info = ROLE_INFO[role] || { en: role, color: '#6B7280', icon: '👤' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '3px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: 600,
      background: `${info.color}12`, color: info.color, border: `1px solid ${info.color}25`,
    }}>
      <span>{info.icon}</span> {info.en}
    </span>
  );
}

function StatusDot({ active }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      fontSize: '12px', fontWeight: 500, color: active ? '#059669' : '#DC2626',
    }}>
      <span style={{
        width: '7px', height: '7px', borderRadius: '50%',
        background: active ? '#10B981' : '#EF4444',
      }}></span>
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

// ══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════
export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [activityLogs, setActivityLogs] = useState([]);
  const [toast, setToast] = useState(null);

  // ── Fetch users ────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, per_page: 15 });
      if (search) params.set('search', search);
      if (roleFilter) params.set('role', roleFilter);
      if (statusFilter) params.set('is_active', statusFilter);
      const data = await apiFetch(`?${params}`);
      setUsers(data.users);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  const fetchStats = async () => {
    try {
      const data = await apiFetch('/stats/overview');
      setStats(data);
    } catch (err) { /* ignore */ }
  };

  useEffect(() => { fetchUsers(); fetchStats(); }, [fetchUsers]);

  // ── Toast ──────────────────────────────────────────────
  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  // ── Actions ────────────────────────────────────────────
  const handleToggleActive = async (user) => {
    try {
      const res = await apiFetch(`/${user.id}/toggle-active`, { method: 'POST' });
      showToast(res.message);
      fetchUsers();
      fetchStats();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const handleUnlock = async (user) => {
    try {
      const res = await apiFetch(`/${user.id}/unlock`, { method: 'POST' });
      showToast(res.message);
      fetchUsers();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const handleResetMfa = async (user) => {
    if (!confirm(`Reset MFA for ${user.email}? They will need to re-enroll.`)) return;
    try {
      const res = await apiFetch(`/${user.id}/reset-mfa`, { method: 'POST' });
      showToast(res.message);
      fetchUsers();
    } catch (err) { showToast(err.message, 'error'); }
  };

  const handleViewActivity = async (user) => {
    setSelectedUser(user);
    try {
      const data = await apiFetch(`/${user.id}/activity?per_page=50`);
      setActivityLogs(data.logs);
      setShowActivityModal(true);
    } catch (err) { showToast(err.message, 'error'); }
  };

  // ── Styles ─────────────────────────────────────────────
  const S = {
    page: { fontFamily: "'Plus Jakarta Sans','Noto Sans Thai',sans-serif", background: '#F8FAFC', minHeight: '100vh', padding: '24px 32px' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' },
    title: { fontSize: '24px', fontWeight: 700, color: '#0F172A', letterSpacing: '-0.02em' },
    subtitle: { fontSize: '13px', color: '#64748B', marginTop: '2px' },
    statGrid: { display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginBottom: '24px' },
    statCard: { background: 'white', borderRadius: '12px', padding: '16px 20px', border: '1px solid #E2E8F0' },
    statNum: { fontSize: '28px', fontWeight: 700, color: '#0F172A', lineHeight: 1 },
    statLabel: { fontSize: '12px', color: '#64748B', marginTop: '4px', fontWeight: 500 },
    toolbar: { display: 'flex', gap: '10px', marginBottom: '16px', alignItems: 'center', flexWrap: 'wrap' },
    searchInput: { flex: 1, minWidth: '240px', padding: '8px 14px 8px 36px', border: '1.5px solid #E2E8F0', borderRadius: '8px', fontSize: '13px', outline: 'none', background: 'white', fontFamily: 'inherit' },
    select: { padding: '8px 12px', border: '1.5px solid #E2E8F0', borderRadius: '8px', fontSize: '13px', background: 'white', fontFamily: 'inherit', color: '#334155', cursor: 'pointer' },
    btnPrimary: { padding: '8px 20px', background: 'linear-gradient(135deg, #C5A044, #8B7331)', color: 'white', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: '6px' },
    table: { width: '100%', borderCollapse: 'separate', borderSpacing: 0, background: 'white', borderRadius: '12px', overflow: 'hidden', border: '1px solid #E2E8F0' },
    th: { padding: '12px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC' },
    td: { padding: '12px 16px', fontSize: '13px', color: '#334155', borderBottom: '1px solid #F1F5F9' },
    actionBtn: { padding: '4px 10px', border: '1px solid #E2E8F0', borderRadius: '6px', fontSize: '11px', cursor: 'pointer', background: 'white', color: '#475569', fontWeight: 500, fontFamily: 'inherit', marginRight: '4px' },
    pagination: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: '1px solid #E2E8F0', background: '#FAFBFC', fontSize: '13px', color: '#64748B' },
    modal: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' },
    modalContent: { background: 'white', borderRadius: '16px', padding: '28px', width: '520px', maxHeight: '85vh', overflow: 'auto', boxShadow: '0 24px 48px rgba(0,0,0,0.15)' },
    modalTitle: { fontSize: '18px', fontWeight: 700, color: '#0F172A', marginBottom: '20px' },
    formGroup: { marginBottom: '14px' },
    formLabel: { display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' },
    formInput: { width: '100%', padding: '8px 12px', border: '1.5px solid #E2E8F0', borderRadius: '8px', fontSize: '13px', fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box' },
    formRow: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' },
  };

  // ══════════════════════════════════════════════════════
  // CREATE USER MODAL
  // ══════════════════════════════════════════════════════
  function CreateUserModal() {
    const [form, setForm] = useState({
      email: '', password: '', first_name_en: '', last_name_en: '',
      first_name_th: '', last_name_th: '', role: 'nurse', phone: '',
      license_number: '', department: '',
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
      setSaving(true);
      setError('');
      try {
        await apiFetch('', { method: 'POST', body: JSON.stringify(form) });
        showToast(`User ${form.email} created`);
        setShowCreateModal(false);
        fetchUsers();
        fetchStats();
      } catch (err) {
        setError(err.message);
      } finally {
        setSaving(false);
      }
    };

    return (
      <div style={S.modal} onClick={() => setShowCreateModal(false)}>
        <div style={S.modalContent} onClick={e => e.stopPropagation()}>
          <h3 style={S.modalTitle}>➕ Create New User</h3>
          {error && <div style={{ padding: '8px 12px', background: '#FEF2F2', color: '#DC2626', borderRadius: '8px', fontSize: '13px', marginBottom: '14px' }}>{error}</div>}

          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>First Name (EN) *</label>
              <input style={S.formInput} value={form.first_name_en} onChange={e => setForm({...form, first_name_en: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Last Name (EN) *</label>
              <input style={S.formInput} value={form.last_name_en} onChange={e => setForm({...form, last_name_en: e.target.value})} />
            </div>
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>ชื่อ (TH)</label>
              <input style={S.formInput} value={form.first_name_th} onChange={e => setForm({...form, first_name_th: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>นามสกุล (TH)</label>
              <input style={S.formInput} value={form.last_name_th} onChange={e => setForm({...form, last_name_th: e.target.value})} />
            </div>
          </div>
          <div style={S.formGroup}>
            <label style={S.formLabel}>Email *</label>
            <input style={S.formInput} type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
          </div>
          <div style={S.formGroup}>
            <label style={S.formLabel}>Password *</label>
            <input style={S.formInput} type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} placeholder="Min 8 chars, upper+lower+digit+special" />
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Role *</label>
              <select style={S.formInput} value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                {Object.entries(ROLE_INFO).filter(([k]) => k !== 'patient').map(([key, info]) => (
                  <option key={key} value={key}>{info.icon} {info.en} / {info.th}</option>
                ))}
              </select>
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Department</label>
              <input style={S.formInput} value={form.department} onChange={e => setForm({...form, department: e.target.value})} />
            </div>
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Phone</label>
              <input style={S.formInput} value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>License No.</label>
              <input style={S.formInput} value={form.license_number} onChange={e => setForm({...form, license_number: e.target.value})} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
            <button style={{ ...S.actionBtn, padding: '8px 20px' }} onClick={() => setShowCreateModal(false)}>Cancel</button>
            <button style={S.btnPrimary} onClick={handleSubmit} disabled={saving}>
              {saving ? '⏳ Creating...' : '✅ Create User'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════
  // EDIT USER MODAL
  // ══════════════════════════════════════════════════════
  function EditUserModal() {
    const [form, setForm] = useState({
      email: selectedUser?.email || '',
      first_name_en: selectedUser?.first_name_en || '',
      last_name_en: selectedUser?.last_name_en || '',
      first_name_th: selectedUser?.first_name_th || '',
      last_name_th: selectedUser?.last_name_th || '',
      role: selectedUser?.role || 'nurse',
      phone: selectedUser?.phone || '',
      license_number: selectedUser?.license_number || '',
      department: selectedUser?.department || '',
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
      setSaving(true);
      setError('');
      try {
        await apiFetch(`/${selectedUser.id}`, { method: 'PATCH', body: JSON.stringify(form) });
        showToast(`User ${form.email} updated`);
        setShowEditModal(false);
        fetchUsers();
      } catch (err) {
        setError(err.message);
      } finally {
        setSaving(false);
      }
    };

    return (
      <div style={S.modal} onClick={() => setShowEditModal(false)}>
        <div style={S.modalContent} onClick={e => e.stopPropagation()}>
          <h3 style={S.modalTitle}>✏️ Edit User — {selectedUser?.email}</h3>
          {error && <div style={{ padding: '8px 12px', background: '#FEF2F2', color: '#DC2626', borderRadius: '8px', fontSize: '13px', marginBottom: '14px' }}>{error}</div>}

          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>First Name (EN)</label>
              <input style={S.formInput} value={form.first_name_en} onChange={e => setForm({...form, first_name_en: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Last Name (EN)</label>
              <input style={S.formInput} value={form.last_name_en} onChange={e => setForm({...form, last_name_en: e.target.value})} />
            </div>
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>ชื่อ (TH)</label>
              <input style={S.formInput} value={form.first_name_th} onChange={e => setForm({...form, first_name_th: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>นามสกุล (TH)</label>
              <input style={S.formInput} value={form.last_name_th} onChange={e => setForm({...form, last_name_th: e.target.value})} />
            </div>
          </div>
          <div style={S.formGroup}>
            <label style={S.formLabel}>Email</label>
            <input style={S.formInput} type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Role</label>
              <select style={S.formInput} value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                {Object.entries(ROLE_INFO).filter(([k]) => k !== 'patient').map(([key, info]) => (
                  <option key={key} value={key}>{info.icon} {info.en}</option>
                ))}
              </select>
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Department</label>
              <input style={S.formInput} value={form.department} onChange={e => setForm({...form, department: e.target.value})} />
            </div>
          </div>
          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.formLabel}>Phone</label>
              <input style={S.formInput} value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
            </div>
            <div style={S.formGroup}>
              <label style={S.formLabel}>License No.</label>
              <input style={S.formInput} value={form.license_number} onChange={e => setForm({...form, license_number: e.target.value})} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
            <button style={{ ...S.actionBtn, padding: '8px 20px' }} onClick={() => setShowEditModal(false)}>Cancel</button>
            <button style={S.btnPrimary} onClick={handleSubmit} disabled={saving}>
              {saving ? '⏳ Saving...' : '💾 Save Changes'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════
  // RESET PASSWORD MODAL
  // ══════════════════════════════════════════════════════
  function PasswordModal() {
    const [newPassword, setNewPassword] = useState('');
    const [saving, setSaving] = useState(false);

    const handleReset = async () => {
      setSaving(true);
      try {
        await apiFetch(`/${selectedUser.id}/reset-password`, {
          method: 'POST',
          body: JSON.stringify({ new_password: newPassword }),
        });
        showToast(`Password reset for ${selectedUser.email}`);
        setShowPasswordModal(false);
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        setSaving(false);
      }
    };

    return (
      <div style={S.modal} onClick={() => setShowPasswordModal(false)}>
        <div style={{ ...S.modalContent, width: '400px' }} onClick={e => e.stopPropagation()}>
          <h3 style={S.modalTitle}>🔐 Reset Password</h3>
          <p style={{ fontSize: '13px', color: '#64748B', marginBottom: '16px' }}>
            Reset password for <strong>{selectedUser?.email}</strong>
          </p>
          <div style={S.formGroup}>
            <label style={S.formLabel}>New Password</label>
            <input style={S.formInput} type="password" value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="Min 8 chars" />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
            <button style={{ ...S.actionBtn, padding: '8px 20px' }} onClick={() => setShowPasswordModal(false)}>Cancel</button>
            <button style={{ ...S.btnPrimary, background: 'linear-gradient(135deg, #E0115F, #B80E4E)' }}
              onClick={handleReset} disabled={saving || newPassword.length < 8}>
              {saving ? '⏳...' : '🔑 Reset Password'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════
  // ACTIVITY LOG MODAL
  // ══════════════════════════════════════════════════════
  function ActivityModal() {
    return (
      <div style={S.modal} onClick={() => setShowActivityModal(false)}>
        <div style={{ ...S.modalContent, width: '640px' }} onClick={e => e.stopPropagation()}>
          <h3 style={S.modalTitle}>📋 Activity Log — {selectedUser?.email}</h3>
          {activityLogs.length === 0 ? (
            <p style={{ color: '#94A3B8', textAlign: 'center', padding: '32px 0' }}>No activity recorded</p>
          ) : (
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
              <table style={{ ...S.table, border: 'none' }}>
                <thead>
                  <tr>
                    <th style={S.th}>Time</th>
                    <th style={S.th}>Action</th>
                    <th style={S.th}>Module</th>
                    <th style={S.th}>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {activityLogs.map(log => (
                    <tr key={log.id}>
                      <td style={{ ...S.td, fontSize: '11px', whiteSpace: 'nowrap' }}>
                        {new Date(log.timestamp).toLocaleString('en-GB', { timeZone: 'Asia/Bangkok' })}
                      </td>
                      <td style={S.td}>
                        <span style={{
                          padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                          background: log.action === 'CREATE' ? '#ECFDF5' : log.action === 'DELETE' ? '#FEF2F2' : '#F0F9FF',
                          color: log.action === 'CREATE' ? '#059669' : log.action === 'DELETE' ? '#DC2626' : '#0369A1',
                        }}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ ...S.td, fontSize: '12px' }}>{log.module}</td>
                      <td style={{ ...S.td, fontSize: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{log.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ textAlign: 'right', marginTop: '16px' }}>
            <button style={{ ...S.actionBtn, padding: '8px 20px' }} onClick={() => setShowActivityModal(false)}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════
  return (
    <div style={S.page}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: '20px', right: '20px', zIndex: 9999,
          padding: '12px 20px', borderRadius: '10px', fontSize: '13px', fontWeight: 600,
          background: toast.type === 'error' ? '#FEF2F2' : '#ECFDF5',
          color: toast.type === 'error' ? '#DC2626' : '#059669',
          border: `1px solid ${toast.type === 'error' ? '#FECACA' : '#A7F3D0'}`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          animation: 'slideDown 0.3s ease',
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={S.header}>
        <div>
          <h1 style={S.title}>👥 User Management</h1>
          <p style={S.subtitle}>การจัดการผู้ใช้ · Manage staff accounts, roles, and permissions</p>
        </div>
        <button style={S.btnPrimary} onClick={() => setShowCreateModal(true)}>
          ➕ New User
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div style={S.statGrid}>
          <div style={S.statCard}>
            <div style={{ ...S.statNum, color: '#0F52BA' }}>{stats.total}</div>
            <div style={S.statLabel}>Total Users</div>
          </div>
          <div style={S.statCard}>
            <div style={{ ...S.statNum, color: '#059669' }}>{stats.active}</div>
            <div style={S.statLabel}>Active</div>
          </div>
          <div style={S.statCard}>
            <div style={{ ...S.statNum, color: '#DC2626' }}>{stats.inactive}</div>
            <div style={S.statLabel}>Inactive</div>
          </div>
          <div style={S.statCard}>
            <div style={{ ...S.statNum, color: '#F59E0B' }}>{stats.locked}</div>
            <div style={S.statLabel}>Locked</div>
          </div>
          <div style={S.statCard}>
            <div style={{ ...S.statNum, color: '#7C3AED' }}>{stats.mfa_percentage}%</div>
            <div style={S.statLabel}>MFA Enabled</div>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div style={S.toolbar}>
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8', fontSize: '14px' }}>🔍</span>
          <input style={S.searchInput} placeholder="Search by name, email, phone..."
            value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <select style={S.select} value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setPage(1); }}>
          <option value="">All Roles</option>
          {Object.entries(ROLE_INFO).map(([key, info]) => (
            <option key={key} value={key}>{info.icon} {info.en}</option>
          ))}
        </select>
        <select style={S.select} value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {/* Table */}
      <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid #E2E8F0' }}>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>User</th>
              <th style={S.th}>Email</th>
              <th style={S.th}>Role</th>
              <th style={S.th}>Department</th>
              <th style={S.th}>Status</th>
              <th style={S.th}>MFA</th>
              <th style={S.th}>Last Login</th>
              <th style={{ ...S.th, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="8" style={{ ...S.td, textAlign: 'center', padding: '40px', color: '#94A3B8' }}>Loading...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan="8" style={{ ...S.td, textAlign: 'center', padding: '40px', color: '#94A3B8' }}>No users found</td></tr>
            ) : users.map(user => (
              <tr key={user.id} style={{ transition: 'background 0.15s' }}
                onMouseEnter={e => e.currentTarget.style.background = '#F8FAFC'}
                onMouseLeave={e => e.currentTarget.style.background = 'white'}>
                <td style={S.td}>
                  <div style={{ fontWeight: 600, color: '#0F172A' }}>{user.full_name_en}</div>
                  {user.full_name_th && <div style={{ fontSize: '11px', color: '#94A3B8' }}>{user.full_name_th}</div>}
                </td>
                <td style={{ ...S.td, fontSize: '12px' }}>{user.email}</td>
                <td style={S.td}><RoleBadge role={user.role} /></td>
                <td style={{ ...S.td, fontSize: '12px' }}>{user.department || '—'}</td>
                <td style={S.td}><StatusDot active={user.is_active} /></td>
                <td style={S.td}>
                  <span style={{ fontSize: '12px', color: user.is_mfa_enabled ? '#059669' : '#94A3B8' }}>
                    {user.is_mfa_enabled ? '🔒 On' : '—'}
                  </span>
                </td>
                <td style={{ ...S.td, fontSize: '11px', color: '#94A3B8' }}>
                  {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString('en-GB') : 'Never'}
                </td>
                <td style={{ ...S.td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button style={S.actionBtn} onClick={() => { setSelectedUser(user); setShowEditModal(true); }}>✏️</button>
                  <button style={S.actionBtn} onClick={() => { setSelectedUser(user); setShowPasswordModal(true); }}>🔑</button>
                  <button style={S.actionBtn} onClick={() => handleToggleActive(user)}>
                    {user.is_active ? '⏸️' : '▶️'}
                  </button>
                  <button style={S.actionBtn} onClick={() => handleViewActivity(user)}>📋</button>
                  {user.locked_until && <button style={{ ...S.actionBtn, color: '#F59E0B' }} onClick={() => handleUnlock(user)}>🔓</button>}
                  {user.is_mfa_enabled && <button style={S.actionBtn} onClick={() => handleResetMfa(user)}>📱</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        <div style={S.pagination}>
          <span>Showing {users.length} of {total} users</span>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button style={S.actionBtn} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
            <span style={{ padding: '4px 12px', fontSize: '13px' }}>Page {page} / {totalPages}</span>
            <button style={S.actionBtn} disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showCreateModal && <CreateUserModal />}
      {showEditModal && selectedUser && <EditUserModal />}
      {showPasswordModal && selectedUser && <PasswordModal />}
      {showActivityModal && selectedUser && <ActivityModal />}
    </div>
  );
}
