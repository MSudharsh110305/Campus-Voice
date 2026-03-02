import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../../utils/api';
import { Skeleton } from '../../../components/UI';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import { useAuth } from '../../../context/AuthContext';
import {
  Users,
  Trophy,
  CheckCircle2,
  MessageSquare,
  Search,
  X,
  Clock,
  Globe,
  Building2,
  Home,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

const MILESTONES = [50, 100, 250];

const STATUS_COLORS = {
  Open: 'bg-blue-50 text-blue-700 border-blue-100',
  Acknowledged: 'bg-amber-50 text-amber-700 border-amber-100',
  Resolved: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  Closed: 'bg-gray-100 text-gray-500 border-gray-200',
};

const SCOPE_ICONS = {
  General: Globe,
  Department: Building2,
  Hostel: Home,
};

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
      setStatus(
        petition?.status === 'Open' ? 'Acknowledged' : petition?.status || 'Acknowledged'
      );
      setError('');
    }
  }, [isOpen, petition]);

  if (!isOpen || !petition) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!response.trim()) {
      setError('Response cannot be empty');
      return;
    }
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-srec-textPrimary">Respond to Petition</h2>
            <p className="text-xs text-srec-textMuted mt-0.5 line-clamp-1">{petition.title}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
            <X size={16} />
          </button>
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
            <textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              placeholder="Write an official response to this petition..."
              rows={5}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
              maxLength={2000}
            />
            <p className="text-[10px] text-srec-textMuted mt-1 text-right">{response.length}/2000</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-srec-textSecondary mb-1.5 uppercase tracking-wide">Update Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all"
            >
              {RESPOND_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 border border-red-100">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 border border-gray-200 text-srec-textSecondary rounded-xl text-sm font-semibold hover:bg-gray-50 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="flex-1 py-2.5 bg-srec-primary text-white rounded-xl text-sm font-bold shadow-btn hover:bg-srec-primaryDark disabled:opacity-60 transition-all">
              {loading ? 'Submitting...' : 'Submit Response'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── PetitionRow ────────────────────────────────────────
function PetitionRow({ petition, onRespond, onApprove, onReject, approving }) {
  const { signature_count, milestone_goal, milestones_reached = [], progress_pct, status } = petition;
  const isPending = !petition.is_published;
  const ScopeIcon = SCOPE_ICONS[petition.petition_scope] || Globe;

  return (
    <div className={`bg-white rounded-2xl border shadow-sm p-4 hover:shadow-md transition-all duration-200 ${isPending ? 'border-amber-200 bg-amber-50/30' : 'border-gray-100'}`}>
      {isPending && (
        <div className="mb-3 px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-center gap-1.5">
          <Clock size={12} className="text-amber-600" />
          <span className="font-semibold">Pending Approval</span>
          <span className="text-amber-600">— Approve to make it visible to students</span>
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
          </div>
          <h3 className="text-sm font-bold text-srec-textPrimary leading-snug line-clamp-1">{petition.title}</h3>
          <p className="text-xs text-srec-textSecondary mt-0.5 line-clamp-2">{petition.description}</p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
          {isPending ? (
            <>
              <button
                onClick={() => onApprove(petition)}
                disabled={approving === petition.id}
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 transition-all disabled:opacity-60"
              >
                <CheckCircle size={12} />
                {approving === petition.id ? '...' : 'Approve'}
              </button>
              <button
                onClick={() => onReject(petition)}
                className="flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold hover:bg-red-100 transition-all"
              >
                <XCircle size={12} />
                Reject
              </button>
            </>
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

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex justify-between text-[10px] text-srec-textMuted mb-1">
          <span><strong className="text-srec-textPrimary">{signature_count}</strong> signed</span>
          <span>Goal: {petition.custom_goal || milestone_goal}</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-1.5 rounded-full bg-gradient-to-r from-srec-primary to-emerald-500 transition-all duration-500"
            style={{ width: `${Math.min(progress_pct || 0, 100)}%` }}
          />
        </div>
      </div>

      {/* Authority response preview */}
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
        {petition.days_remaining !== null && petition.days_remaining !== undefined && (
          <>
            <span>·</span>
            <span className={petition.days_remaining <= 0 ? 'text-red-500 font-semibold' : petition.days_remaining <= 3 ? 'text-orange-500' : ''}>
              {petition.days_remaining <= 0 ? 'Expired' : `${petition.days_remaining}d left`}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────── RejectModal ────────────────────────────────────────
function RejectModal({ petition, isOpen, onClose, onRejected }) {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen || !petition) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!reason.trim()) { setError('Please provide a reason'); return; }
    try {
      setLoading(true);
      await api(`/petitions/${petition.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ response: reason.trim(), status: 'Closed' }),
      });
      onRejected(petition.id);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to reject petition');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-bold text-srec-textPrimary">Reject Petition</h2>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100"><X size={15} /></button>
        </div>
        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-3">
          <p className="text-xs text-srec-textSecondary line-clamp-2">"{petition.title}"</p>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Reason for rejection *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this petition cannot be published..."
              rows={4}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none transition-all"
            />
          </div>
          {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2 border border-gray-200 rounded-xl text-sm font-semibold text-gray-600 hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={loading} className="flex-1 py-2 bg-red-600 text-white rounded-xl text-sm font-bold hover:bg-red-700 disabled:opacity-60">
              {loading ? 'Rejecting...' : 'Reject Petition'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ═══════════════════════ AuthorityPetitions ══════════════════════════════════
export default function AuthorityPetitions() {
  const { user } = useAuth();

  const [petitions, setPetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [pubTab, setPubTab] = useState('ongoing'); // 'ongoing' | 'closed'
  const [respondTarget, setRespondTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
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
      const data = await api(`/petitions/?${params}`);
      setPetitions(data?.petitions || []);
    } catch (err) {
      console.error('Failed to load petitions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPetitions();
  }, []);

  const filtered = petitions.filter((p) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.title?.toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q) ||
      p.creator_name?.toLowerCase().includes(q)
    );
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
      console.error('Failed to approve petition:', err);
      alert(err.message || 'Failed to approve petition');
    } finally {
      setApproving(null);
    }
  };

  const handleRejected = (petitionId) => {
    setPetitions((prev) => prev.filter((p) => p.id !== petitionId));
  };

  const getGoal = (p) => p.custom_goal || p.milestone_goal || 50;
  const pendingPetitions = filtered.filter((p) => !p.is_published);
  const publishedPetitions = filtered.filter((p) => p.is_published);
  const ongoingPetitions = publishedPetitions.filter((p) => p.status === 'Open' || p.status === 'Acknowledged');
  const closedPetitions = publishedPetitions.filter((p) => p.status === 'Resolved' || p.status === 'Closed');
  const goalReachedPetitions = closedPetitions.filter((p) => p.signature_count >= getGoal(p));
  const failedPetitions = closedPetitions.filter((p) => p.signature_count < getGoal(p));

  return (
    <div className="flex min-h-screen bg-srec-background">
      <AuthoritySidebar />

      <div className="flex-1 min-w-0 overflow-y-auto flex flex-col">
        {/* Use AuthorityHeader for consistent top nav with profile hover */}
        <AuthorityHeader />

        <div className="max-w-5xl mx-auto w-full px-6 py-6 space-y-5">
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { label: 'Total', value: stats.total, icon: Users, color: '#415d43' },
              { label: 'Pending', value: stats.pending, icon: Clock, color: '#D97706' },
              { label: 'Open', value: stats.open, icon: MessageSquare, color: '#2563EB' },
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

          {/* Search bar */}
          <div className="relative">
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
                {search ? 'Try adjusting your search' : 'No student petitions submitted yet'}
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Pending approval section — always shown at top */}
              {pendingPetitions.length > 0 && (
                <div>
                  <h2 className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Clock size={12} /> Awaiting Approval ({pendingPetitions.length})
                  </h2>
                  <div className="space-y-3">
                    {pendingPetitions.map((petition) => (
                      <PetitionRow
                        key={petition.id}
                        petition={petition}
                        onRespond={(p) => setRespondTarget(p)}
                        onApprove={handleApprove}
                        onReject={(p) => setRejectTarget(p)}
                        approving={approving}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Published petitions — tabbed: Ongoing | Closed */}
              {publishedPetitions.length > 0 && (
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                      <CheckCircle size={12} className="text-emerald-600" /> Published ({publishedPetitions.length})
                    </h2>
                  </div>

                  {/* Ongoing | Closed tab bar */}
                  <div className="flex gap-1 mb-4 bg-gray-50 border border-gray-200 rounded-xl p-1">
                    <button
                      onClick={() => setPubTab('ongoing')}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        pubTab === 'ongoing'
                          ? 'bg-white text-gray-900 shadow-sm border border-gray-200/60'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Ongoing {ongoingPetitions.length > 0 && `(${ongoingPetitions.length})`}
                    </button>
                    <button
                      onClick={() => setPubTab('closed')}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        pubTab === 'closed'
                          ? 'bg-white text-gray-900 shadow-sm border border-gray-200/60'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Closed {closedPetitions.length > 0 && `(${closedPetitions.length})`}
                    </button>
                  </div>

                  {pubTab === 'ongoing' ? (
                    ongoingPetitions.length === 0 ? (
                      <div className="text-center py-10 bg-white rounded-2xl border border-gray-100">
                        <p className="text-srec-textPrimary text-sm font-semibold">No ongoing petitions</p>
                        <p className="text-srec-textMuted text-xs mt-1">All published petitions have been resolved.</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {ongoingPetitions.map((petition) => (
                          <PetitionRow
                            key={petition.id}
                            petition={petition}
                            onRespond={(p) => setRespondTarget(p)}
                            onApprove={handleApprove}
                            onReject={(p) => setRejectTarget(p)}
                            approving={approving}
                          />
                        ))}
                      </div>
                    )
                  ) : (
                    closedPetitions.length === 0 ? (
                      <div className="text-center py-10 bg-white rounded-2xl border border-gray-100">
                        <p className="text-srec-textPrimary text-sm font-semibold">No closed petitions</p>
                        <p className="text-srec-textMuted text-xs mt-1">Resolved or closed petitions will appear here.</p>
                      </div>
                    ) : (
                      <div className="space-y-5">
                        {/* Goal Reached */}
                        {goalReachedPetitions.length > 0 && (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <CheckCircle size={13} className="text-emerald-600" />
                              <h3 className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                                Goal Reached ({goalReachedPetitions.length})
                              </h3>
                              <div className="flex-1 h-px bg-emerald-100" />
                            </div>
                            <div className="space-y-3">
                              {goalReachedPetitions.map((petition) => (
                                <PetitionRow
                                  key={petition.id}
                                  petition={petition}
                                  onRespond={(p) => setRespondTarget(p)}
                                  onApprove={handleApprove}
                                  onReject={(p) => setRejectTarget(p)}
                                  approving={approving}
                                />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Goal Not Reached */}
                        {failedPetitions.length > 0 && (
                          <div>
                            <div className="flex items-center gap-2 mb-3">
                              <AlertTriangle size={13} className="text-gray-400" />
                              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                                Goal Not Reached ({failedPetitions.length})
                              </h3>
                              <div className="flex-1 h-px bg-gray-100" />
                            </div>
                            <div className="space-y-3">
                              {failedPetitions.map((petition) => (
                                <PetitionRow
                                  key={petition.id}
                                  petition={petition}
                                  onRespond={(p) => setRespondTarget(p)}
                                  onApprove={handleApprove}
                                  onReject={(p) => setRejectTarget(p)}
                                  approving={approving}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  )}
                </div>
              )}
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

      <RejectModal
        petition={rejectTarget}
        isOpen={!!rejectTarget}
        onClose={() => setRejectTarget(null)}
        onRejected={(id) => { handleRejected(id); setRejectTarget(null); }}
      />
    </div>
  );
}
