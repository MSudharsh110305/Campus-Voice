import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import adminService from '../../../services/admin.service';
import { Skeleton } from '../../../components/UI';
import { AlertTriangle, CheckCircle, TrendingUp, Clock, ChevronRight, RefreshCw } from 'lucide-react';

const STATUS_COLORS = {
    Raised: 'bg-blue-50 text-blue-700',
    'In Progress': 'bg-amber-50 text-amber-700',
    Resolved: 'bg-green-50 text-green-700',
    Closed: 'bg-gray-100 text-gray-600',
    Spam: 'bg-red-50 text-red-600',
};

const PRIORITY_COLORS = {
    Critical: 'bg-red-100 text-red-700 font-semibold',
    High: 'bg-orange-50 text-orange-700',
    Medium: 'bg-yellow-50 text-yellow-700',
    Low: 'bg-gray-100 text-gray-500',
};

function EscalationCard({ complaint }) {
    const navigate = useNavigate();
    const daysOld = complaint.submitted_at
        ? Math.floor((Date.now() - new Date(complaint.submitted_at).getTime()) / 86400000)
        : null;

    return (
        <div
            onClick={() => navigate(`/complaint/${complaint.id}`)}
            className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm hover:shadow-md hover:border-srec-primary/20 transition-all cursor-pointer group"
        >
            <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex flex-wrap items-center gap-1.5">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[complaint.priority] || 'bg-gray-100 text-gray-500'}`}>
                        {complaint.priority}
                    </span>
                    <span className={`text-[11px] px-2 py-0.5 rounded-full ${STATUS_COLORS[complaint.status] || 'bg-gray-100 text-gray-500'}`}>
                        {complaint.status}
                    </span>
                    {complaint.was_escalated && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-medium flex items-center gap-1">
                            <TrendingUp size={10} /> Escalated
                        </span>
                    )}
                </div>
                <ChevronRight size={16} className="text-gray-300 group-hover:text-srec-primary transition-colors flex-shrink-0 mt-0.5" />
            </div>

            <p className="text-sm text-gray-800 font-medium line-clamp-2 mb-2 leading-snug">
                {complaint.rephrased_text || complaint.original_text}
            </p>

            <div className="flex items-center justify-between text-xs text-gray-400 flex-wrap gap-1">
                <span>
                    {complaint.student_roll_no}
                    {complaint.category_name && <span className="ml-1 text-gray-300">· {complaint.category_name}</span>}
                </span>
                <div className="flex items-center gap-1">
                    {complaint.assigned_authority_name && (
                        <span className="text-srec-primary font-medium">{complaint.assigned_authority_name}</span>
                    )}
                    {daysOld !== null && (
                        <span className={`ml-2 flex items-center gap-0.5 ${daysOld >= 2 ? 'text-red-500 font-semibold' : 'text-gray-400'}`}>
                            <Clock size={10} /> {daysOld}d
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

function Section({ title, subtitle, icon: Icon, iconBg, count, children, emptyText }) {
    return (
        <div>
            <div className="flex items-center gap-3 mb-4">
                <div className={`p-2.5 rounded-xl ${iconBg}`}>
                    <Icon size={18} />
                </div>
                <div>
                    <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                        {title}
                        <span className="ml-1 text-sm font-semibold bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{count}</span>
                    </h2>
                    <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>
                </div>
            </div>

            {count === 0 ? (
                <div className="text-center py-10 bg-white rounded-xl border border-gray-100 text-gray-400 text-sm">
                    {emptyText}
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {children}
                </div>
            )}
        </div>
    );
}

export default function AdminEscalations() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = async () => {
        try {
            setLoading(true);
            setError(null);
            const result = await adminService.getEscalations();
            setData(result);
        } catch (err) {
            setError('Failed to load escalation data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    if (loading) return (
        <div className="space-y-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-2xl" />)}
        </div>
    );

    const summary = data?.summary || {};
    const totalIssues = (summary.escalated_count || 0) + (summary.critical_count || 0) + (summary.overdue_count || 0);

    return (
        <div className="animate-fadeIn space-y-8">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-red-50 text-srec-danger rounded-xl">
                        <AlertTriangle size={20} />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-gray-900">Escalations</h1>
                        <p className="text-xs text-gray-400 mt-0.5">
                            Complaints that need elevated attention · Auto-escalates after {summary.escalation_threshold_days ?? 2} days
                        </p>
                    </div>
                </div>
                <button
                    onClick={load}
                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-srec-primary border border-gray-200 rounded-xl px-3 py-2 transition-colors"
                >
                    <RefreshCw size={13} /> Refresh
                </button>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-100 rounded-xl p-4 text-sm text-red-600">{error}</div>
            )}

            {!error && totalIssues === 0 && (
                <div className="text-center py-24 bg-white rounded-2xl border border-gray-100 shadow-sm">
                    <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle size={32} className="text-green-500" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">All Clear</h3>
                    <p className="text-gray-400 text-sm mt-1 max-w-xs mx-auto">
                        No escalated, critical, or overdue complaints. System is running smoothly.
                    </p>
                </div>
            )}

            {/* Section 1: Already Escalated */}
            {data && (summary.escalated_count || 0) > 0 && (
                <Section
                    title="Escalated Complaints"
                    subtitle="Moved to a higher authority"
                    icon={TrendingUp}
                    iconBg="bg-purple-50 text-purple-600"
                    count={summary.escalated_count || 0}
                    emptyText=""
                >
                    {data.escalated.map(c => <EscalationCard key={c.id} complaint={c} />)}
                </Section>
            )}

            {/* Section 2: Critical (not yet escalated) */}
            {data && (summary.critical_count || 0) > 0 && (
                <Section
                    title="Critical Issues"
                    subtitle="High-severity — act immediately"
                    icon={AlertTriangle}
                    iconBg="bg-red-50 text-srec-danger"
                    count={summary.critical_count || 0}
                    emptyText=""
                >
                    {data.critical.map(c => <EscalationCard key={c.id} complaint={c} />)}
                </Section>
            )}

            {/* Section 3: Overdue */}
            {data && (summary.overdue_count || 0) > 0 && (
                <Section
                    title="Overdue Complaints"
                    subtitle={`Open > ${summary.escalation_threshold_days ?? 2} days`}
                    icon={Clock}
                    iconBg="bg-amber-50 text-amber-600"
                    count={summary.overdue_count || 0}
                    emptyText=""
                >
                    {data.overdue.map(c => <EscalationCard key={c.id} complaint={c} />)}
                </Section>
            )}
        </div>
    );
}
