import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../../utils/api';
import { Skeleton } from '../../../components/UI';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import {
  Users, CheckCircle2, Search, X,
  Globe, Building2, Home, TrendingUp, Trophy, Target,
} from 'lucide-react';

const SCOPE_ICONS = { General: Globe, Department: Building2, Hostel: Home };
const SCOPE_COLORS = {
  General: 'bg-sky-50 text-sky-700 border-sky-100',
  Department: 'bg-purple-50 text-purple-700 border-purple-100',
  Hostel: 'bg-orange-50 text-orange-700 border-orange-100',
};

// ─────────────────────── PetitionCard ───────────────────────────────────────
function PetitionCard({ petition }) {
  const { signature_count, milestones_reached = [], progress_pct } = petition;
  const ScopeIcon = SCOPE_ICONS[petition.petition_scope] || Globe;
  const goal = petition.custom_goal || petition.milestone_goal || 50;
  const goalReached = petition.goal_reached_notified;
  const pct = Math.min(progress_pct || Math.round((signature_count / goal) * 100), 100);

  return (
    <div className={`bg-white rounded-2xl border shadow-sm hover:shadow-md transition-all duration-200 ${goalReached ? 'border-emerald-200' : 'border-gray-100'}`}>
      {goalReached && <div className="h-0.5 w-full bg-emerald-400 rounded-t-2xl" />}
      <div className="p-4">
        {/* Badges */}
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border inline-flex items-center gap-1 ${SCOPE_COLORS[petition.petition_scope] || SCOPE_COLORS.General}`}>
            <ScopeIcon size={9} />{petition.petition_scope || 'General'}
          </span>
          {petition.department_name && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-100">{petition.department_name}</span>
          )}
          {goalReached ? (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">
              <CheckCircle2 size={9} />Goal Reached — Action Required
            </span>
          ) : petition.days_remaining !== null && petition.days_remaining !== undefined ? (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
              petition.days_remaining <= 0 ? 'bg-red-50 text-red-600 border-red-100'
              : petition.days_remaining <= 3 ? 'bg-orange-50 text-orange-600 border-orange-100'
              : 'bg-gray-50 text-gray-500 border-gray-100'
            }`}>
              {petition.days_remaining <= 0 ? 'Expired' : `${petition.days_remaining}d left`}
            </span>
          ) : null}
        </div>

        {/* Title + description */}
        <h3 className="text-sm font-bold text-srec-textPrimary leading-snug">{petition.title}</h3>
        <p className="text-xs text-srec-textSecondary mt-0.5 line-clamp-2">{petition.description}</p>

        {/* Progress bar */}
        <div className="mt-3 mb-2">
          <div className="flex justify-between text-[10px] text-srec-textMuted mb-1">
            <span><strong className="text-srec-textPrimary text-xs">{signature_count}</strong> signed</span>
            <span>Goal: {goal}</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${goalReached ? 'bg-emerald-500' : 'bg-gradient-to-r from-srec-primary to-emerald-400'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Footer meta */}
        <div className="flex items-center gap-2 text-[10px] text-srec-textMuted mt-2">
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
        <Target size={20} className="text-srec-primary" />
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
  const [tab, setTab] = useState('active');
  const [search, setSearch] = useState('');

  const fetchPetitions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api('/petitions/?skip=0&limit=500');
      setPetitions(data?.petitions || []);
    } catch (err) {
      console.error('Failed to load petitions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPetitions(); }, [fetchPetitions]);

  const q = search.toLowerCase();
  const filtered = petitions.filter((p) =>
    !search || p.title?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q) || p.creator_name?.toLowerCase().includes(q)
  );

  const active      = filtered.filter((p) => !p.goal_reached_notified);
  const goalReached = filtered.filter((p) => p.goal_reached_notified);

  const stats = [
    { label: 'Total',        value: petitions.length,                                        icon: Users,        color: '#415d43' },
    { label: 'Active',       value: petitions.filter((p) => !p.goal_reached_notified).length, icon: TrendingUp,   color: '#2563EB' },
    { label: 'Goal Reached', value: petitions.filter((p) => p.goal_reached_notified).length,  icon: CheckCircle2, color: '#059669' },
    { label: 'Milestones',   value: petitions.reduce((s, p) => s + (p.milestones_reached?.length || 0), 0), icon: Trophy, color: '#D97706' },
  ];

  const TABS = [
    { key: 'active',      label: 'Active',      count: active.length },
    { key: 'goalreached', label: 'Goal Reached', count: goalReached.length },
  ];

  const currentList = tab === 'active' ? active : goalReached;

  return (
    <div className="flex min-h-screen bg-srec-background">
      <AuthoritySidebar />
      <div className="flex-1 min-w-0 overflow-y-auto flex flex-col">
        <AuthorityHeader />
        <div className="max-w-5xl mx-auto w-full px-6 py-6 space-y-5">

          <div>
            <h1 className="text-xl font-bold text-srec-textPrimary">Petitions</h1>
            <p className="text-sm text-srec-textMuted mt-0.5">You are notified when a petition in your scope reaches its goal</p>
          </div>

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
            <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}</div>
          ) : currentList.length === 0 ? (
            <EmptyState
              message={tab === 'active' ? 'No active petitions in your scope' : 'No petitions have reached their goal yet'}
              sub={search ? 'Try adjusting your search' : undefined}
            />
          ) : (
            <div className="space-y-3">
              {currentList.map((p) => <PetitionCard key={p.id} petition={p} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
