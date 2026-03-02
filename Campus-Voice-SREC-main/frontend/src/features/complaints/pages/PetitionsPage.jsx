import React, { useState, useEffect, useCallback } from 'react';
import petitionService from '../../../services/petition.service';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Users, MessageSquarePlus, X, ChevronDown, Clock,
  CheckCircle, AlertTriangle, Flame, Globe, Building2, Home,
  ShieldCheck, Info, Lock,
} from 'lucide-react';

const MILESTONES = [50, 100, 250];

const STATUS_ACCENT = {
  Open: 'bg-emerald-500',
  Acknowledged: 'bg-amber-400',
  Resolved: 'bg-blue-500',
  Closed: 'bg-gray-300',
};
const STATUS_BADGE = {
  Open: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Acknowledged: 'bg-amber-50 text-amber-700 border-amber-200',
  Resolved: 'bg-blue-50 text-blue-700 border-blue-200',
  Closed: 'bg-gray-100 text-gray-500 border-gray-200',
};

const SCOPE_ICONS = { General: Globe, Department: Building2, Hostel: Home };
const SCOPE_COLORS = {
  General: 'bg-sky-50 text-sky-700 border-sky-200',
  Department: 'bg-purple-50 text-purple-700 border-purple-200',
  Hostel: 'bg-orange-50 text-orange-700 border-orange-200',
};

// ─────────────────────── DeadlineChip ───────────────────────────────────────
function DeadlineChip({ daysRemaining, deadline }) {
  if (!deadline) return null;
  if (daysRemaining === null || daysRemaining === undefined) return null;
  if (daysRemaining <= 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-red-50 text-red-600 border border-red-200">
        <AlertTriangle size={9} /> Expired
      </span>
    );
  }
  if (daysRemaining <= 3) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-orange-50 text-orange-600 border border-orange-200">
        <Clock size={9} /> {daysRemaining}d left
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-gray-50 text-gray-500 border border-gray-200">
      <Clock size={9} /> {daysRemaining}d left
    </span>
  );
}

// ─────────────────────── PetitionCard ───────────────────────────────────────
function PetitionCard({ petition, onSign, currentUserRoll, signing }) {
  const {
    signature_count,
    custom_goal,
    milestone_goal,
    milestones_reached = [],
    progress_pct,
    status,
    days_remaining,
    deadline,
  } = petition;

  const goal = custom_goal || milestone_goal || 50;
  const isSigned = petition.signed_by_me;
  const isOwner = petition.created_by_roll_no === currentUserRoll;
  const isClosed = status === 'Resolved' || status === 'Closed';
  const isExpired = days_remaining !== null && days_remaining !== undefined && days_remaining <= 0;
  const goalReached = signature_count >= goal;
  const accentClass = STATUS_ACCENT[status] || STATUS_ACCENT.Open;
  const ScopeIcon = SCOPE_ICONS[petition.petition_scope] || Globe;
  const isPending = !petition.is_published;

  return (
    <div className={`bg-white/80 backdrop-blur-sm rounded-2xl border shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)] overflow-hidden
                    hover:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.12)] hover:-translate-y-0.5 transition-all duration-300
                    ${isPending ? 'border-amber-200' : 'border-white/60'}`}>
      {/* Accent top bar */}
      <div className={`h-1 w-full ${isPending ? 'bg-amber-300' : accentClass}`} />

      <div className="p-4">
        {isPending && (
          <div className="mb-2 px-2.5 py-1.5 bg-amber-50 border border-amber-200 rounded-xl text-[10px] text-amber-800 flex items-center gap-1.5">
            <Clock size={10} className="text-amber-600 flex-shrink-0" />
            Awaiting authority approval before visible to others
          </div>
        )}

        <div className="flex items-start gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border ${STATUS_BADGE[status] || STATUS_BADGE.Open}`}>
                {status}
              </span>
              <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border inline-flex items-center gap-1 ${SCOPE_COLORS[petition.petition_scope] || SCOPE_COLORS.General}`}>
                <ScopeIcon size={8} />
                {petition.petition_scope || 'General'}
              </span>
              {petition.department_name && (
                <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-purple-50 text-purple-600 border border-purple-200">
                  {petition.department_name}
                </span>
              )}
              <DeadlineChip daysRemaining={days_remaining} deadline={deadline} />
              {goalReached && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle size={9} /> Goal Reached!
                </span>
              )}
            </div>
            <h3 className="text-sm font-bold text-gray-900 leading-snug line-clamp-2">
              {petition.title}
            </h3>
          </div>
        </div>

        <p className="text-xs text-gray-600 mb-3 line-clamp-2">{petition.description}</p>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
            <span>
              <strong className="text-gray-900 text-xs">{signature_count}</strong>{' '}
              <span className="text-gray-400">/ {goal} signatures</span>
            </span>
            <span className="font-semibold text-srec-primary">{Math.min(progress_pct || 0, 100)}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-2.5 rounded-full transition-all duration-700 ${
                goalReached
                  ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                  : 'bg-gradient-to-r from-srec-primary to-emerald-500'
              }`}
              style={{ width: `${Math.min(progress_pct || 0, 100)}%` }}
            />
          </div>
          {MILESTONES.some(m => m <= goal * 3) && (
            <div className="flex gap-1 mt-1.5 flex-wrap">
              {MILESTONES.filter(m => m <= goal * 3).map((m) => (
                <span
                  key={m}
                  className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border transition-all ${
                    milestones_reached.includes(m)
                      ? 'bg-amber-100 text-amber-700 border-amber-300'
                      : 'bg-gray-50 text-gray-400 border-gray-200'
                  }`}
                >
                  {milestones_reached.includes(m) ? '🏆' : '○'} {m}
                </span>
              ))}
            </div>
          )}
        </div>

        {petition.authority_response && (
          <div className="mb-3 p-2.5 bg-blue-50 rounded-xl border border-blue-100 text-xs text-blue-800">
            <p className="font-bold text-[10px] uppercase tracking-wider text-blue-600 mb-0.5">Official Response</p>
            {petition.authority_response}
          </div>
        )}

        {!isPending && !isClosed && !isOwner && !isExpired && (
          <button
            onClick={() => onSign(petition.id)}
            disabled={signing === petition.id}
            className={`w-full py-2.5 rounded-xl text-xs font-bold border transition-all duration-200 ${
              isSigned
                ? 'bg-srec-primarySoft text-srec-primary border-srec-primaryMuted/40 hover:bg-red-50 hover:text-red-600 hover:border-red-200'
                : 'bg-srec-primary text-white border-srec-primary hover:bg-srec-primaryDark shadow-btn active:scale-[0.97]'
            } disabled:opacity-60`}
          >
            {signing === petition.id ? '...' : isSigned ? '✓ Signed — Click to Unsign' : '✍ Sign this Petition'}
          </button>
        )}
        {isExpired && !isClosed && !isPending && (
          <div className="w-full py-2 rounded-xl text-xs font-medium text-center text-gray-400 bg-gray-50 border border-dashed border-gray-200">
            This petition has expired
          </div>
        )}
        {isOwner && !isClosed && !isPending && (
          <p className="text-center text-[10px] text-gray-400 mt-1 py-1">You created this petition</p>
        )}
        {isClosed && (
          <p className="text-center text-[10px] text-gray-400 mt-1 py-1">This petition is {status.toLowerCase()}</p>
        )}

        <p className="text-[10px] text-gray-400 mt-2 text-right">
          {petition.creator_name || petition.created_by_roll_no} ·{' '}
          {petition.submitted_at
            ? new Date(petition.submitted_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
            : ''}
        </p>
      </div>
    </div>
  );
}

// ─────────────────────── RepresentativeBanner ───────────────────────────────
function RepresentativeBanner({ onTryCreate }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    petitionService.getMyRepStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (!status) return null;

  if (status.is_representative && status.can_create) {
    return (
      <div className="mb-4 p-3.5 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <ShieldCheck size={16} className="text-emerald-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-emerald-800">
            You are a Student Representative
          </p>
          <p className="text-[11px] text-emerald-700 mt-0.5">
            {(status.scopes || [status.scope]).join(' & ')} rep — you can launch petitions on behalf of your peers.{' '}
            <button onClick={onTryCreate} className="underline font-semibold hover:text-emerald-600">
              Start one now
            </button>
          </p>
        </div>
      </div>
    );
  }

  if (status.is_representative && !status.can_create) {
    const days = status.cooldown_remaining ?? status.cooldown_days_remaining ?? 0;
    return (
      <div className="mb-4 p-3.5 bg-amber-50 rounded-xl border border-amber-200 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
          <Clock size={16} className="text-amber-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-amber-800">Rep cooldown active</p>
          <p className="text-[11px] text-amber-700 mt-0.5">
            You can create another petition in <strong>{days} day{days !== 1 ? 's' : ''}</strong>.
          </p>
        </div>
      </div>
    );
  }

  // Not a rep
  return (
    <div className="mb-4 p-3.5 bg-gray-50 rounded-xl border border-gray-200 flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Lock size={15} className="text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-gray-700">Petitions are for Student Representatives only</p>
        <p className="text-[11px] text-gray-500 mt-0.5">
          Only students appointed as representatives by an authority can launch petitions.
          Signing and following petitions is open to all.
        </p>
      </div>
    </div>
  );
}

// ─────────────────────── CreatePetitionModal ────────────────────────────────
function CreatePetitionModal({ isOpen, onClose, onCreated, userStayType, repStatus }) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    petition_scope: 'Department',
    custom_goal: 50,
    duration_days: 7,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Derive allowed scopes — NO General, only rep's actual scopes
  const allowedScopes = (() => {
    const backendScopes = repStatus?.scopes;
    if (backendScopes && backendScopes.length > 0) {
      return backendScopes.filter(s => s === 'Department' || s === 'Hostel');
    }
    const single = repStatus?.scope;
    if (single === 'Hostel') return ['Hostel'];
    return ['Department'];
  })();

  const isDualScope = allowedScopes.length > 1;

  // Auto-select the correct scope when modal opens
  useEffect(() => {
    if (isOpen && allowedScopes.length > 0) {
      setForm(f => ({ ...f, petition_scope: allowedScopes[0] }));
      setError('');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen) return null;

  const cooldownActive = repStatus?.is_representative && !repStatus?.can_create;
  const cooldownDays = repStatus?.cooldown_remaining ?? repStatus?.cooldown_days_remaining ?? 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.title.length < 10) { setError('Title must be at least 10 characters'); return; }
    if (form.description.length < 30) { setError('Description must be at least 30 characters'); return; }
    if (form.custom_goal < 50) { setError('Minimum goal is 50 signatures'); return; }
    if (form.duration_days < 1 || form.duration_days > 15) { setError('Duration must be 1–15 days'); return; }

    try {
      setLoading(true);
      const payload = {
        title: form.title,
        description: form.description,
        petition_scope: form.petition_scope,
        custom_goal: Number(form.custom_goal),
        duration_days: Number(form.duration_days),
      };
      const result = await petitionService.createPetition(payload);
      onCreated(result);
      onClose();
      setForm({ title: '', description: '', petition_scope: allowedScopes[0] || 'Department', custom_goal: 50, duration_days: 7 });
    } catch (err) {
      setError(err.message || 'Failed to create petition');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm animate-backdrop"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-3xl sm:rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto animate-modal-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white/90 backdrop-blur-sm px-6 pt-6 pb-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-900 font-heading">Launch a Petition</h2>
            <p className="text-xs text-gray-500 mt-0.5">Collect signatures for systemic campus issues</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          {cooldownActive ? (
            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 flex items-start gap-2">
              <Clock size={13} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-[11px] text-amber-800">
                Cooldown active — you can create another petition in <strong>{cooldownDays} day{cooldownDays !== 1 ? 's' : ''}</strong>. (1 petition per {repStatus?.cooldown_days ?? 7} days)
              </p>
            </div>
          ) : (
            <div className="p-3 bg-blue-50 rounded-xl border border-blue-100 flex items-start gap-2">
              <Info size={13} className="text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-[11px] text-blue-800">
                Your petition needs authority approval before it becomes visible to others.
              </p>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Title *</label>
            <input
              type="text"
              placeholder="e.g. Extend library hours during exams"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
              maxLength={255}
            />
            <p className="text-[10px] text-gray-400 mt-0.5 text-right">{form.title.length}/255</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Description *</label>
            <textarea
              placeholder="Who is affected, why it matters, what change you want..."
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={4}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm resize-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
              maxLength={2000}
            />
            <p className="text-[10px] text-gray-400 mt-0.5 text-right">{form.description.length}/2000</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">Visibility Scope</label>
            {isDualScope ? (
              /* Dual rep: show Department / Hostel toggle */
              <div className="flex gap-2">
                {allowedScopes.map((scope) => {
                  const Icon = SCOPE_ICONS[scope] || Building2;
                  const desc = scope === 'Department'
                    ? 'Only students in your department'
                    : 'Only hostel residents';
                  return (
                    <button
                      key={scope}
                      type="button"
                      onClick={() => setForm(f => ({ ...f, petition_scope: scope }))}
                      className={`flex-1 flex flex-col items-center gap-1 p-3 rounded-xl border text-xs font-semibold transition-all ${
                        form.petition_scope === scope
                          ? 'border-srec-primary bg-srec-primarySoft text-srec-primary'
                          : 'border-gray-200 text-gray-600 hover:border-srec-primaryMuted hover:bg-gray-50'
                      }`}
                    >
                      <Icon size={16} />
                      {scope}
                      <span className="text-[10px] font-normal text-gray-400">{desc}</span>
                    </button>
                  );
                })}
              </div>
            ) : (
              /* Single rep: show static badge, no toggle */
              <div className="p-3 bg-srec-primarySoft rounded-xl border border-srec-primaryMuted/40 flex items-center gap-2.5">
                {React.createElement(SCOPE_ICONS[allowedScopes[0]] || Building2, { size: 14, className: 'text-srec-primary flex-shrink-0' })}
                <div>
                  <p className="text-xs font-semibold text-srec-primary">{allowedScopes[0]}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    {allowedScopes[0] === 'Department'
                      ? 'Only students in your department can see and sign'
                      : 'Only hostel residents can see and sign'}
                  </p>
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Signature Goal <span className="font-normal text-gray-400">(min. 50)</span>
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={50}
                step={10}
                max={10000}
                value={form.custom_goal}
                onChange={(e) => setForm((f) => ({ ...f, custom_goal: Math.max(50, parseInt(e.target.value) || 50) }))}
                className="w-32 border border-gray-200 rounded-xl px-3 py-2.5 text-sm font-bold text-srec-primary focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary outline-none transition-all"
              />
              <p className="text-xs text-gray-500">signatures needed to notify authorities</p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Petition Duration:{' '}
              <span className="text-srec-primary font-bold">
                {form.duration_days} day{form.duration_days !== 1 ? 's' : ''}
              </span>
            </label>
            <input
              type="range"
              min={1}
              max={15}
              step={1}
              value={form.duration_days}
              onChange={(e) => setForm((f) => ({ ...f, duration_days: parseInt(e.target.value) }))}
              className="w-full accent-srec-primary"
            />
            <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
              <span>1 day</span>
              <span>7 days</span>
              <span>15 days</span>
            </div>
            <p className="text-[10px] text-amber-700 mt-1">Signing is blocked after the deadline. Max 15 days.</p>
          </div>

          {error && <p className="text-xs text-srec-danger bg-red-50 px-3 py-2 rounded-lg border border-red-100">{error}</p>}

          <button
            type="submit"
            disabled={loading || cooldownActive}
            className="w-full py-3 bg-srec-primary text-white rounded-xl text-sm font-bold shadow-btn hover:bg-srec-primaryDark disabled:opacity-60 transition-all active:scale-[0.98]"
          >
            {loading ? 'Creating petition...' : cooldownActive ? `Available in ${cooldownDays}d` : '🚀 Launch Petition'}
          </button>

          <p className="text-[10px] text-center text-gray-400 pb-2">
            You automatically sign your own petition. When the goal is reached, all signers and relevant authorities will be notified.
          </p>
        </form>
      </div>
    </div>
  );
}

// ═══════════════════════ PetitionsPage ══════════════════════════════════════
export default function PetitionsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [petitions, setPetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [mainTab, setMainTab] = useState('ongoing'); // 'ongoing' | 'closed'
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [signing, setSigning] = useState(null);
  const [repStatus, setRepStatus] = useState(null);

  const LIMIT = 50;
  const isStudent = user?.role === 'Student';

  // Load rep status once
  useEffect(() => {
    if (isStudent) {
      petitionService.getMyRepStatus()
        .then(setRepStatus)
        .catch(() => setRepStatus(null));
    }
  }, [isStudent]);

  const fetchPetitions = useCallback(
    async (resetSkip = true) => {
      try {
        if (resetSkip) setLoading(true);
        else setLoadingMore(true);

        const currentSkip = resetSkip ? 0 : skip;
        const data = await petitionService.getPetitions(currentSkip, LIMIT, null);
        const list = data?.petitions || [];
        const dataTotal = data?.total || 0;

        if (resetSkip) {
          setPetitions(list);
          setSkip(LIMIT);
        } else {
          setPetitions((prev) => [...prev, ...list]);
          setSkip((s) => s + LIMIT);
        }
        setTotal(dataTotal);
        setHasMore(list.length === LIMIT);
      } catch (err) {
        console.error('Failed to load petitions:', err);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [skip]
  );

  useEffect(() => {
    fetchPetitions(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSign = async (petitionId) => {
    setSigning(petitionId);
    try {
      const result = await petitionService.signPetition(petitionId);
      setPetitions((prev) =>
        prev.map((p) =>
          p.id === petitionId
            ? {
                ...p,
                signed_by_me: result.signed,
                signature_count: result.signature_count,
                progress_pct: Math.min(
                  Math.round((result.signature_count / (p.custom_goal || p.milestone_goal || 50)) * 100),
                  100
                ),
              }
            : p
        )
      );
    } catch (err) {
      console.error('Sign error:', err);
    } finally {
      setSigning(null);
    }
  };

  const handleCreated = (newPetition) => {
    setPetitions((prev) => [newPetition, ...prev]);
    setTotal((t) => t + 1);
  };

  const isRep = repStatus?.is_representative;
  const canCreate = isRep && repStatus?.can_create;

  // Compute petition groups
  const getGoal = (p) => p.custom_goal || p.milestone_goal || 50;
  const ongoingPetitions = petitions.filter(p => p.status === 'Open' || p.status === 'Acknowledged');
  const closedPetitions = petitions.filter(p => p.status === 'Resolved' || p.status === 'Closed');
  const goalReachedPetitions = closedPetitions.filter(p => p.signature_count >= getGoal(p));
  const failedPetitions = closedPetitions.filter(p => p.signature_count < getGoal(p));

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />

      <div className="max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">
        {/* Community tab bar: Petitions | Wins */}
        <div className="flex gap-1 mb-4 bg-white/70 backdrop-blur-sm border border-white/60 rounded-xl p-1 shadow-sm">
          <button
            className="flex-1 py-2 rounded-lg text-xs font-bold bg-srec-primary text-white shadow-sm transition-all"
          >
            Petitions
          </button>
          <button
            onClick={() => navigate('/wins')}
            className="flex-1 py-2 rounded-lg text-xs font-semibold text-gray-500 hover:text-gray-800 hover:bg-gray-100/60 transition-all"
          >
            Wins
          </button>
        </div>

        {/* Page header */}
        <div className="mb-5 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-5 shadow-elevated relative overflow-hidden">
          <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-white/5 pointer-events-none" />
          <div className="absolute -bottom-10 -right-3 w-24 h-24 rounded-full bg-white/5 pointer-events-none" />
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Users size={16} className="text-emerald-300" />
                <p className="text-emerald-300/80 text-[11px] font-semibold uppercase tracking-[0.15em]">CampusVoice</p>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight font-heading">Petitions</h1>
              <p className="text-green-300/80 text-xs mt-1">Collective action for systemic campus changes</p>
              {total > 0 && (
                <span className="mt-2 inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-white/15 text-white border border-white/20">
                  {total} petition{total !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            {isStudent && isRep && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-white/15 hover:bg-white/25 text-white border border-white/20 rounded-xl text-xs font-bold transition-all backdrop-blur-sm flex-shrink-0"
              >
                <MessageSquarePlus size={14} />
                Start Petition
              </button>
            )}
          </div>
        </div>

        {/* Rep banner — students only */}
        {isStudent && <RepresentativeBanner onTryCreate={() => setShowCreateModal(true)} />}

        {/* Info banner */}
        <div className="mb-4 p-3 bg-amber-50 rounded-xl border border-amber-100 flex items-start gap-2">
          <Flame size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-800">
            When a petition hits <strong>50, 100, or 250</strong> signatures, authorities are notified.
            Reaching your custom goal notifies all signers, the creator, and relevant admin.
            Petitions expire after their deadline (max 15 days).
          </p>
        </div>

        {/* Ongoing | Closed tab bar */}
        <div className="flex gap-1 mb-4 bg-white/70 backdrop-blur-sm border border-white/60 rounded-xl p-1 shadow-sm">
          <button
            onClick={() => setMainTab('ongoing')}
            className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
              mainTab === 'ongoing'
                ? 'bg-srec-primary text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100/60'
            }`}
          >
            Ongoing {!loading && ongoingPetitions.length > 0 && `(${ongoingPetitions.length})`}
          </button>
          <button
            onClick={() => setMainTab('closed')}
            className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
              mainTab === 'closed'
                ? 'bg-srec-primary text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100/60'
            }`}
          >
            Closed {!loading && closedPetitions.length > 0 && `(${closedPetitions.length})`}
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-52 rounded-2xl" />)}
          </div>
        ) : mainTab === 'ongoing' ? (
          ongoingPetitions.length === 0 ? (
            <div className="text-center py-14 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]">
              <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-srec-primarySoft flex items-center justify-center">
                <Users size={24} className="text-srec-primary" />
              </div>
              <p className="text-gray-900 text-base font-semibold">No ongoing petitions</p>
              <p className="text-gray-500 text-sm mt-1">No active petitions at the moment.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {ongoingPetitions.map((petition) => (
                <PetitionCard
                  key={petition.id}
                  petition={petition}
                  onSign={handleSign}
                  currentUserRoll={user?.roll_no}
                  signing={signing}
                />
              ))}
            </div>
          )
        ) : (
          /* Closed tab */
          closedPetitions.length === 0 ? (
            <div className="text-center py-14 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]">
              <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
                <CheckCircle size={24} className="text-gray-400" />
              </div>
              <p className="text-gray-900 text-base font-semibold">No closed petitions</p>
              <p className="text-gray-500 text-sm mt-1">Completed petitions will appear here.</p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Goal Reached sub-section */}
              {goalReachedPetitions.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle size={14} className="text-emerald-600" />
                    <h3 className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                      Goal Reached ({goalReachedPetitions.length})
                    </h3>
                    <div className="flex-1 h-px bg-emerald-100" />
                  </div>
                  <div className="space-y-3">
                    {goalReachedPetitions.map((petition) => (
                      <PetitionCard
                        key={petition.id}
                        petition={petition}
                        onSign={handleSign}
                        currentUserRoll={user?.roll_no}
                        signing={signing}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Failed / Did not reach goal sub-section */}
              {failedPetitions.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle size={14} className="text-gray-400" />
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                      Goal Not Reached ({failedPetitions.length})
                    </h3>
                    <div className="flex-1 h-px bg-gray-100" />
                  </div>
                  <div className="space-y-3">
                    {failedPetitions.map((petition) => (
                      <PetitionCard
                        key={petition.id}
                        petition={petition}
                        onSign={handleSign}
                        currentUserRoll={user?.roll_no}
                        signing={signing}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        )}

        {/* Load more — only for ongoing tab */}
        {!loading && mainTab === 'ongoing' && hasMore && (
          <div className="flex justify-center pt-4">
            <button
              onClick={() => fetchPetitions(false)}
              disabled={loadingMore}
              className="flex items-center gap-2 border border-gray-200 bg-white text-gray-600 rounded-xl px-6 py-2 text-sm font-semibold hover:bg-srec-primarySoft hover:border-srec-primaryMuted hover:text-srec-primary transition-all disabled:opacity-50 shadow-sm"
            >
              {loadingMore ? 'Loading...' : <><ChevronDown size={15} /> Load More</>}
            </button>
          </div>
        )}
      </div>

      <CreatePetitionModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={handleCreated}
        userStayType={user?.stay_type}
        repStatus={repStatus}
      />

      <BottomNav />
    </div>
  );
}
