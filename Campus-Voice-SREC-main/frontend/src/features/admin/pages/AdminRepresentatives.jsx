import React, { useState, useEffect, useCallback } from 'react';
import adminService from '../../../services/admin.service';
import { Skeleton } from '../../../components/UI';
import { UserCheck, UserPlus, UserMinus, Building2, Home, RefreshCw, Search, Shield, Clock } from 'lucide-react';

const SCOPE_STYLES = {
    Department: { icon: Building2, bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    Hostel: { icon: Home, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
};

function RepCard({ rep, onRemove }) {
    const scope = SCOPE_STYLES[rep.scope] || SCOPE_STYLES.Department;
    const ScopeIcon = scope.icon;

    return (
        <div className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-2xl p-5
                        shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]
                        hover:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.12)]
                        hover:-translate-y-0.5 transition-all duration-300
                        opacity-0 animate-slide-up">
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${scope.bg} ${scope.text}`}>
                        <ScopeIcon size={18} />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-gray-900">{rep.student_name || rep.student_roll_no}</p>
                        <p className="text-xs text-gray-500">{rep.student_roll_no} · Year {rep.year}</p>
                    </div>
                </div>
                <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${scope.bg} ${scope.text} ${scope.border} border`}>
                    {rep.scope}
                </span>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-3">
                    {rep.department_code && (
                        <span className="font-medium text-srec-primary">{rep.department_code}</span>
                    )}
                    {rep.appointed_by_name && (
                        <span>by {rep.appointed_by_name}</span>
                    )}
                </div>
                {rep.is_active && (
                    <button
                        onClick={() => onRemove(rep.id)}
                        className="flex items-center gap-1 text-red-500 hover:text-red-700
                                   hover:bg-red-50 px-2 py-1 rounded-lg transition-all duration-150"
                    >
                        <UserMinus size={12} /> Remove
                    </button>
                )}
            </div>
        </div>
    );
}

function AppointModal({ show, onClose, onAppoint }) {
    const [rollNo, setRollNo] = useState('');
    const [scope, setScope] = useState('Department');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    if (!show) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!rollNo.trim()) return;
        setLoading(true);
        setError('');
        try {
            await onAppoint({ student_roll_no: rollNo.trim(), scope });
            setRollNo('');
            onClose();
        } catch (err) {
            setError(err?.error || err?.detail || 'Failed to appoint representative');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="fixed inset-0 bg-black/30 animate-backdrop" onClick={onClose} />
            <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-modal-in">
                <h3 className="text-lg font-heading font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <UserPlus size={20} className="text-srec-primary" />
                    Appoint Representative
                </h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Student Roll Number</label>
                        <input
                            type="text"
                            value={rollNo}
                            onChange={e => setRollNo(e.target.value)}
                            placeholder="e.g. 23CS001"
                            className="w-full px-3 py-2.5 rounded-xl border border-srec-border bg-white
                                       text-sm text-gray-900 placeholder:text-gray-400
                                       focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary
                                       transition-all duration-150"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Scope</label>
                        <div className="flex gap-2">
                            {['Department', 'Hostel'].map(s => (
                                <button
                                    key={s}
                                    type="button"
                                    onClick={() => setScope(s)}
                                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5
                                               rounded-xl text-sm font-medium border transition-all duration-150
                                               ${scope === s
                                                   ? 'bg-srec-primary text-white border-srec-primary shadow-btn-primary'
                                                   : 'bg-white text-gray-600 border-srec-border hover:border-srec-primaryMuted'
                                               }`}
                                >
                                    {s === 'Department' ? <Building2 size={14} /> : <Home size={14} />}
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>

                    {error && (
                        <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl p-3">{error}</div>
                    )}

                    <div className="flex gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium
                                       border border-srec-border text-gray-600
                                       hover:bg-gray-50 transition-all duration-150"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !rollNo.trim()}
                            className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium
                                       bg-gradient-to-b from-srec-primary to-srec-primaryDark text-white
                                       shadow-btn-primary hover:shadow-btn-primary-hover
                                       hover:-translate-y-px active:translate-y-0 active:scale-[0.98]
                                       disabled:opacity-50 disabled:pointer-events-none
                                       transition-all duration-150"
                        >
                            {loading ? 'Appointing...' : 'Appoint'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default function AdminRepresentatives() {
    const [reps, setReps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAppoint, setShowAppoint] = useState(false);
    const [search, setSearch] = useState('');
    const [scopeFilter, setScopeFilter] = useState('All');
    // Petition weekly limit setting
    const [weeklyLimit, setWeeklyLimit] = useState(1);
    const [weeklyLimitInput, setWeeklyLimitInput] = useState('1');
    const [savingCooldown, setSavingCooldown] = useState(false);
    const [cooldownMsg, setCooldownMsg] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [repsData, settingsData] = await Promise.all([
                adminService.getRepresentatives({ active_only: true }),
                adminService.getSystemSettings().catch(() => null),
            ]);
            setReps(repsData.representatives || []);
            if (settingsData?.settings) {
                const wl = settingsData.settings.find(s => s.key === 'petition_weekly_limit');
                if (wl) {
                    setWeeklyLimit(parseInt(wl.value));
                    setWeeklyLimitInput(wl.value);
                }
            }
        } catch (err) {
            console.error('Failed to load representatives:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    const handleSaveCooldown = async () => {
        const val = parseInt(weeklyLimitInput);
        if (isNaN(val) || val < 0 || val > 20) {
            setCooldownMsg('Enter a number between 0 and 20');
            return;
        }
        setSavingCooldown(true);
        setCooldownMsg('');
        try {
            await adminService.updateSystemSetting('petition_weekly_limit', val);
            setWeeklyLimit(val);
            setCooldownMsg(val === 0 ? 'No limit (unlimited).' : `Set to ${val} per week.`);
            setTimeout(() => setCooldownMsg(''), 3000);
        } catch (err) {
            setCooldownMsg('Failed to save setting');
        } finally {
            setSavingCooldown(false);
        }
    };

    useEffect(() => { load(); }, [load]);

    const handleAppoint = async (body) => {
        await adminService.appointRepresentative(body);
        await load();
    };

    const handleRemove = async (repId) => {
        if (!confirm('Remove this student representative?')) return;
        try {
            await adminService.removeRepresentative(repId);
            await load();
        } catch (err) {
            console.error('Remove failed:', err);
        }
    };

    const filtered = reps.filter(r => {
        if (scopeFilter !== 'All' && r.scope !== scopeFilter) return false;
        if (search && !r.student_roll_no?.toLowerCase().includes(search.toLowerCase())
            && !r.student_name?.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    return (
        <div className="animate-fadeIn space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-srec-primarySoft to-emerald-100 text-srec-primary rounded-xl shadow-sm">
                        <Shield size={20} />
                    </div>
                    <div>
                        <h1 className="text-xl font-heading font-bold text-gray-900">Student Representatives</h1>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Appointed students who can create petitions · Max 3 per department per year
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={load}
                        className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-srec-primary
                                   border border-srec-border bg-white rounded-xl px-3 py-2
                                   shadow-btn hover:shadow-btn-hover hover:-translate-y-px
                                   active:scale-[0.97] transition-all duration-150">
                        <RefreshCw size={13} /> Refresh
                    </button>
                    <button onClick={() => setShowAppoint(true)}
                        className="flex items-center gap-1.5 text-xs text-white
                                   bg-gradient-to-b from-srec-primary to-srec-primaryDark
                                   rounded-xl px-4 py-2 shadow-btn-primary
                                   hover:shadow-btn-primary-hover hover:-translate-y-px
                                   active:scale-[0.97] transition-all duration-150">
                        <UserPlus size={13} /> Appoint
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px] max-w-xs">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search by name or roll no..."
                        className="w-full pl-9 pr-3 py-2 rounded-xl border border-srec-border bg-white
                                   text-sm text-gray-800 placeholder:text-gray-400
                                   focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary
                                   transition-all duration-150"
                    />
                </div>
                <div className="flex gap-1 bg-gray-50/80 p-1 rounded-xl border border-srec-borderLight">
                    {['All', 'Department', 'Hostel'].map(s => (
                        <button
                            key={s}
                            onClick={() => setScopeFilter(s)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150
                                ${scopeFilter === s
                                    ? 'bg-white text-gray-900 shadow-sm border border-gray-200/60'
                                    : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* Stats + Rate limit setting */}
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex gap-3 text-sm">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full">
                        <Building2 size={13} />
                        <span className="font-semibold">{reps.filter(r => r.scope === 'Department').length}</span> Dept reps
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full">
                        <Home size={13} />
                        <span className="font-semibold">{reps.filter(r => r.scope === 'Hostel').length}</span> Hostel reps
                    </div>
                </div>

                {/* Petition weekly limit setting */}
                <div className="ml-auto flex items-center gap-2 bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl px-4 py-2 shadow-sm">
                    <Clock size={13} className="text-srec-primary flex-shrink-0" />
                    <span className="text-xs font-medium text-gray-700 whitespace-nowrap">Petitions/week:</span>
                    <input
                        type="number"
                        min="0"
                        max="20"
                        value={weeklyLimitInput}
                        onChange={e => setWeeklyLimitInput(e.target.value)}
                        className="w-12 px-2 py-0.5 text-xs border border-gray-200 rounded-lg text-center
                                   focus:ring-1 focus:ring-srec-primary/30 focus:border-srec-primary outline-none"
                    />
                    <button
                        onClick={handleSaveCooldown}
                        disabled={savingCooldown}
                        className="text-xs px-2.5 py-1 rounded-lg bg-srec-primary text-white
                                   hover:bg-srec-primaryDark disabled:opacity-60 transition-colors"
                    >
                        {savingCooldown ? '...' : 'Save'}
                    </button>
                    {cooldownMsg && (
                        <span className={`text-[10px] ${cooldownMsg.includes('Failed') ? 'text-red-500' : 'text-green-600'}`}>
                            {cooldownMsg}
                        </span>
                    )}
                    {parseInt(weeklyLimitInput) === 0 && !cooldownMsg && (
                        <span className="text-[10px] text-amber-600">No limit</span>
                    )}
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
                </div>
            ) : filtered.length === 0 ? (
                <div className="text-center py-20 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-sm">
                    <div className="w-16 h-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <UserCheck size={28} className="text-gray-300" />
                    </div>
                    <h3 className="text-base font-heading font-semibold text-gray-900">No representatives found</h3>
                    <p className="text-gray-500 text-sm mt-1 max-w-xs mx-auto">
                        {search ? 'Try a different search term.' : 'Appoint student representatives to enable petition creation.'}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filtered.map((rep, idx) => (
                        <div key={rep.id} style={{ animationDelay: `${idx * 50}ms` }}>
                            <RepCard rep={rep} onRemove={handleRemove} />
                        </div>
                    ))}
                </div>
            )}

            <AppointModal
                show={showAppoint}
                onClose={() => setShowAppoint(false)}
                onAppoint={handleAppoint}
            />
        </div>
    );
}
