import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import { Skeleton, STATUS_COLORS } from '../../../components/UI';
import { AlertTriangle, CheckCircle, TrendingUp, Clock, ChevronRight, RefreshCw } from 'lucide-react';

const PRIORITY_COLORS = {
    Critical: 'bg-red-100 text-red-700 font-semibold',
    High: 'bg-orange-50 text-orange-700',
    Medium: 'bg-yellow-50 text-yellow-700',
    Low: 'bg-gray-100 text-gray-600',
};

const TABS = [
    { key: 'escalated', label: 'Escalated', icon: TrendingUp, iconBg: 'bg-purple-50 text-purple-600' },
    { key: 'critical', label: 'Critical', icon: AlertTriangle, iconBg: 'bg-red-50 text-red-600' },
    { key: 'overdue', label: 'Overdue', icon: Clock, iconBg: 'bg-amber-50 text-amber-600' },
];

function EscalationCard({ complaint, style }) {
    const navigate = useNavigate();
    const daysOld = complaint.submitted_at
        ? Math.floor((Date.now() - new Date(complaint.submitted_at).getTime()) / 86400000)
        : null;

    return (
        <div
            onClick={() => navigate(`/complaint/${complaint.id}`)}
            style={style}
            className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-2xl p-5
                       shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]
                       hover:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.12)]
                       hover:-translate-y-0.5 transition-all duration-300 cursor-pointer group
                       opacity-0 animate-slide-up"
        >
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex flex-wrap items-center gap-1.5">
                    <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[complaint.priority] || 'bg-gray-100 text-gray-600'}`}>
                        {complaint.priority}
                    </span>
                    <span className={`text-[11px] px-2.5 py-0.5 rounded-full ${
                        STATUS_COLORS?.[complaint.status]
                            ? `${STATUS_COLORS[complaint.status].bg} ${STATUS_COLORS[complaint.status].text}`
                            : 'bg-gray-100 text-gray-600'
                    }`}>
                        {complaint.status}
                    </span>
                    {complaint.was_escalated && (
                        <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-purple-50 text-purple-700 font-medium flex items-center gap-1">
                            <TrendingUp size={10} /> Escalated
                        </span>
                    )}
                </div>
                <ChevronRight size={16} className="text-gray-300 group-hover:text-srec-primary transition-colors flex-shrink-0 mt-0.5" />
            </div>

            <p className="text-sm text-gray-800 font-medium line-clamp-2 mb-3 leading-relaxed">
                {complaint.rephrased_text || complaint.original_text}
            </p>

            <div className="flex items-center justify-between text-xs text-gray-500 flex-wrap gap-1">
                <span className="font-medium">
                    {complaint.student_roll_no}
                    {complaint.category_name && <span className="ml-1.5 text-gray-400 font-normal">· {complaint.category_name}</span>}
                </span>
                <div className="flex items-center gap-2">
                    {complaint.assigned_authority_name && (
                        <span className="text-srec-primary font-medium">{complaint.assigned_authority_name}</span>
                    )}
                    {daysOld !== null && (
                        <span className={`flex items-center gap-0.5 ${daysOld >= 2 ? 'text-red-500 font-semibold' : 'text-gray-500'}`}>
                            <Clock size={10} /> {daysOld}d
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function AdminEscalations() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState(null);

    const load = async () => {
        try {
            setLoading(true);
            setError(null);
            const result = await adminService.getEscalations();
            setData(result);
            // Default to tab with highest count
            if (!activeTab) {
                const s = result?.summary || {};
                const counts = { escalated: s.escalated_count || 0, critical: s.critical_count || 0, overdue: s.overdue_count || 0 };
                const maxKey = Object.keys(counts).reduce((a, b) => counts[a] >= counts[b] ? a : b);
                setActiveTab(maxKey);
            }
        } catch (err) {
            setError('Failed to load escalation data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    if (loading) return (
        <div className="space-y-4 animate-fadeIn">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
        </div>
    );

    const summary = data?.summary || {};
    const totalIssues = (summary.escalated_count || 0) + (summary.critical_count || 0) + (summary.overdue_count || 0);

    const tabData = {
        escalated: { items: data?.escalated || [], count: summary.escalated_count || 0, empty: 'No escalated complaints' },
        critical: { items: data?.critical || [], count: summary.critical_count || 0, empty: 'No critical complaints right now' },
        overdue: { items: data?.overdue || [], count: summary.overdue_count || 0, empty: 'No overdue complaints right now' },
    };

    const current = tabData[activeTab] || tabData.escalated;

    return (
        <div className="animate-fadeIn space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-red-50 to-red-100 text-srec-danger rounded-xl shadow-sm">
                        <AlertTriangle size={20} />
                    </div>
                    <div>
                        <h1 className="text-xl font-heading font-bold text-gray-900">Escalations</h1>
                        <p className="text-xs text-gray-500 mt-0.5">
                            Complaints needing elevated attention · Auto-escalates after {summary.escalation_threshold_days ?? 2} days
                        </p>
                    </div>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-srec-primary
                               border border-srec-border bg-white rounded-xl px-3 py-2
                               shadow-btn hover:shadow-btn-hover hover:-translate-y-px
                               active:scale-[0.97] transition-all duration-150"
                >
                    <RefreshCw size={13} /> Refresh
                </button>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-sm text-red-600">{error}</div>
            )}

            {!error && totalIssues === 0 && (
                <div className="text-center py-24 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.06)]">
                    <div className="w-16 h-16 bg-gradient-to-br from-green-50 to-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
                        <CheckCircle size={32} className="text-green-500" />
                    </div>
                    <h3 className="text-lg font-heading font-semibold text-gray-900">All Clear</h3>
                    <p className="text-gray-500 text-sm mt-1 max-w-xs mx-auto">
                        No escalated, critical, or overdue complaints. System is running smoothly.
                    </p>
                </div>
            )}

            {!error && totalIssues > 0 && (
                <>
                    {/* Tab Bar */}
                    <div className="flex gap-1 bg-gray-50/80 p-1 rounded-xl border border-srec-borderLight">
                        {TABS.map(tab => {
                            const count = tabData[tab.key]?.count || 0;
                            const isActive = activeTab === tab.key;
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium
                                        transition-all duration-200
                                        ${isActive
                                            ? 'bg-white text-gray-900 shadow-md shadow-black/5 border border-gray-200/60'
                                            : 'text-gray-500 hover:text-gray-700 hover:bg-white/60'
                                        }`}
                                >
                                    <Icon size={14} className={isActive ? 'text-srec-primary' : ''} />
                                    <span>{tab.label}</span>
                                    <span className={`text-[11px] px-1.5 py-0.5 rounded-full min-w-[20px] text-center
                                        ${isActive
                                            ? 'bg-srec-primary text-white'
                                            : count > 0 ? 'bg-gray-200 text-gray-600' : 'bg-gray-100 text-gray-400'
                                        }`}>
                                        {count}
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    {/* Tab Content */}
                    <div key={activeTab} className="animate-fadeIn">
                        {current.count === 0 ? (
                            <div className="text-center py-16 bg-white/80 backdrop-blur-sm rounded-2xl border border-white/60 shadow-sm">
                                <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-3">
                                    <CheckCircle size={24} className="text-gray-300" />
                                </div>
                                <p className="text-gray-500 text-sm">{current.empty}</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {current.items.map((c, idx) => (
                                    <EscalationCard
                                        key={c.id}
                                        complaint={c}
                                        style={{ animationDelay: `${idx * 60}ms` }}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
