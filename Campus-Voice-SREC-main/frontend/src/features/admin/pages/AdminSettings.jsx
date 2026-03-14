import React, { useState, useEffect, useCallback } from 'react';
import adminService from '../../../services/admin.service';
import { Skeleton } from '../../../components/UI';
import {
  Settings, ToggleRight, Save, ArrowRightLeft,
  ShieldAlert, Trash2, Clock, ChevronDown, ChevronUp,
  AlertTriangle, Check, X, UserCog, UserPlus,
} from 'lucide-react';

// ─── Toggle Switch ───────────────────────────────────────────────────────────
function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
        checked ? 'bg-srec-primary' : 'bg-gray-300'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
        checked ? 'translate-x-6' : 'translate-x-1'
      }`} />
    </button>
  );
}

// ─── Confirmation Modal ──────────────────────────────────────────────────────
function ConfirmModal({ open, title, message, confirmText, dangerPhrase, onConfirm, onCancel }) {
  const [typed, setTyped] = useState('');
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const canConfirm = dangerPhrase ? typed === dangerPhrase : true;

  const handleConfirm = async () => {
    setLoading(true);
    try { await onConfirm(); } finally { setLoading(false); setTyped(''); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 animate-fadeIn">
        <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-4">{message}</p>
        {dangerPhrase && (
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-1.5">
              Type <span className="font-mono font-bold text-red-600">{dangerPhrase}</span> to confirm:
            </p>
            <input
              type="text"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-red-300 focus:border-red-400 outline-none"
              placeholder="Type confirmation phrase..."
            />
          </div>
        )}
        <div className="flex gap-3 justify-end">
          <button onClick={() => { onCancel(); setTyped(''); }} className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm || loading}
            className={`px-4 py-2 text-sm font-semibold text-white rounded-lg transition-all ${
              canConfirm && !loading
                ? 'bg-red-600 hover:bg-red-700 shadow-sm'
                : 'bg-gray-300 cursor-not-allowed'
            }`}
          >
            {loading ? 'Processing...' : (confirmText || 'Confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Section Card ────────────────────────────────────────────────────────────
function SectionCard({ title, icon: Icon, children, danger = false, collapsible = false, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`bg-white/80 backdrop-blur-sm rounded-2xl border shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] ${
      danger ? 'border-red-200' : 'border-white/60'
    }`}>
      <div
        className={`flex items-center gap-3 px-5 py-4 ${collapsible ? 'cursor-pointer' : ''} ${
          danger ? 'border-l-4 border-l-red-500 rounded-l-2xl' : ''
        }`}
        onClick={collapsible ? () => setOpen(o => !o) : undefined}
      >
        {Icon && <Icon size={18} className={danger ? 'text-red-500' : 'text-srec-primary'} />}
        <h3 className={`text-sm font-bold flex-1 ${danger ? 'text-red-700' : 'text-gray-900'}`}>{title}</h3>
        {collapsible && (open ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />)}
      </div>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

// ═══════════════════════ MAIN COMPONENT ═════════════════════════════════════
export default function AdminSettings() {
  const [settings, setSettings] = useState([]);
  const [authorities, setAuthorities] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null); // key being saved
  const [toast, setToast] = useState(null);
  const [localValues, setLocalValues] = useState({});

  // Transfer state
  const [transferSrc, setTransferSrc] = useState('');
  const [transferTgt, setTransferTgt] = useState('');
  const [adminTransferTarget, setAdminTransferTarget] = useState('');

  // Modals
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showSoftResetModal, setShowSoftResetModal] = useState(false);

  // Authority management state
  const [authMode, setAuthMode] = useState('edit'); // 'create' | 'edit'
  const [selectedAuthId, setSelectedAuthId] = useState('');
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [authSaving, setAuthSaving] = useState(false);

  // Populate edit form when authority is selected
  const handleSelectAuth = (id) => {
    setSelectedAuthId(id);
    const a = authorities.find(x => String(x.id) === id);
    if (a) setAuthForm({ name: a.name || '', email: a.email || '', password: '' });
    else setAuthForm({ name: '', email: '', password: '' });
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthSaving(true);
    try {
      if (authMode === 'create') {
        await adminService.createAuthority({
          name: authForm.name,
          email: authForm.email,
          password: authForm.password,
          authority_type: authForm.authority_type || 'Warden',
          authority_level: Number(authForm.authority_level) || 5,
          department_id: authForm.department_id ? Number(authForm.department_id) : null,
          designation: authForm.designation || null,
        });
        showToast('Authority created successfully');
      } else {
        if (!selectedAuthId) { showToast('Select an authority to edit', 'error'); return; }
        await adminService.updateAuthority(Number(selectedAuthId), {
          name: authForm.name || undefined,
          email: authForm.email || undefined,
          password: authForm.password || undefined,
        });
        showToast('Authority updated successfully');
      }
      setAuthForm({ name: '', email: '', password: '' });
      setSelectedAuthId('');
      loadAuthorities();
    } catch (err) {
      showToast(err?.detail || err?.error || 'Operation failed', 'error');
    } finally {
      setAuthSaving(false);
    }
  };

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // ── Load data ──────────────────────────────────────────────────────────────
  const loadSettings = useCallback(async () => {
    try {
      const data = await adminService.getSystemSettings();
      const items = data.settings || [];
      setSettings(items);
      const vals = {};
      items.forEach(s => { vals[s.key] = s.value; });
      setLocalValues(vals);
    } catch { showToast('Failed to load settings', 'error'); }
  }, []);

  const loadAuthorities = useCallback(async () => {
    try {
      const data = await adminService.getAllAuthorities(0, 200);
      setAuthorities(data.authorities || []);
    } catch {}
  }, []);

  const loadAuditLogs = useCallback(async () => {
    try {
      const data = await adminService.getAuditLogs({ limit: 20 });
      setAuditLogs(data.logs || []);
      setAuditTotal(data.total || 0);
    } catch {}
  }, []);

  useEffect(() => {
    Promise.all([loadSettings(), loadAuthorities(), loadAuditLogs()]).finally(() => setLoading(false));
  }, [loadSettings, loadAuthorities, loadAuditLogs]);

  // ── Setting update ─────────────────────────────────────────────────────────
  const updateSetting = async (key, value) => {
    setSaving(key);
    try {
      await adminService.updateSystemSetting(key, String(value));
      setLocalValues(v => ({ ...v, [key]: String(value) }));
      showToast(`${key} updated`);
    } catch (err) {
      showToast(err?.error || 'Update failed', 'error');
    } finally {
      setSaving(null);
    }
  };

  const toggleBool = (key) => {
    const newVal = localValues[key] === 'true' ? 'false' : 'true';
    setLocalValues(v => ({ ...v, [key]: newVal }));
    updateSetting(key, newVal);
  };

  // ── Group settings ─────────────────────────────────────────────────────────
  const grouped = {};
  settings.forEach(s => {
    const group = s.group || 'general';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(s);
  });

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleAuthorityTransfer = async () => {
    try {
      const res = await adminService.transferAuthority(Number(transferSrc), Number(transferTgt));
      showToast(`Transferred ${res.complaints_transferred} complaints from ${res.from} to ${res.to}`);
      setShowTransferModal(false);
      loadAuditLogs();
    } catch (err) {
      showToast(err?.detail || err?.error || 'Transfer failed', 'error');
    }
  };

  const handleAdminTransfer = async () => {
    try {
      const res = await adminService.transferAdmin(Number(adminTransferTarget), 'TRANSFER ADMIN ROLE');
      showToast(res.message || 'Admin role transferred');
      setShowAdminModal(false);
    } catch (err) {
      showToast(err?.detail || err?.error || 'Transfer failed', 'error');
    }
  };

  const handleDatabaseReset = async () => {
    try {
      await adminService.resetDatabase('RESET CAMPUS VOICE DATABASE');
      showToast('Database has been reset');
      setShowResetModal(false);
    } catch (err) {
      showToast(err?.detail || err?.error || 'Reset failed', 'error');
    }
  };

  const handleSoftReset = async () => {
    try {
      const res = await adminService.softReset('CLEAR ALL COMPLAINTS');
      showToast(res.message || 'Complaints cleared');
      setShowSoftResetModal(false);
      loadAuditLogs();
    } catch (err) {
      showToast(err?.detail || err?.error || 'Reset failed', 'error');
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
      </div>
    );
  }

  const featureSettings = grouped.features || [];
  const rateLimitSettings = grouped.rate_limits || [];
  const petitionSettings = grouped.petitions || [];
  const dataSettings = grouped.data || [];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold shadow-lg animate-fadeIn ${
          toast.type === 'error' ? 'bg-red-500 text-white' : 'bg-emerald-500 text-white'
        }`}>
          {toast.type === 'error' ? <X size={14} /> : <Check size={14} />}
          {toast.msg}
        </div>
      )}

      {/* Page header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-srec-primarySoft flex items-center justify-center">
          <Settings size={20} className="text-srec-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 font-heading">System Settings</h1>
          <p className="text-xs text-gray-500">Manage features, limits, transfers, and exports</p>
        </div>
      </div>

      {/* ── Feature Toggles ─────────────────────────────────────────────────── */}
      {featureSettings.length > 0 && (
        <SectionCard title="Feature Toggles" icon={ToggleRight}>
          <div className="space-y-3">
            {featureSettings.map(s => (
              <div key={s.key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {s.key.replace(/^enable_/, '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                  <p className="text-xs text-gray-500">{s.description}</p>
                </div>
                <Toggle
                  checked={localValues[s.key] === 'true'}
                  onChange={() => toggleBool(s.key)}
                  disabled={saving === s.key}
                />
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Rate Limits ─────────────────────────────────────────────────────── */}
      {rateLimitSettings.length > 0 && (
        <SectionCard title="Rate Limits" icon={Clock}>
          <div className="space-y-4">
            {rateLimitSettings.map(s => (
              <div key={s.key} className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {s.key.replace(/^rate_limit_/, '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                  <p className="text-xs text-gray-500">{s.description} (min: {s.min}, max: {s.max})</p>
                </div>
                <input
                  type="number"
                  min={s.min} max={s.max}
                  value={localValues[s.key] || ''}
                  onChange={(e) => setLocalValues(v => ({ ...v, [s.key]: e.target.value }))}
                  className="w-20 border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm text-center focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                />
                <button
                  onClick={() => updateSetting(s.key, localValues[s.key])}
                  disabled={saving === s.key}
                  className="flex items-center gap-1 px-3 py-1.5 bg-srec-primary text-white text-xs font-semibold rounded-lg hover:bg-srec-primaryHover transition-colors disabled:opacity-50"
                >
                  <Save size={12} /> {saving === s.key ? '...' : 'Save'}
                </button>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Petition Settings ───────────────────────────────────────────────── */}
      {petitionSettings.length > 0 && (
        <SectionCard title="Petition Settings" icon={Settings}>
          <div className="space-y-4">
            {petitionSettings.map(s => (
              <div key={s.key} className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {s.key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                  <p className="text-xs text-gray-500">{s.description}</p>
                </div>
                <input
                  type="number"
                  min={s.min} max={s.max}
                  value={localValues[s.key] || ''}
                  onChange={(e) => setLocalValues(v => ({ ...v, [s.key]: e.target.value }))}
                  className="w-20 border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm text-center focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                />
                <button
                  onClick={() => updateSetting(s.key, localValues[s.key])}
                  disabled={saving === s.key}
                  className="flex items-center gap-1 px-3 py-1.5 bg-srec-primary text-white text-xs font-semibold rounded-lg hover:bg-srec-primaryHover transition-colors disabled:opacity-50"
                >
                  <Save size={12} /> {saving === s.key ? '...' : 'Save'}
                </button>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Data Management ─────────────────────────────────────────────────── */}
      {dataSettings.length > 0 && (
        <SectionCard title="Data Management" icon={Settings}>
          <div className="space-y-3">
            {dataSettings.map(s => (
              <div key={s.key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {s.key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                  <p className="text-xs text-gray-500">{s.description}</p>
                </div>
                {s.type === 'bool' ? (
                  <Toggle checked={localValues[s.key] === 'true'} onChange={() => toggleBool(s.key)} disabled={saving === s.key} />
                ) : (
                  <div className="flex items-center gap-2">
                    <input
                      type="number" min={s.min} max={s.max}
                      value={localValues[s.key] || ''}
                      onChange={(e) => setLocalValues(v => ({ ...v, [s.key]: e.target.value }))}
                      className="w-20 border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm text-center focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                    />
                    <button
                      onClick={() => updateSetting(s.key, localValues[s.key])}
                      disabled={saving === s.key}
                      className="flex items-center gap-1 px-3 py-1.5 bg-srec-primary text-white text-xs font-semibold rounded-lg hover:bg-srec-primaryHover transition-colors disabled:opacity-50"
                    >
                      <Save size={12} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Manage Authorities ──────────────────────────────────────────────── */}
      <SectionCard title="Manage Authorities" icon={UserCog}>
        {/* Mode toggle */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => { setAuthMode('edit'); setAuthForm({ name: '', email: '', password: '' }); setSelectedAuthId(''); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              authMode === 'edit' ? 'bg-srec-primary text-white border-srec-primary' : 'bg-white text-gray-600 border-gray-300 hover:border-srec-primary'
            }`}
          >
            <UserCog size={13} /> Edit Authority
          </button>
          <button
            onClick={() => { setAuthMode('create'); setAuthForm({ name: '', email: '', password: '', authority_type: 'Warden', authority_level: 5 }); setSelectedAuthId(''); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              authMode === 'create' ? 'bg-srec-primary text-white border-srec-primary' : 'bg-white text-gray-600 border-gray-300 hover:border-srec-primary'
            }`}
          >
            <UserPlus size={13} /> Create New
          </button>
        </div>

        <form onSubmit={handleAuthSubmit} className="space-y-3">
          {/* Select authority (edit mode only) */}
          {authMode === 'edit' && (
            <div>
              <label className="text-xs font-medium text-gray-700 mb-1 block">Select Authority to Edit</label>
              <select
                value={selectedAuthId}
                onChange={(e) => handleSelectAuth(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
              >
                <option value="">Choose authority...</option>
                {authorities.map(a => (
                  <option key={a.id} value={a.id}>{a.name} — {a.authority_type} {a.email ? `(${a.email})` : ''}</option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-700 mb-1 block">Name</label>
              <input
                type="text"
                value={authForm.name}
                onChange={(e) => setAuthForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Full name"
                required={authMode === 'create'}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700 mb-1 block">Email (@srec.ac.in)</label>
              <input
                type="email"
                value={authForm.email}
                onChange={(e) => setAuthForm(f => ({ ...f, email: e.target.value }))}
                placeholder="name@srec.ac.in"
                required={authMode === 'create'}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700 mb-1 block">
                Password {authMode === 'edit' && <span className="font-normal text-gray-400">(leave blank to keep current)</span>}
              </label>
              <input
                type="password"
                value={authForm.password}
                onChange={(e) => setAuthForm(f => ({ ...f, password: e.target.value }))}
                placeholder={authMode === 'edit' ? 'New password (optional)' : 'Min 8 characters'}
                required={authMode === 'create'}
                minLength={authMode === 'create' ? 8 : 0}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
              />
            </div>
            {/* Extra fields for create mode */}
            {authMode === 'create' && (
              <>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Authority Type</label>
                  <select
                    value={authForm.authority_type || 'Warden'}
                    onChange={(e) => setAuthForm(f => ({ ...f, authority_type: e.target.value }))}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                  >
                    {['Warden', 'Deputy Warden', 'Senior Deputy Warden', 'HOD', 'Admin Officer', 'Disciplinary Committee', 'Admin'].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Authority Level (1–100)</label>
                  <input
                    type="number"
                    min={1} max={100}
                    value={authForm.authority_level || 5}
                    onChange={(e) => setAuthForm(f => ({ ...f, authority_level: e.target.value }))}
                    required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Designation <span className="font-normal text-gray-400">(optional)</span></label>
                  <input
                    type="text"
                    value={authForm.designation || ''}
                    onChange={(e) => setAuthForm(f => ({ ...f, designation: e.target.value }))}
                    placeholder="e.g. Chief Warden"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Department ID <span className="font-normal text-gray-400">(optional, for HOD)</span></label>
                  <input
                    type="number"
                    min={1}
                    value={authForm.department_id || ''}
                    onChange={(e) => setAuthForm(f => ({ ...f, department_id: e.target.value }))}
                    placeholder="e.g. 1 for CSE"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                  />
                </div>
              </>
            )}
          </div>

          <button
            type="submit"
            disabled={authSaving || (authMode === 'edit' && !selectedAuthId)}
            className="flex items-center gap-2 px-4 py-2 bg-srec-primary text-white text-sm font-semibold rounded-xl hover:bg-srec-primaryHover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save size={14} />
            {authSaving ? 'Saving...' : (authMode === 'create' ? 'Create Authority' : 'Save Changes')}
          </button>
        </form>
      </SectionCard>

      {/* ── Authority Transfer ──────────────────────────────────────────────── */}
      <SectionCard title="Authority Transfer" icon={ArrowRightLeft}>
        <p className="text-xs text-gray-500 mb-3">
          Reassign all complaints from one authority to another. The source authority is not deleted — all historical data is preserved.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[180px]">
            <label className="text-xs font-medium text-gray-700 mb-1 block">From</label>
            <select
              value={transferSrc} onChange={(e) => setTransferSrc(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
            >
              <option value="">Select source...</option>
              {authorities.map(a => <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="text-xs font-medium text-gray-700 mb-1 block">To</label>
            <select
              value={transferTgt} onChange={(e) => setTransferTgt(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
            >
              <option value="">Select target...</option>
              {authorities.filter(a => String(a.id) !== transferSrc).map(a => (
                <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => transferSrc && transferTgt && setShowTransferModal(true)}
            disabled={!transferSrc || !transferTgt}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 text-white text-sm font-semibold rounded-lg hover:bg-amber-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ArrowRightLeft size={14} /> Transfer
          </button>
        </div>
      </SectionCard>

      {/* ── Admin Ownership Transfer ────────────────────────────────────────── */}
      <SectionCard title="Admin Ownership Transfer" icon={ShieldAlert} danger>
        <p className="text-xs text-red-600 mb-3">
          Transfer the Admin role to another authority. You will be demoted to their current role. This action cannot be undone by you.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-medium text-red-700 mb-1 block">New Admin</label>
            <select
              value={adminTransferTarget} onChange={(e) => setAdminTransferTarget(e.target.value)}
              className="w-full border border-red-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-red-300 focus:border-red-400 outline-none"
            >
              <option value="">Select authority...</option>
              {authorities.filter(a => a.is_active && a.authority_type !== 'Admin').map(a => (
                <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => adminTransferTarget && setShowAdminModal(true)}
            disabled={!adminTransferTarget}
            className="flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-lg hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ShieldAlert size={14} /> Transfer Admin Role
          </button>
        </div>
      </SectionCard>

      {/* ── Audit Log ───────────────────────────────────────────────────────── */}
      <SectionCard title={`Audit Log (${auditTotal})`} icon={Clock} collapsible defaultOpen={false}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-3 font-semibold text-gray-600">Time</th>
                <th className="text-left py-2 pr-3 font-semibold text-gray-600">Admin</th>
                <th className="text-left py-2 pr-3 font-semibold text-gray-600">Action</th>
                <th className="text-left py-2 pr-3 font-semibold text-gray-600">Target</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.length === 0 ? (
                <tr><td colSpan={4} className="py-6 text-center text-gray-400">No audit logs yet</td></tr>
              ) : auditLogs.map(log => (
                <tr key={log.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                  <td className="py-2 pr-3 text-gray-500 whitespace-nowrap">
                    {log.action_at ? new Date(log.action_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                  </td>
                  <td className="py-2 pr-3 text-gray-800 font-medium">{log.admin_name}</td>
                  <td className="py-2 pr-3">
                    <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-[10px] font-semibold">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-gray-500">{log.target_type} #{log.target_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {auditTotal > 20 && (
          <p className="text-xs text-gray-400 mt-2 text-center">Showing latest 20 of {auditTotal} entries</p>
        )}
      </SectionCard>

      {/* ── Danger Zone ──────────────────────────────────────────────────────── */}
      <SectionCard title="Danger Zone" icon={Trash2} danger>
        <div className="space-y-4">
          {/* Soft Reset */}
          <div className="rounded-xl border-2 border-dashed border-amber-200 bg-amber-50/50 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-amber-800">Clear Complaints & Petitions</h4>
                <p className="text-xs text-amber-700 mt-1">
                  Permanently deletes all complaints, petitions, votes, and notifications. Student and authority accounts are preserved.
                  <strong className="block mt-1">This action is irreversible.</strong>
                </p>
                <button
                  onClick={() => setShowSoftResetModal(true)}
                  className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 transition-colors"
                >
                  <Trash2 size={14} /> Clear All Complaints
                </button>
              </div>
            </div>
          </div>

          {/* Full Database Reset */}
          <div className="rounded-xl border-2 border-dashed border-red-200 bg-red-50/50 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-red-800">Reset Entire Database</h4>
                <p className="text-xs text-red-600 mt-1">
                  Permanently deletes ALL data — complaints, students, authorities, votes, petitions, notifications — and re-seeds with default departments and categories only.
                  <strong className="block mt-1">This action is irreversible.</strong>
                </p>
                <button
                  onClick={() => setShowResetModal(true)}
                  className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Trash2 size={14} /> Reset Database
                </button>
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ── Modals ──────────────────────────────────────────────────────────── */}
      <ConfirmModal
        open={showTransferModal}
        title="Confirm Authority Transfer"
        message={`All complaints assigned to the source authority will be reassigned to the target authority. This preserves all historical data.`}
        confirmText="Transfer Complaints"
        onConfirm={handleAuthorityTransfer}
        onCancel={() => setShowTransferModal(false)}
      />
      <ConfirmModal
        open={showAdminModal}
        title="Transfer Admin Ownership"
        message="You will lose Admin privileges and be demoted to the target's current role. The selected authority will become the new Admin."
        confirmText="Transfer Admin Role"
        dangerPhrase="TRANSFER ADMIN ROLE"
        onConfirm={handleAdminTransfer}
        onCancel={() => setShowAdminModal(false)}
      />
      <ConfirmModal
        open={showSoftResetModal}
        title="Clear All Complaints & Petitions"
        message="All complaints, petitions, votes, and notifications will be permanently deleted. Student and authority accounts will be preserved. This cannot be undone."
        confirmText="Clear All Complaints"
        dangerPhrase="CLEAR ALL COMPLAINTS"
        onConfirm={handleSoftReset}
        onCancel={() => setShowSoftResetModal(false)}
      />
      <ConfirmModal
        open={showResetModal}
        title="Reset Entire Database"
        message="ALL data will be permanently deleted. The database will be re-seeded with default departments and categories only. All students, authorities, complaints, and votes will be lost."
        confirmText="Reset Database"
        dangerPhrase="RESET CAMPUS VOICE DATABASE"
        onConfirm={handleDatabaseReset}
        onCancel={() => setShowResetModal(false)}
      />
    </div>
  );
}
