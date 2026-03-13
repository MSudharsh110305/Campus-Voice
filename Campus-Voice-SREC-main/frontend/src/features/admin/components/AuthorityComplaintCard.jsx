import React, { useState, useEffect } from 'react';
import { StatusBadge, PriorityBadge, EliteButton } from '../../../components/UI';
import { format } from 'date-fns';
import { MessageSquare, ThumbsUp, Image as ImageIcon, ArrowUpCircle, MessageCircle, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { VALID_STATUS_TRANSITIONS } from '../../../utils/constants';

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

const AuthorityComplaintCard = ({ complaint, onStatusUpdate, onPostUpdate, onEscalate, onAttach, token }) => {
    const navigate = useNavigate();
    const [expanded, setExpanded] = useState(false);
    const validTransitions = VALID_STATUS_TRANSITIONS[complaint.status] || [];
    const canTransition = validTransitions.length > 0;
    const isClosed = complaint.status === 'Closed' || complaint.status === 'Spam';
    const bodyText = complaint.rephrased_text || complaint.original_text || '';
    const TRUNCATE_LEN = 140;
    const isLong = bodyText.length > TRUNCATE_LEN;

    return (
        <div
            className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md cursor-pointer"
            onClick={() => navigate(`/complaint/${complaint.id}`)}
        >
            {/* Complaint image if present */}
            {complaint.has_image && token && (
                <AuthenticatedImage
                    complaintId={complaint.id}
                    token={token}
                    thumbnail={true}
                    className="w-full h-32 object-cover"
                />
            )}

            <div className="p-4">
            {/* Top: student info + date */}
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                    <p className="text-xs text-gray-500 font-medium truncate">
                        {complaint.student_name || complaint.student_roll_no || 'Anonymous'}
                        {complaint.student_roll_no && complaint.student_name && (
                            <span className="text-gray-400 ml-1">· {complaint.student_roll_no}</span>
                        )}
                    </p>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">
                    {complaint.submitted_at
                        ? format(new Date(complaint.submitted_at), 'MMM dd, h:mm a')
                        : 'Unknown date'}
                </span>
            </div>

            {/* Category chip */}
            {complaint.category_name && (
                <div className="mb-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-srec-primary/10 text-srec-primary border border-srec-primary/20">
                        {complaint.category_name}
                    </span>
                </div>
            )}

            {/* Content */}
            <div className="mb-3" onClick={(e) => e.stopPropagation()}>
                <p className="text-sm text-gray-700 leading-relaxed font-medium">
                    {expanded || !isLong ? bodyText : bodyText.slice(0, TRUNCATE_LEN) + '…'}
                </p>
                {isLong && (
                    <button
                        onClick={() => setExpanded(v => !v)}
                        className="text-xs text-srec-primary font-semibold mt-1 hover:underline"
                    >
                        {expanded ? 'Show less' : 'Read more'}
                    </button>
                )}
            </div>

            {/* Status + Priority row */}
            <div className="flex items-center gap-2 mb-3">
                <StatusBadge status={complaint.status} />
                <PriorityBadge priority={complaint.priority} />
                {complaint.is_marked_as_spam && complaint.has_disputed && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-50 text-orange-600 border border-orange-200">
                        <ShieldAlert size={9} />Disputed
                    </span>
                )}
                {complaint.has_image && (
                    <span className="ml-auto">
                        <ImageIcon size={14} className="text-gray-400" />
                    </span>
                )}
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 pt-3 border-t border-gray-50 flex-wrap min-w-0">
                {canTransition && (
                    <EliteButton
                        size="sm"
                        variant="primary"
                        onClick={(e) => {
                            e.stopPropagation();
                            onStatusUpdate(e, complaint.id, complaint.status);
                        }}
                    >
                        Update Status
                    </EliteButton>
                )}

                {!isClosed && onPostUpdate && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onPostUpdate(e, complaint.id);
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium border border-gray-200 text-gray-600 rounded-lg hover:border-srec-primary hover:text-srec-primary transition-all duration-200"
                    >
                        <MessageCircle size={12} />
                        Post Update
                    </button>
                )}

                {!isClosed && onEscalate && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onEscalate(e, complaint.id);
                        }}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium border border-gray-200 text-gray-600 rounded-lg hover:border-amber-400 hover:text-amber-600 transition-all duration-200"
                    >
                        <ArrowUpCircle size={12} />
                        Escalate
                    </button>
                )}


                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/complaint/${complaint.id}`);
                    }}
                    className="ml-auto text-xs text-gray-400 hover:text-srec-primary transition-colors font-medium"
                >
                    View details
                </button>
            </div>
            </div>
        </div>
    );
};

export default AuthorityComplaintCard;
