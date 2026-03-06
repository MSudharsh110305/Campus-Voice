import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { StatusBadge, PriorityBadge, EliteButton } from '../../../components/UI';
import {
    Clock,
    User,
    ShieldCheck,
    Tag,
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

// Top accent bar color by priority
const PRIORITY_ACCENT = {
    'Critical': 'bg-red-500',
    'High':     'bg-orange-400',
    'Medium':   'bg-amber-400',
    'Low':      'bg-gray-300',
};

export default function AdminComplaintCard({ complaint, token, authorities = [], onDelete, onReassign }) {
    const navigate = useNavigate();
    const [expanded, setExpanded] = useState(false);
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
            setActionMsg({ type: 'success', text: 'Reassigned' });
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

    const summary = complaint.rephrased_text || complaint.original_text || '';
    const TRUNCATE_LEN = 160;
    const isLong = summary.length > TRUNCATE_LEN;
    const truncated = expanded || !isLong ? summary : summary.slice(0, TRUNCATE_LEN) + '…';

    const accentColor = PRIORITY_ACCENT[complaint.priority] || PRIORITY_ACCENT['Low'];

    return (
        <div
            className="bg-white rounded-2xl border border-gray-100 hover:shadow-lg transition-all duration-200 cursor-pointer overflow-hidden flex flex-col"
            onClick={() => navigate(`/complaint/${complaint.id}`)}
        >
            {/* Top accent bar colored by priority */}
            <div className={`h-1 w-full ${accentColor}`} />

            <div className="p-4 flex gap-3 flex-1">
                {/* Main content */}
                <div className="flex-1 min-w-0 flex flex-col gap-3">
                {/* Row 1: StatusBadge + PriorityBadge + ID */}
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                        <StatusBadge status={complaint.status} />
                        <PriorityBadge priority={complaint.priority} />
                        {complaint.is_marked_as_spam && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-600 border border-red-200">
                                <AlertTriangle size={9} />Spam
                            </span>
                        )}
                        {complaint.is_marked_as_spam && complaint.has_disputed && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-50 text-orange-600 border border-orange-200">
                                <ShieldAlert size={9} />Disputed
                            </span>
                        )}
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono shrink-0">
                        #{complaint.id?.substring(0, 8)}
                    </span>
                </div>

                {/* Row 2: Student info */}
                <div className="bg-srec-primary/5 border border-srec-primary/10 rounded-xl px-3 py-2 space-y-1">
                    <div className="flex items-center gap-2 text-xs text-gray-600">
                        <User size={11} className="text-srec-primary shrink-0" />
                        <span className="font-semibold text-gray-900 truncate">{complaint.student_name || 'Unknown'}</span>
                        <span className="text-gray-300">·</span>
                        <span className="font-mono text-srec-primary font-bold text-[10px]">{complaint.student_roll_no || '—'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <ShieldCheck size={11} className="text-green-500 shrink-0" />
                        {complaint.assigned_authority_name
                            ? <span className="truncate">{complaint.assigned_authority_name}</span>
                            : <span className="italic text-gray-400">Unassigned</span>
                        }
                    </div>
                </div>


{/* Row 3: Complaint text */}
                <p className="text-sm text-gray-700 leading-relaxed font-semibold line-clamp-1">
                    {complaint.category_name || 'General Complaint'}
                </p>
                <div onClick={(e) => e.stopPropagation()}>
                    <p className="text-xs text-gray-500 leading-relaxed">
                        {truncated}
                    </p>
                    {isLong && (
                        <button
                            onClick={() => setExpanded(v => !v)}
                            className="text-[11px] text-srec-primary font-semibold mt-1 hover:underline"
                        >
                            {expanded ? 'Show less' : 'Read more'}
                        </button>
                    )}
                </div>

                {/* Row 4: Category + Visibility + Time */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-400 mt-auto">
                    {complaint.category_name && (
                        <div className="flex items-center gap-1">
                            <Tag size={10} />
                            <span>{complaint.category_name}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-1">
                        <Eye size={10} />
                        <span className={
                            complaint.visibility === 'Public' ? 'text-green-600' :
                            complaint.visibility === 'Department' ? 'text-blue-600' : 'text-gray-400'
                        }>
                            {complaint.visibility}
                        </span>
                    </div>
                    <div className="flex items-center gap-1 ml-auto">
                        <Clock size={10} />
                        <span>{format(new Date(complaint.submitted_at), 'MMM dd, h:mm a')}</span>
                    </div>
                </div>

                {/* Row 5: Actions */}
                <div className="border-t border-gray-100 pt-3 space-y-2" onClick={(e) => e.stopPropagation()}>
                    {actionMsg && (
                        <p className={`text-xs font-medium px-2 py-1 rounded ${actionMsg.type === 'success' ? 'text-green-700 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                            {actionMsg.text}
                        </p>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                        <EliteButton
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/complaint/${complaint.id}`)}
                            className="flex items-center gap-1 text-xs"
                        >
                            Details <ArrowRight size={12} />
                        </EliteButton>
                        {(onDelete || onReassign) && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setShowActions(v => !v); }}
                                className="text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
                            >
                                Manage
                            </button>
                        )}
                    </div>
                    {showActions && (
                        <div className="bg-gray-50 rounded-xl border border-gray-200 p-3 space-y-2">
                            {onReassign && authorities.length > 0 && (
                                <div className="flex items-center gap-2">
                                    <select
                                        value={selectedAuthority}
                                        onChange={e => setSelectedAuthority(e.target.value)}
                                        onClick={e => e.stopPropagation()}
                                        className="flex-1 text-xs bg-white border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-srec-primary/30"
                                    >
                                        <option value="">Select authority…</option>
                                        {authorities.map(a => (
                                            <option key={a.id} value={a.id}>{a.name} ({a.authority_type})</option>
                                        ))}
                                    </select>
                                    <button
                                        disabled={!selectedAuthority || isReassigning}
                                        onClick={handleReassign}
                                        className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-srec-primary text-white hover:bg-srec-primaryHover disabled:opacity-50 transition-colors"
                                    >
                                        <RefreshCw size={11} /> {isReassigning ? '…' : 'Reassign'}
                                    </button>
                                </div>
                            )}
                            {onDelete && (
                                <button
                                    disabled={isDeleting}
                                    onClick={handleDelete}
                                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors w-full justify-center"
                                >
                                    <Trash2 size={12} /> {isDeleting ? 'Deleting…' : 'Delete Complaint'}
                                </button>
                            )}
                        </div>
                    )}
                </div>
                </div>{/* end main content */}

                {/* Thumbnail image on right — compact, no horizontal expansion */}
                {complaint.has_image && token && (
                    <div className="w-20 h-20 flex-shrink-0 rounded-xl overflow-hidden bg-gray-100 self-start mt-0">
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
    );
}
