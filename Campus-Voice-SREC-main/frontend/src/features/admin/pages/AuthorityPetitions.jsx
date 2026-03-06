import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../../utils/api';
import { Skeleton } from '../../../components/UI';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import { useAuth } from '../../../context/AuthContext';
import {
  Users, Trophy, CheckCircle2, MessageSquare, Search, X,
  Globe, Building2, Home, TrendingUp, CheckCircle,
} from 'lucide-react';

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

// ─────────────────────── RespondModal ───────────────────────────────────────
function RespondModal({ petition, isOpen, onClose, onResponded }) {
  const [response, setResponse] = useState('');
  const [newStatus, setNewStatus] = useState('Acknowledged');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setResponse(petition?.authority_response || '');
      setNewStatus(petition?.status === 'Open' ? 'Acknowledged' : petition?.status || 'Acknowledged');
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
        body: JSON.stringify({ response: response.trim(), status: newStatus }),
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
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-3 text-xs text-srec-textSecondary">
          <span className="flex items-center gap-1"><Users size={12} />{petition.signature_count} signatures</span>
          <span className={`px-2 py-0.5 rounded-full font-bold border ${STATUS_COLORS[petition.status] || STATUS_COLORS.Open}`}>{petition.status}</span>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-srec-textSecondary mb-1.5 uppercase tracking-wide">Official Response</label>
            <textarea value={response} onChange={(e) => setResponse(e.target.value)} placeholder="Write an official response..." rows={4}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all" maxLength={2000} />
            <p className="text-[10px] text-srec-textMuted mt-1 text-right">{response.length}/2000</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-srec-textSecondary mb-1.5 uppercase tracking-wide">Update Status</label>
            <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all">
              <option value="Acknowledged">Acknowledged — working on it</option>
              <option value="Closed">Closed — mark as done / dismiss</option>
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

// ─────────────────────── PetitionCard ───────────────────────────────────────
function PetitionCard({ petition, onRespond, isClosed }) {
  const { signature_count, milestone_goal, milestones_reached = [], progress_pct, status } = petition;
  const ScopeIcon = SCOPE_ICONS[petition.petition_scope] || Globe;
  const goal = petition.custom_goal || milestone_goal || 50;
  const goalReached = signature_count >= goal;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 mb-2">
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${STATUS_COLORS[status] || STATUS_COLORS.Open}`}>{status}</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border inline-flex items-center gap-1 ${SCOPE_COLORS[petition.petition_scope] || SCOPE_COLORS.General}`}>
                <ScopeIcon size={9} />{petition.petition_scope || 'General'}
              </span>
              {petition.department_name && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-100">{petition.department_name}</span>
              )}
              {!isClosed && petition.days_remaining !== null && petition.days_remaining !== undefined && (
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                  petition.days_remaining <= 0 ? 'bg-red-50 text-red-600 border-red-100'
                  : petition.days_remaining <= 3 ? 'bg-orange-50 text-orange-600 border-orange-100'
                  : 'bg-gray-50 text-gray-500 border-gray-100'
                }`}>
                  {petition.days_remaining <= 0 ? 'Expired' : `${petition.days_remaining}d left`}
                </span>
              )}
              {isClosed && goalReached && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Goal Reached</span>
              )}
            </div>
            <h3 className="text-sm font-bold text-srec-textPrimary leading-snug">{petition.title}</h3>
            <p className="text-xs text-srec-textSecondary mt-0.5 line-clamp-2">{petition.description}</p>
          </div>
          {!isClosed && (
            <button onClick={() => onRespond(petition)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-srec-primary text-white rounded-lg text-xs font-bold shadow-btn hover:bg-srec-primaryDark transition-all shrink-0">
              <MessageSquare size={12} />Respond
            </button>
          )}
        </div>

        <div className="mb-3">
          <div className="flex justify-between text-[10px] text-srec-textMuted mb-1">
            <span><strong className="text-srec-textPrimary text-xs">{signature_count}</strong> signed</span>
            <span>Goal: {goal}</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
            <div className={`h-1.5 rounded-full transition-all duration-500 ${goalReached ? 'bg-emerald-500' : 'bg-gradient-to-r from-srec-primary to-emerald-400'}`}
              style={{ width: `${Math.min(progress_pct || 0, 100)}%` }} />
          </div>
        </div>

        {petition.authority_response && (
          <div className="mb-3 px-3 py-2 bg-blue-50 rounded-xl border border-blue-100 text-xs text-blue-800">
            <span className="font-semibold">Response: </span>
            <span className="line-clamp-1">{petition.authority_response}</span>
          </div>
        )}

        <div className="flex items-center gap-2 text-[10px] text-srec-textMuted">
          <span>By {petition.creator_name || petition.created_by_roll_no}</span>
          {petition.submitted_at && (
            <><span>·</span><span>{new Date(petition.submitted_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span></>
          )}
          {milestones_reached.length > 0 && (
            <><span>·</span><span className="text-amber-600 font-semibold">🏆 {milestones_reached.join(', ')}</span></>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message, sub }) {
  return (
    <div className="text-center py-14 bg-white rounded-2xl border border-gray-100 shadow-sm">
      <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-srec-primarySoft flex items-center justify-center">
        <Users size={20} className="text-srec-primary" />
      </div>
      <p className="text-srec-textPrimary text-sm font-semibold">{message}</p>
      {sub && <p className="text-srec-textMuted text-xs mt-1">{sub}</p>}
    </div>
  );
}

// ═══════════════════════ AuthorityPetitions ══════════════════════════════════
export default function AuthorityPetitions() {
  const [petitions, setPetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('requests');
  const [search, setSearch] = useState('');
  const [respondTarget, setRespondTarget] = useState(null);

  const fetchPetitions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api('/petitions/?skip=0&limit=200');
      setPetitions(data?.petitions || []);
    } catch (err) {
      console.error('Failed to load petitions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPetitions(); }, []);

  const handleResponded = (updated) => {
    setPetitions((prev) => prev.map((p) => p.id === updated.id ? { ...p, ...updated } : p));
  };

  const q = search.toLowerCase();
  const filtered = petitions.filter((p) =>
    !search || p.title?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q) || p.creator_name?.toLowerCase().includes(q)
  );

  const requests   = filtered.filter((p) => p.status === 'Open');
  const inProgress = filtered.filter((p) => p.status === 'Acknowledged');
  const closed     = filtered.filter((p) => p.status === 'Resolved' || p.status === 'Closed');

  const stats = [
    { label: 'Total',       value: petitions.length,                                              icon: Users,       color: '#415d43' },
    { label: 'Active',      value: petitions.filter((p) => p.status === 'Open').length,           icon: TrendingUp,  color: '#2563EB' },
    { label: 'In Progress', value: petitions.filter((p) => p.status === 'Acknowledged').length,   icon: Trophy,      color: '#D97706' },
    { label: 'Closed',      value: petitions.filter((p) => ['Resolved','Closed'].includes(p.status)).length, icon: CheckCircle2, color: '#059669' },
  ];

  const TABS = [
    { key: 'requests',   label: 'Requests',    count: requests.length },
    { key: 'inprogress', label: 'In Progress', count: inProgress.length },
    { key: 'closed',     label: 'Closed',      count: closed.length },
  ];

  const currentList = tab === 'requests' ? requests : tab === 'inprogress' ? inProgress : closed;

  return (
    <div className="flex min-h-screen bg-srec-background">
      <AuthoritySidebar />
      <div className="flex-1 min-w-0 overflow-y-auto flex flex-col">
        <AuthorityHeader />
        <div className="max-w-5xl mx-auto w-full px-6 py-6 space-y-5">

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {stats.map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="h-0.5 w-full" style={{ background: color }} />
                <div className="p-3 flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">{label}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
                  </div>
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${color}18`, color }}>
                    <Icon size={16} />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Search + Tabs */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
              <input type="text" placeholder="Search petitions..." value={search} onChange={(e) => setSearch(e.target.value)}
                className="w-full border border-gray-200 rounded-xl py-2.5 pl-9 pr-3 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none bg-white" />
              {search && <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"><X size={13} /></button>}
            </div>
            <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
              {TABS.map(({ key, label, count }) => (
                <button key={key} onClick={() => setTab(key)}
                  className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                  {label}{count > 0 ? ` (${count})` : ''}
                </button>
              ))}
            </div>
          </div>

          {/* List */}
          {loading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32 rounded-2xl" />)}</div>
          ) : currentList.length === 0 ? (
            <EmptyState
              message={`No ${tab === 'requests' ? 'active' : tab === 'inprogress' ? 'in-progress' : 'closed'} petitions`}
              sub={search ? 'Try adjusting your search' : undefined}
            />
          ) : (
            <div className="space-y-3">
              {currentList.map((p) => (
                <PetitionCard key={p.id} petition={p} onRespond={(p) => setRespondTarget(p)} isClosed={tab === 'closed'} />
              ))}
            </div>
          )}
        </div>
      </div>

      <RespondModal
        petition={respondTarget}
        isOpen={!!respondTarget}
        onClose={() => setRespondTarget(null)}
        onResponded={(updated) => { handleResponded(updated); setRespondTarget(null); }}
      />
    </div>
  );
}
