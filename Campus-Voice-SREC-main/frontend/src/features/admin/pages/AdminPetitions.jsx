import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../../utils/api';
import { Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import {
  Users, Trophy, CheckCircle2, MessageSquare, Search, X,
  Clock, Globe, Building2, Home, CheckCircle, XCircle, Filter,
} from 'lucide-react';

const MILESTONES = [50, 100, 250];

const STATUS_COLORS = {
  Open: 'bg-blue-50 text-blue-700 border-blue-100',
  Acknowledged: 'bg-amber-50 text-amber-700 border-amber-100',
  Resolved: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  Closed: 'bg-gray-100 text-gray-500 border-gray-200',
};

const SCOPE_ICONS = { General: Globe, Department: Building2, Hostel: Home };
const SCOPE_COLORS = {
  General: 'bg-sky-50 text-sky-700 border-sky-100',
  Department: 'bg-purple-50 text-purple-700 border-purple-100',
  Hostel: 'bg-orange-50 text-orange-700 border-orange-100',
};

const RESPOND_STATUSES = ['Acknowledged', 'Resolved', 'Closed'];

// ─────────────────────── RespondModal ───────────────────────────────────────
function RespondModal({ petition, isOpen, onClose, onResponded }) {
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState('Acknowledged');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setResponse(petition?.authority_response || '');
      setStatus(petition?.status === 'Open' ? 'Acknowledged' : petition?.status || 'Acknowledged');
      setError('');
    }
  }, [isOpen, petition]);

  if (!isOpen || !petition) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!response.trim()) { setError('Response cannot be empty'); return; }
    try {
      setLoading(true);
      const result = await api(`/petitions/${petition.id}/respond`, {
        method: 'POST',
        body: JSON.stringify({ response: response.trim(), status }),
      });
      onResponded(result);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-srec-textPrimary">Respond to Petition</h2>
            <p className="text-xs text-srec-textMuted mt-0.5 line-clamp-1">{petition.title}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100"><X size={16} /></button>
        </div>
        <div className="px-6 py-3 bg-srec-backgroundAlt border-b border-gray-100">
          <div className="flex items-center gap-3 text-xs text-srec-textSecondary">
            <span className="flex items-center gap-1"><Users size={12} />{petition.signature_count} signatures</span>
            <span className={`px-2 py-0.5 rounded-full font-bold border ${STATUS_COLORS[petition.status] || STATUS_COLORS.Open}`}>{petition.status}</span>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-srec-textSecondary mb-1.5 uppercase tracking-wide">Official Response</label>
            <textarea value={response} onChange={(e) => setResponse(e.target.value)} placeholder="Write an official response..." rows={5}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all" maxLength={2000} />
            <p className="text-[10px] text-srec-textMuted mt-1 text-right">{response.length}/2000</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-srec-textSecondary mb-1.5 uppercase tracking-wide">Update Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all">
              {RESPOND_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 border border-red-100">{error}</p>}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 border border-gray-200 text-srec-textSecondary rounded-xl text-sm font-semibold hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={loading} className="flex-1 py-2.5 bg-srec-primary text-white rounded-xl text-sm font-bold shadow-btn hover:bg-srec-primaryDark disabled:opacity-60">
              {loading ? 'Submitting...' : 'Submit Response'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── PetitionRow ────────────────────────────────────────
function PetitionRow({ petition, onRespond, onApprove, approving }) {
  const { signature_count, milestone_goal, milestones_reached = [], progress_pct, status } = petition;
  const isPending = !petition.is_published;
  const ScopeIcon = SCOPE_ICONS[petition.petition_scope] || Globe;

  return (
    <div className={`bg-white rounded-2xl border shadow-sm p-4 hover:shadow-md transition-all duration-200 ${isPending ? 'border-amber-200 bg-amber-50/20' : 'border-gray-100'}`}>
      {isPending && (
        <div className="mb-2 px-2 py-1 bg-amber-50 border border-amber-200 rounded-lg text-[10px] text-amber-800 flex items-center gap-1.5">
          <Clock size={10} className="text-amber-600" />
          <span className="font-semibold">Pending Approval</span>
          <span>— not visible to students yet</span>
        </div>
      )}

      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border ${STATUS_COLORS[status] || STATUS_COLORS.Open}`}>{status}</span>
            <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border inline-flex items-center gap-1 ${SCOPE_COLORS[petition.petition_scope] || SCOPE_COLORS.General}`}>
              <ScopeIcon size={8} />
              {petition.petition_scope || 'General'}
            </span>
            {petition.department_name && (
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-purple-50 text-purple-700 border border-purple-100">{petition.department_name}</span>
            )}
            {petition.days_remaining !== null && petition.days_remaining !== undefined && (
              <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border ${
                petition.days_remaining <= 0 ? 'bg-red-50 text-red-600 border-red-100'
                : petition.days_remaining <= 3 ? 'bg-orange-50 text-orange-600 border-orange-100'
                : 'bg-gray-50 text-gray-500 border-gray-100'
              }`}>
                {petition.days_remaining <= 0 ? 'Expired' : `${petition.days_remaining}d left`}
              </span>
            )}
          </div>
          <h3 className="text-sm font-bold text-srec-textPrimary leading-snug line-clamp-1">{petition.title}</h3>
          <p className="text-xs text-srec-textSecondary mt-0.5 line-clamp-2">{petition.description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
          {isPending ? (
            <button
              onClick={() => onApprove(petition)}
              disabled={approving === petition.id}
              className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 transition-all disabled:opacity-60"
            >
              <CheckCircle size={12} />
              {approving === petition.id ? '...' : 'Approve & Publish'}
            </button>
          ) : (
            <button
              onClick={() => onRespond(petition)}
              className="flex items-center gap-1 px-3 py-1.5 bg-srec-primary text-white rounded-lg text-xs font-bold shadow-btn hover:bg-srec-primaryDark transition-all"
            >
              <MessageSquare size={12} />
              Respond
            </button>
          )}
        </div>
      </div>

      {/* Milestone badges */}
      {milestones_reached.length > 0 && (
        <div className="flex gap-1 mb-2 flex-wrap">
          {milestones_reached.map((m) => (
            <span key={m} className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-100">🏆 {m}</span>
          ))}
        </div>
      )}

      <div className="mb-2">
        <div className="flex justify-between text-[10px] text-srec-textMuted mb-1">
          <span><strong className="text-srec-textPrimary">{signature_count}</strong> signed</span>
          <span>Goal: {petition.custom_goal || milestone_goal}</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
          <div className="h-1.5 rounded-full bg-gradient-to-r from-srec-primary to-emerald-500 transition-all duration-500"
            style={{ width: `${Math.min(progress_pct || 0, 100)}%` }} />
        </div>
      </div>

      {petition.authority_response && (
        <div className="mb-2 px-2 py-1.5 bg-blue-50 rounded-lg border border-blue-100 text-xs text-blue-800 line-clamp-1">
          <span className="font-semibold">Response: </span>{petition.authority_response}
        </div>
      )}

      <div className="flex items-center gap-3 text-[10px] text-srec-textMuted">
        <span>By {petition.creator_name || petition.created_by_roll_no}</span>
        <span>·</span>
        {petition.submitted_at && (
          <span>{new Date(petition.submitted_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════ AdminPetitions ═════════════════════════════════════
export default function AdminPetitions() {
  const { user } = useAuth();

  const [petitions, setPetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [respondTarget, setRespondTarget] = useState(null);
  const [approving, setApproving] = useState(null);

  const stats = {
    total: petitions.length,
    pending: petitions.filter((p) => !p.is_published).length,
    open: petitions.filter((p) => p.is_published && p.status === 'Open').length,
    acknowledged: petitions.filter((p) => p.status === 'Acknowledged').length,
    resolved: petitions.filter((p) => p.status === 'Resolved').length,
  };

  const fetchPetitions = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ skip: 0, limit: 200 });
      if (statusFilter) params.set('status', statusFilter);
      const data = await api(`/petitions/?${params}`);
      setPetitions(data?.petitions || []);
    } catch (err) {
      console.error('Failed to load petitions:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchPetitions(); }, [statusFilter]);

  const filtered = petitions.filter((p) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return p.title?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q) || p.creator_name?.toLowerCase().includes(q);
  });

  const handleResponded = (updatedPetition) => {
    setPetitions((prev) => prev.map((p) => p.id === updatedPetition.id ? { ...p, ...updatedPetition } : p));
  };

  const handleApprove = async (petition) => {
    setApproving(petition.id);
    try {
      const result = await api(`/petitions/${petition.id}/approve`, { method: 'POST' });
      setPetitions((prev) => prev.map((p) => p.id === petition.id ? { ...p, is_published: true, ...result } : p));
    } catch (err) {
      console.error('Failed to approve:', err);
      alert(err.message || 'Failed to approve petition');
    } finally {
      setApproving(null);
    }
  };

  const pendingList = filtered.filter((p) => !p.is_published);
  const publishedList = filtered.filter((p) => p.is_published);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-srec-textPrimary">Petitions Management</h1>
          <p className="text-sm text-srec-textMuted mt-0.5">Review, approve, and respond to student petitions</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: 'Total', value: stats.total, icon: Users, color: '#415d43' },
          { label: 'Pending', value: stats.pending, icon: Clock, color: '#D97706' },
          { label: 'Open', value: stats.open, icon: Filter, color: '#2563EB' },
          { label: 'Acknowledged', value: stats.acknowledged, icon: Trophy, color: '#7C3AED' },
          { label: 'Resolved', value: stats.resolved, icon: CheckCircle2, color: '#059669' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="h-1 w-full" style={{ background: color }} />
            <div className="p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
                <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: `${color}18`, color }}>
                  <Icon size={13} />
                </div>
              </div>
              <p className="text-xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
          <input
            type="text"
            placeholder="Search petitions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border border-gray-200 rounded-xl py-2.5 pl-9 pr-3 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all bg-white"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X size={13} />
            </button>
          )}
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {['', 'Open', 'Acknowledged', 'Resolved', 'Closed'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                statusFilter === s
                  ? 'bg-srec-primary text-white border-srec-primary shadow-sm'
                  : 'bg-white text-srec-textSecondary border-gray-200 hover:border-srec-primaryMuted hover:text-srec-primary'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Petition list */}
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
          <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-srec-primarySoft flex items-center justify-center">
            <Users size={24} className="text-srec-primary" />
          </div>
          <p className="text-srec-textPrimary text-base font-semibold">No petitions found</p>
          <p className="text-srec-textMuted text-sm mt-1">
            {search || statusFilter ? 'Try adjusting your filters' : 'No student petitions submitted yet'}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Pending approvals */}
          {pendingList.length > 0 && (
            <div>
              <h2 className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Clock size={12} /> Awaiting Approval ({pendingList.length})
              </h2>
              <div className="space-y-3">
                {pendingList.map((petition) => (
                  <PetitionRow
                    key={petition.id}
                    petition={petition}
                    onRespond={(p) => setRespondTarget(p)}
                    onApprove={handleApprove}
                    approving={approving}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Published petitions */}
          {publishedList.length > 0 && (
            <div>
              {pendingList.length > 0 && (
                <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <CheckCircle size={12} className="text-emerald-600" /> Published ({publishedList.length})
                </h2>
              )}
              <div className="space-y-3">
                {publishedList.map((petition) => (
                  <PetitionRow
                    key={petition.id}
                    petition={petition}
                    onRespond={(p) => setRespondTarget(p)}
                    onApprove={handleApprove}
                    approving={approving}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <RespondModal
        petition={respondTarget}
        isOpen={!!respondTarget}
        onClose={() => setRespondTarget(null)}
        onResponded={(updated) => { handleResponded(updated); setRespondTarget(null); }}
      />
    </div>
  );
}
