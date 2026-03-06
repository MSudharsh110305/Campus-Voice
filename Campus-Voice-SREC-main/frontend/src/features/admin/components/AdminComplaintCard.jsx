import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { StatusBadge, PriorityBadge } from '../../../components/UI';
import {
    Clock,
    User,
    ShieldCheck,
    Eye,
    AlertTriangle,
    ArrowRight,
    Trash2,
    RefreshCw,
    ShieldAlert,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function AuthenticatedImage({ complaintId, token, className = '', thumbnail = false }) {
    const [src, setSrc] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        if (!complaintId || !token) return;
        let objectUrl = null;
        setLoading(true);
        setError(false);
        const url = `/api/complaints/${complaintId}/image${thumbnail ? '?thumbnail=true' : ''}`;
        fetch(url, { headers: { Authorization: `Bearer ${token}` } })
            .then(res => {
                if (!res.ok) throw new Error('Failed');
                return res.blob();
            })
            .then(blob => {
                objectUrl = URL.createObjectURL(blob);
                setSrc(objectUrl);
            })
            .catch(() => setError(true))
            .finally(() => setLoading(false));
        return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
    }, [complaintId, token, thumbnail]);

    if (loading) return <div className={`animate-pulse bg-gray-100 rounded-xl ${className}`} />;
    if (error) return null;
    return <img src={src} alt="Complaint" className={className} />;
}

const PRIORITY_ACCENT = {
    'Critical': 'bg-red-500',
    'High':     'bg-orange-400',
    'Medium':   'bg-amber-400',
    'Low':      'bg-gray-300',
};

export default function AdminComplaintCard({ complaint, token, authorities = [], onDelete, onReassign }) {
    const navigate = useNavigate();
    const [showActions, setShowActions] = useState(false);
    const [selectedAuthority, setSelectedAuthority] = useState('');
    const [isReassigning, setIsReassigning] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [actionMsg, setActionMsg] = useState(null);

    const handleReassign = async (e) => {
        e.stopPropagation();
        if (!selectedAuthority) return;
        setIsReassigning(true);
        try {
            await onReassign(complaint.id, parseInt(selectedAuthority));
            setActionMsg({ type: 'success', text: 'Reassigned successfully' });
            setTimeout(() => setActionMsg(null), 2500);
        } catch (err) {
            setActionMsg({ type: 'error', text: err.message || 'Failed' });
            setTimeout(() => setActionMsg(null), 3000);
        } finally {
            setIsReassigning(false);
        }
    };

    const handleDelete = async (e) => {
        e.stopPropagation();
        if (!window.confirm('Permanently delete this complaint? This cannot be undone.')) return;
        setIsDeleting(true);
        try {
            await onDelete(complaint.id);
        } catch (err) {
            setActionMsg({ type: 'error', text: err.message || 'Delete failed' });
            setTimeout(() => setActionMsg(null), 3000);
            setIsDeleting(false);
        }
    };

    const bodyText = complaint.rephrased_text || complaint.original_text || '';
    const accentColor = PRIORITY_ACCENT[complaint.priority] || PRIORITY_ACCENT['Low'];
    const isSpam = complaint.is_marked_as_spam;
    const isDisputed = isSpam && complaint.has_disputed;

    return (
        <div
            className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer overflow-hidden flex flex-col"
            onClick={() => navigate(`/complaint/${complaint.id}`)}
        >
            {/* Priority accent bar */}
            <div className={`h-0.5 w-full ${accentColor}`} />

            {/* Card body */}
            <div className="p-4 flex flex-col gap-3 flex-1">

                {/* ── Row 1: Header — badges left, ID + image right ── */}
                <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                        {/* Status + Priority always on one line */}
                        <div className="flex items-center gap-1.5">
                            <StatusBadge status={complaint.status} />
                            <PriorityBadge priority={complaint.priority} />
                        </div>
                        {/* Spam + Disputed tags on a separate line — only when present */}
                        {isSpam && (
                            <div className="flex items-center gap-1.5 mt-1.5">
                                <span className="inline-flex items-center gap-1 px-1.5 py-px rounded text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">
                                    <AlertTriangle size={8} />Spam
                                </span>
                                {isDisputed && (
                                    <span className="inline-flex items-center gap-1 px-1.5 py-px rounded text-[10px] font-semibold bg-orange-50 text-orange-600 border border-orange-200">
                                        <ShieldAlert size={8} />Disputed
                                    </span>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Right side: ID + optional thumbnail stacked */}
                    <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                        <span className="text-[10px] text-gray-400 font-mono">#{complaint.id?.substring(0, 8)}</span>
                        {complaint.has_image && token && (
                            <div className="w-14 h-14 rounded-lg overflow-hidden bg-gray-100 border border-gray-200">
                                <AuthenticatedImage
                                    complaintId={complaint.id}
                                    token={token}
                                    thumbnail={true}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Row 2: Student + Authority info ── */}
                <div className="rounded-xl bg-gray-50 border border-gray-100 px-3 py-2 space-y-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                        <User size={10} className="text-srec-primary shrink-0" />
                        <span className="text-xs font-semibold text-gray-900 truncate">
                            {complaint.student_name || 'Unknown'}
                        </span>
                        {complaint.student_roll_no && (
                            <>
                                <span className="text-gray-300 text-xs">·</span>
                                <span className="text-[10px] font-mono text-srec-primary font-bold shrink-0">
                                    {complaint.student_roll_no}
                                </span>
                            </>
                        )}
                    </div>
                    <div className="flex items-center gap-1.5 min-w-0">
                        <ShieldCheck size={10} className="text-green-500 shrink-0" />
                        <span className="text-[11px] text-gray-500 truncate">
                            {complaint.assigned_authority_name
                                ? complaint.assigned_authority_name
                                : <span className="italic text-gray-400">Unassigned</span>
                            }
                        </span>
                    </div>
                </div>

                {/* ── Row 3: Category + complaint body ── */}
                <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-semibold text-srec-primary uppercase tracking-wider mb-1">
                        {complaint.category_name || 'General'}
                    </p>
                    <p className="text-xs text-gray-700 leading-relaxed line-clamp-2">
                        {bodyText || 'No description provided.'}
                    </p>
                </div>

                {/* ── Row 4: Meta footer — visibility + time ── */}
                <div className="flex items-center gap-2 text-[10px] text-gray-400 mt-auto">
                    <Eye size={9} />
                    <span className={
                        complaint.visibility === 'Public' ? 'text-green-600 font-medium' :
                        complaint.visibility === 'Department' ? 'text-blue-600 font-medium' : ''
                    }>
                        {complaint.visibility || 'Private'}
                    </span>
                    <span className="ml-auto flex items-center gap-1">
                        <Clock size={9} />
                        {format(new Date(complaint.submitted_at), 'MMM dd, h:mm a')}
                    </span>
                </div>

                {/* ── Row 5: Action buttons ── */}
                <div className="border-t border-gray-100 pt-3 space-y-2" onClick={(e) => e.stopPropagation()}>
                    {actionMsg && (
                        <p className={`text-xs font-medium px-2 py-1 rounded-lg ${actionMsg.type === 'success' ? 'text-green-700 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                            {actionMsg.text}
                        </p>
                    )}
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => navigate(`/complaint/${complaint.id}`)}
                            className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 px-3 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors font-medium"
                        >
                            Details <ArrowRight size={11} />
                        </button>
                        {(onDelete || onReassign) && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setShowActions(v => !v); }}
                                className={`flex-1 text-xs py-1.5 px-3 rounded-lg border transition-colors font-medium ${showActions ? 'border-srec-primary/30 bg-srec-primary/5 text-srec-primary' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}
                            >
                                {showActions ? 'Close' : 'Manage'}
                            </button>
                        )}
                    </div>
                    {showActions && (
                        <div className="bg-gray-50 rounded-xl border border-gray-100 p-2.5 space-y-2">
                            {onReassign && authorities.length > 0 && (
                                <div className="space-y-1.5">
                                    <select
                                        value={selectedAuthority}
                                        onChange={e => setSelectedAuthority(e.target.value)}
                                        onClick={e => e.stopPropagation()}
                                        className="w-full text-xs bg-white border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-srec-primary/30"
                                    >
                                        <option value="">Select authority…</option>
                                        {authorities.map(a => (
                                            <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>
                                        ))}
                                    </select>
                                    <button
                                        disabled={!selectedAuthority || isReassigning}
                                        onClick={handleReassign}
                                        className="w-full flex items-center justify-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-srec-primary text-white hover:bg-srec-primaryHover disabled:opacity-50 transition-colors"
                                    >
                                        <RefreshCw size={10} /> {isReassigning ? 'Reassigning…' : 'Reassign'}
                                    </button>
                                </div>
                            )}
                            {onDelete && (
                                <button
                                    disabled={isDeleting}
                                    onClick={handleDelete}
                                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors w-full justify-center"
                                >
                                    <Trash2 size={11} /> {isDeleting ? 'Deleting…' : 'Delete Complaint'}
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
