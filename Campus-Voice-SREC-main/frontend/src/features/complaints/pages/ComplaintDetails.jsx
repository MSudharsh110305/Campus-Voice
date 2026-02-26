import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TopNav } from '../../../components/Navbars';
import { useAuth } from '../../../context/AuthContext';
import complaintService from '../../../services/complaint.service';
import authorityService from '../../../services/authority.service';
import { VOTE_TYPES, COMPLAINT_CATEGORIES } from '../../../utils/constants';
import { ThumbsUp, ThumbsDown, FileX, Clock, History, CheckCircle2, AlertCircle, ShieldAlert, FileText, ChevronRight, ShieldCheck, Send, MessageSquareWarning } from 'lucide-react';
import { Skeleton, Card, Badge, Button } from '../../../components/UI';
import { format } from 'date-fns';

export default function ComplaintDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [complaint, setComplaint] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [userVote, setUserVote] = useState(null);
    const [isVoting, setIsVoting] = useState(false);
    const [voteError, setVoteError] = useState(null);

    const showVoteError = (msg) => {
        setVoteError(msg);
        setTimeout(() => setVoteError(null), 4000);
    };

    const [imageUrl, setImageUrl] = useState(null);
    const [imageLoading, setImageLoading] = useState(false);
    const [history, setHistory] = useState([]);
    const [timeline, setTimeline] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingTimeline, setLoadingTimeline] = useState(false);

    // Authority/Admin action panel state
    const [newStatus, setNewStatus] = useState('');
    const [statusReason, setStatusReason] = useState('');
    const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
    const [statusUpdateMsg, setStatusUpdateMsg] = useState(null);
    const [updateNote, setUpdateNote] = useState('');
    const [updateTitle, setUpdateTitle] = useState('');
    const [isPostingUpdate, setIsPostingUpdate] = useState(false);
    const [postUpdateMsg, setPostUpdateMsg] = useState(null);

    // Spam dispute state
    const [disputeReason, setDisputeReason] = useState('');
    const [isDisputing, setIsDisputing] = useState(false);
    const [disputeMsg, setDisputeMsg] = useState(null);

    const fetchHistory = async () => {
        try {
            setLoadingHistory(true);
            const data = await complaintService.getComplaintStatusHistory(id);
            setHistory(Array.isArray(data) ? data : data?.history || []);
        } catch (error) {
            console.log("Could not fetch status history:", error.message);
            setHistory([]);
        } finally {
            setLoadingHistory(false);
        }
    };

    const fetchTimeline = async () => {
        try {
            setLoadingTimeline(true);
            const data = await complaintService.getComplaintTimeline(id);
            setTimeline(Array.isArray(data) ? data : data?.timeline || []);
        } catch (error) {
            console.log("Could not fetch timeline:", error.message);
            setTimeline([]);
        } finally {
            setLoadingTimeline(false);
        }
    };

    useEffect(() => {
        let active = true;
        if (complaint?.has_image) {
            setImageLoading(true);
            complaintService.fetchImage(id, false)
                .then(url => {
                    if (active) setImageUrl(url);
                })
                .catch(err => {
                    console.log("Could not fetch image:", err.message);
                    if (active) setImageUrl(null);
                })
                .finally(() => {
                    if (active) setImageLoading(false);
                });
        }

        return () => {
            active = false;
            if (imageUrl) {
                URL.revokeObjectURL(imageUrl);
            }
        };
    }, [id, complaint?.has_image]);

    useEffect(() => {
        const fetchDetails = async () => {
            try {
                setLoading(true);

                // Use authority endpoint for Authority/Admin, student endpoint for students
                const isAuthorityOrAdmin = user?.role === 'Authority' || user?.role === 'Admin';
                const data = isAuthorityOrAdmin
                    ? await authorityService.getComplaintDetails(id)
                    : await complaintService.getComplaintDetails(id);
                setComplaint(data);

                // Only fetch vote status for students
                if (!isAuthorityOrAdmin) {
                    setTimeout(async () => {
                        try {
                            const voteData = await complaintService.getMyVote(id);
                            setUserVote(voteData.has_voted ? voteData.vote_type : null);
                        } catch (voteError) {
                            console.log("Could not fetch vote status:", voteError.message);
                        }
                    }, 300);
                }

                // Fetch history and timeline with delays
                setTimeout(fetchHistory, 500);
                setTimeout(fetchTimeline, 700);
            } catch (err) {
                console.error('❌ Failed to fetch complaint details:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        if (id) {
            fetchDetails();
        }
    }, [id]);

    const handleVote = async (type) => {
        if (!user?.roll_no) {
            showVoteError("Please login to vote");
            return;
        }
        if (isVoting) return;

        setIsVoting(true);

        // Store previous state for rollback
        const prevVote = userVote;
        const prevComplaint = { ...complaint };

        // Optimistic UI update
        const isRemoving = userVote === type;
        let newUpvotes = complaint.upvotes || 0;
        let newDownvotes = complaint.downvotes || 0;

        if (isRemoving) {
            // Removing vote
            if (type === VOTE_TYPES.UPVOTE) newUpvotes--;
            else newDownvotes--;
            setUserVote(null);
        } else {
            // Adding or changing vote
            if (prevVote === VOTE_TYPES.UPVOTE) newUpvotes--;
            if (prevVote === VOTE_TYPES.DOWNVOTE) newDownvotes--;
            if (type === VOTE_TYPES.UPVOTE) newUpvotes++;
            else newDownvotes++;
            setUserVote(type);
        }

        setComplaint({
            ...complaint,
            upvotes: Math.max(0, newUpvotes),
            downvotes: Math.max(0, newDownvotes),
            net_votes: newUpvotes - newDownvotes
        });

        try {
            let response;

            // If clicking same vote type, remove vote
            if (isRemoving) {
                response = await complaintService.removeVote(id);
            } else {
                // Add or change vote
                response = await complaintService.voteOnComplaint(id, type);
            }

            // Update with actual backend response
            setComplaint({
                ...complaint,
                upvotes: response.upvotes,
                downvotes: response.downvotes,
                net_votes: response.upvotes - response.downvotes,
                priority: response.priority
            });
            setUserVote(response.user_vote);

        } catch (error) {
            console.error("Vote failed:", error);

            // Rollback optimistic update
            setComplaint(prevComplaint);
            setUserVote(prevVote);

            // Show user-friendly error message
            const errMsg = error?.response?.data?.error || error?.response?.data?.detail || '';
            const errorMsg = (errMsg || error.message || '').toLowerCase();
            if (errMsg.toLowerCase().includes('own') || errMsg.toLowerCase().includes('cannot vote') || error?.response?.status === 403 || error?.status === 403) {
                showVoteError("You can't vote on your own complaint");
            } else if (errorMsg.includes('greenlet') || errorMsg.includes('sqlalchemy')) {
                showVoteError("Server is temporarily busy. Please try again in a moment.");
            } else if (errorMsg.includes('rate limit')) {
                showVoteError("Too many requests. Please wait a moment and try again.");
            } else {
                showVoteError("Vote could not be registered. Please try again.");
            }
        } finally {
            setIsVoting(false);
        }
    };

    // Handler: authority/admin status update
    const handleStatusUpdate = async (e) => {
        e.preventDefault();
        if (!newStatus) return;
        setIsUpdatingStatus(true);
        setStatusUpdateMsg(null);
        try {
            await authorityService.updateComplaintStatus(id, newStatus, statusReason || null);
            setComplaint(prev => ({ ...prev, status: newStatus }));
            setStatusUpdateMsg({ type: 'success', text: `Status updated to "${newStatus}" successfully.` });
            setNewStatus('');
            setStatusReason('');
            setTimeout(fetchHistory, 500);
        } catch (err) {
            const msg = err?.response?.data?.detail || err.message || 'Failed to update status';
            setStatusUpdateMsg({ type: 'error', text: typeof msg === 'object' ? JSON.stringify(msg) : msg });
        } finally {
            setIsUpdatingStatus(false);
        }
    };

    // Handler: authority/admin post update note
    const handlePostUpdate = async (e) => {
        e.preventDefault();
        if (!updateNote.trim()) return;
        setIsPostingUpdate(true);
        setPostUpdateMsg(null);
        try {
            await authorityService.postUpdate(id, updateTitle || 'Update', updateNote);
            setPostUpdateMsg({ type: 'success', text: 'Update posted. Student has been notified.' });
            setUpdateTitle('');
            setUpdateNote('');
        } catch (err) {
            const msg = err?.response?.data?.detail || err.message || 'Failed to post update';
            setPostUpdateMsg({ type: 'error', text: typeof msg === 'object' ? JSON.stringify(msg) : msg });
        } finally {
            setIsPostingUpdate(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50">
                <TopNav />
                <div className="max-w-3xl mx-auto p-6 pt-10">
                    <Skeleton className="h-64 rounded-xl mb-6" />
                    <Skeleton className="h-10 w-1/3 mb-4" />
                    <Skeleton className="h-4 w-full mb-2" />
                    <Skeleton className="h-4 w-2/3" />
                </div>
            </div>
        );
    }

    if (error || !complaint) {
        const isRateLimitError = error && error.toLowerCase().includes('rate limit');

        return (
            <div className="min-h-screen bg-gray-50">
                <TopNav />
                <div className="max-w-3xl mx-auto p-6 pt-20 text-center">
                    {isRateLimitError ? (
                        <>
                            <div className="mb-4 text-6xl">⏱️</div>
                            <h2 className="text-xl font-bold text-gray-800 mb-2">Too Many Requests</h2>
                            <p className="text-gray-500 mb-6">
                                The server is experiencing high traffic. Please wait a moment and try again.
                            </p>
                            <div className="flex gap-3 justify-center">
                                <button
                                    onClick={() => window.location.reload()}
                                    className="px-4 py-2 bg-srec-primary text-white rounded-lg hover:bg-srec-primaryHover transition"
                                >
                                    Retry
                                </button>
                                <button
                                    onClick={() => navigate(-1)}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                                >
                                    Go Back
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <h2 className="text-xl font-bold text-gray-800 mb-2">Complaint Not Found</h2>
                            <p className="text-gray-500 mb-6">{error || "The complaint you're looking for doesn't exist or you don't have permission to view it."}</p>
                            <button
                                onClick={() => navigate(-1)}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                            >
                                Go Back
                            </button>
                        </>
                    )}
                </div>
            </div>
        );
    }

    const isAdmin = user?.role === 'Admin';
    const isAuthorityOrAdmin = user?.role === 'Authority' || user?.role === 'Admin';
    const isOwner = user?.roll_no && complaint.student_roll_no && user.roll_no === complaint.student_roll_no;

    // Sanitize timeline descriptions to protect student identity
    const sanitizeDescription = (description) => {
        if (!description || isAuthorityOrAdmin) return description;

        // Replace patterns like "Complaint raised by [Name]" with "Complaint raised by Student"
        return description
            .replace(/raised by [A-Za-z\s]+$/i, 'raised by Student')
            .replace(/submitted by [A-Za-z\s]+$/i, 'submitted by Student')
            .replace(/created by [A-Za-z\s]+$/i, 'created by Student')
            .replace(/by [A-Z][a-z]+ [A-Z][a-z]+/g, 'by Student');
    };

    // Sanitize names in timeline updated_by field
    const sanitizeName = (name) => {
        if (!name || isAuthorityOrAdmin) return name;

        // If it looks like a student name (contains spaces, proper case), hide it
        if (/^[A-Z][a-z]+ [A-Z][a-z]+/.test(name)) {
            return 'Student';
        }
        return name; // Keep authority/admin names
    };

    // Status banner background
    const statusBannerClass = {
        'Raised':      'bg-blue-50 border-blue-100 text-blue-800',
        'In Progress': 'bg-amber-50 border-amber-100 text-amber-800',
        'Resolved':    'bg-green-50 border-green-100 text-green-800',
        'Closed':      'bg-gray-100 border-gray-200 text-gray-700',
        'Spam':        'bg-red-50 border-red-100 text-red-700',
    }[complaint.status] || 'bg-blue-50 border-blue-100 text-blue-800';

    return (
        <div className="min-h-screen bg-srec-background">
            <TopNav />

            <div className="animate-fadeIn max-w-3xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">
                <button
                    onClick={() => navigate(-1)}
                    className="mb-4 flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-srec-primary transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                    Back
                </button>

                {/* Hero status banner */}
                <div className={`w-full px-4 py-3 rounded-xl border mb-4 flex items-center justify-between ${statusBannerClass}`}>
                    <span className="text-sm font-semibold">Status: {complaint.status || 'Raised'}</span>
                    {complaint.submitted_at && (
                        <span className="text-xs opacity-70">
                            {new Date(complaint.submitted_at || complaint.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                        </span>
                    )}
                </div>

                <Card className="overflow-hidden shadow-neu-flat">
                    {complaint?.has_image && (
                        <div className="relative bg-gray-100">
                            {imageLoading ? (
                                <Skeleton className="w-full h-64 sm:h-80" />
                            ) : imageUrl ? (
                                <>
                                    <img
                                        src={imageUrl}
                                        alt={complaint.title}
                                        className="w-full h-64 sm:h-80 object-cover rounded-2xl"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none"></div>
                                </>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-64 sm:h-96 text-gray-400">
                                    <FileX size={48} strokeWidth={1.5} />
                                    <span className="text-sm mt-2">Image failed to load</span>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="p-5 sm:p-8">

                        {/* Category & Metadata row (compact) */}
                        <div className="flex flex-wrap items-center gap-2 mb-5 text-sm">
                            <Badge type={complaint.category_name || COMPLAINT_CATEGORIES[complaint.category_id]} variant="category">
                                {complaint.category_name || COMPLAINT_CATEGORIES[complaint.category_id] || 'General'}
                            </Badge>
                            {complaint.department_code && (
                                <Badge variant="category" className="bg-blue-50 text-blue-700 border-blue-200">
                                    {complaint.department_code}
                                </Badge>
                            )}
                            {complaint.cross_department && (
                                <Badge variant="category" className="bg-orange-50 text-orange-700 border-orange-200">
                                    Cross-Department
                                </Badge>
                            )}
                            <span className="text-gray-300">·</span>
                            <span className="text-xs text-gray-500">
                                <span className="font-medium">{complaint.visibility}</span> visibility
                            </span>
                        </div>

                        {/* Content display based on ownership */}
                        <div className="mb-10">
                            {isOwner ? (
                                <>
                                    {/* Owner view: Show both original text and AI rephrased text */}
                                    {complaint.original_text && (
                                        <div className="mb-6">
                                            <div className="mb-2 uppercase tracking-wider text-xs font-bold text-gray-500">
                                                Your Submitted Complaint
                                            </div>
                                            <div className="prose prose-green max-w-none text-gray-600 leading-relaxed whitespace-pre-wrap bg-gray-50 rounded-lg p-4 border border-gray-100">
                                                {complaint.original_text}
                                            </div>
                                        </div>
                                    )}
                                    {complaint.rephrased_text && (
                                        <div>
                                            <div className="mb-2 uppercase tracking-wider text-xs font-bold text-srec-primary flex items-center gap-1.5">
                                                <span>✨ AI Rephrased Summary</span>
                                            </div>
                                            <div className="prose prose-green max-w-none text-gray-600 leading-relaxed whitespace-pre-wrap">
                                                {complaint.rephrased_text}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : isAuthorityOrAdmin ? (
                                <>
                                    {/* Admin/Authority view: show both original + rephrased */}
                                    {complaint.original_text && (
                                        <div className="mb-4">
                                            <div className="mb-1.5 text-xs font-bold text-gray-400 uppercase tracking-wider">Original Text</div>
                                            <div className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap bg-gray-50 rounded-lg p-3 border border-gray-100">
                                                {complaint.original_text}
                                            </div>
                                        </div>
                                    )}
                                    {complaint.rephrased_text && complaint.rephrased_text !== complaint.original_text && (
                                        <div>
                                            <div className="mb-1.5 text-xs font-bold text-srec-primary uppercase tracking-wider flex items-center gap-1">✨ AI Summary</div>
                                            <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                                                {complaint.rephrased_text}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <>
                                    {/* Public view: Only show AI rephrased text */}
                                    {complaint.rephrased_text && (
                                        <div className="mb-2 uppercase tracking-wider text-xs font-bold text-srec-primary flex items-center gap-1.5">
                                            <span>✨ AI Reviewed Complaint</span>
                                        </div>
                                    )}
                                    <div className="prose prose-green max-w-none text-gray-600 leading-relaxed whitespace-pre-wrap">
                                        {complaint.rephrased_text || 'No description available.'}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* ── Spam Dispute (owner only) ───────────────────────── */}
                        {isOwner && (complaint.is_marked_as_spam || complaint.status === 'Spam') && (
                            <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-xl">
                                <div className="flex items-start gap-3 mb-3">
                                    <MessageSquareWarning size={18} className="text-red-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <p className="text-sm font-semibold text-red-700">Your complaint was marked as spam</p>
                                        <p className="text-xs text-red-500 mt-0.5">
                                            {complaint.spam_reason || 'Our system detected this as spam.'}
                                        </p>
                                    </div>
                                </div>
                                {disputeMsg ? (
                                    <div className={`text-xs px-3 py-2 rounded-lg font-medium ${disputeMsg.ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                        {disputeMsg.text}
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <p className="text-xs text-red-600 font-medium">Think this is a mistake? Dispute it:</p>
                                        <textarea
                                            value={disputeReason}
                                            onChange={e => setDisputeReason(e.target.value)}
                                            rows={2}
                                            placeholder="Briefly explain why this is a genuine complaint (optional)"
                                            className="w-full text-xs border border-red-200 rounded-lg px-3 py-2 bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-300 resize-none"
                                        />
                                        <button
                                            disabled={isDisputing}
                                            onClick={async () => {
                                                setIsDisputing(true);
                                                try {
                                                    await complaintService.appealSpam(id, disputeReason);
                                                    setDisputeMsg({ ok: true, text: 'Dispute submitted. An admin will review your complaint shortly.' });
                                                } catch (e) {
                                                    const msg = e?.response?.data?.detail || e?.message || 'Failed to submit dispute';
                                                    setDisputeMsg({ ok: false, text: msg });
                                                } finally {
                                                    setIsDisputing(false);
                                                }
                                            }}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
                                        >
                                            <Send size={11} />
                                            {isDisputing ? 'Submitting…' : 'Submit Dispute to Admin'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* LLM Failure Warning */}
                        {complaint.llm_failed && (
                            <div className="mb-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                                <p className="text-sm text-yellow-800 font-medium">
                                    ⚠️ AI analysis is temporarily unavailable. This complaint is under manual review.
                                </p>
                            </div>
                        )}

                        {/* Read-only vote summary for admin/authority */}
                        {isAuthorityOrAdmin && complaint.visibility !== 'Private' && (
                            <div className="flex items-center gap-4 py-3 px-4 bg-gray-50 rounded-xl border border-gray-100 mb-6">
                                <div className="flex items-center gap-1.5 text-sm text-green-700 font-semibold">
                                    <ThumbsUp size={14} className="fill-green-600 text-green-600" />
                                    {complaint.upvotes || 0} upvotes
                                </div>
                                <div className="flex items-center gap-1.5 text-sm text-red-600 font-semibold">
                                    <ThumbsDown size={14} className="fill-red-500 text-red-500" />
                                    {complaint.downvotes || 0} downvotes
                                </div>
                                <span className="ml-auto text-xs text-gray-400">
                                    Net score: <span className={`font-bold ${(complaint.net_votes || 0) > 0 ? 'text-green-600' : (complaint.net_votes || 0) < 0 ? 'text-red-500' : 'text-gray-500'}`}>{complaint.net_votes || 0}</span>
                                </span>
                            </div>
                        )}

                        {/* Voting & Interaction - Enhanced (students only, hide for Private) */}
                        {!isAuthorityOrAdmin && complaint.visibility !== 'Private' && <div className="py-6 border-t border-b border-gray-100 mb-8 bg-gradient-to-r from-gray-50/50 to-transparent -mx-6 sm:-mx-10 px-6 sm:px-10">
                            {isOwner ? (
                                <p className="text-xs text-gray-400 italic">Your complaint</p>
                            ) : (
                                <div className="flex flex-wrap items-center gap-4">
                                    {/* Upvote Button */}
                                    <button
                                        onClick={() => handleVote(VOTE_TYPES.UPVOTE)}
                                        disabled={isVoting}
                                        className={
                                            `flex items-center gap-2 px-4 py-2.5 rounded-xl border shadow-sm transition-all duration-200 ${userVote === VOTE_TYPES.UPVOTE
                                                ? 'bg-srec-primary text-white border-srec-primary shadow-md'
                                                : 'bg-srec-primary/5 border-srec-primary/20 hover:bg-srec-primary/10'
                                            } ${isVoting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`
                                        }
                                    >
                                        <ThumbsUp size={18} className={userVote === VOTE_TYPES.UPVOTE ? 'fill-current' : ''} />
                                        <span className="font-bold">{complaint.upvotes || 0}</span>
                                    </button>

                                    {/* Downvote Button */}
                                    <button
                                        onClick={() => handleVote(VOTE_TYPES.DOWNVOTE)}
                                        disabled={isVoting}
                                        className={
                                            `flex items-center gap-2 px-4 py-2.5 rounded-xl border shadow-sm transition-all duration-200 ${userVote === VOTE_TYPES.DOWNVOTE
                                                ? 'bg-srec-danger text-white border-srec-danger shadow-md'
                                                : 'bg-srec-danger/5 border-srec-danger/20 hover:bg-srec-danger/10'
                                            } ${isVoting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`
                                        }
                                    >
                                        <ThumbsDown size={18} className={userVote === VOTE_TYPES.DOWNVOTE ? 'fill-current' : ''} />
                                        <span className="font-bold text-gray-700">{complaint.downvotes || 0}</span>
                                    </button>

                                    {/* Net Score */}
                                    <div className="text-sm text-gray-500 ml-auto font-medium bg-gray-50 px-4 py-2 rounded-lg border border-gray-100">
                                        Net Score: <span className={`font-bold ${complaint.net_votes > 0 ? 'text-green-600' : complaint.net_votes < 0 ? 'text-red-500' : 'text-gray-900'}`}>{complaint.net_votes || 0}</span>
                                    </div>
                                </div>
                            )}
                            {voteError && (
                                <p className="text-xs text-amber-600 mt-1 text-center">{voteError}</p>
                            )}
                            {!isOwner && (
                                <p className="text-xs text-gray-400 mt-4 font-medium">
                                    👆 Votes help authorities prioritise this issue
                                </p>
                            )}
                        </div>}

                        {/* Details Grid */}
                        <div className={`grid grid-cols-1 ${isAuthorityOrAdmin ? 'sm:grid-cols-2' : ''} gap-6 mb-8 p-6 rounded-xl border border-gray-100 bg-gray-50/50`}>
                            {/* Student Info Section */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                                    <ShieldAlert size={16} /> Complaint Author
                                </h3>
                                <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-srec-primary/10 flex items-center justify-center text-srec-primary font-bold">
                                            S
                                        </div>
                                        <div>
                                            <div className="font-bold text-gray-900">
                                                {isAuthorityOrAdmin ? complaint.student_roll_no : 'Student'}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {user?.role === 'Admin' ? 'Full identity — Admin View' : isAuthorityOrAdmin ? 'Full identity visible to you' : 'Identity protected'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Complaint Metadata */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                                    <FileText size={16} /> Reference Info
                                </h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                                        <div className="text-[10px] text-gray-400 uppercase font-bold mb-1">Status</div>
                                        <Badge type={complaint.status} variant="status">{complaint.status || 'Pending'}</Badge>
                                    </div>
                                    <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                                        <div className="text-[10px] text-gray-400 uppercase font-bold mb-1">Priority</div>
                                        <Badge type={complaint.priority} variant="priority">{complaint.priority || 'Normal'}</Badge>
                                    </div>
                                    <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                                        <div className="text-[10px] text-gray-400 uppercase font-bold mb-1">Raised On</div>
                                        <div className="text-sm font-bold text-gray-700">
                                            {format(new Date(complaint.created_at || complaint.submitted_at), 'dd MMM yyyy')}
                                        </div>
                                    </div>
                                    <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                                        <div className="text-[10px] text-gray-400 uppercase font-bold mb-1">Complaint ID</div>
                                        <div className="text-sm font-mono font-bold text-gray-700">#{complaint.id?.toString().slice(-6).toUpperCase()}</div>
                                    </div>
                                </div>

                                {/* Assigned To — shown to complaint owner or when not private */}
                                {complaint.assigned_authority_name && (isOwner || complaint.visibility !== 'Private') && (
                                    <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm flex items-start gap-2.5">
                                        <ShieldCheck size={16} className="text-srec-primary mt-0.5 flex-shrink-0" />
                                        <div>
                                            <div className="text-[10px] text-gray-400 uppercase font-bold mb-0.5">Assigned To</div>
                                            <div className="text-sm font-bold text-gray-800">{complaint.assigned_authority_name}</div>
                                            {complaint.assigned_authority_type && (
                                                <div className="text-xs text-gray-500 mt-0.5">{complaint.assigned_authority_type}</div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Timeline & History Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
                            {/* --- Timeline --- */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
                                    <Clock size={14} className="text-srec-primary" /> Timeline
                                </h3>
                                <div className="relative pl-5 space-y-3 before:absolute before:left-[9px] before:top-1 before:bottom-1 before:w-px before:bg-gray-200">
                                    {loadingTimeline ? (
                                        [1, 2].map(i => <Skeleton key={i} className="h-14 rounded-lg" />)
                                    ) : timeline.length > 0 ? (
                                        timeline.map((event, idx) => (
                                            <div key={idx} className="relative">
                                                <div className={`absolute -left-[19px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-white ${idx === 0 ? 'bg-srec-primary' : 'bg-gray-300'}`} />
                                                <div className="bg-white px-3 py-2.5 rounded-lg border border-gray-100">
                                                    <div className="flex items-start justify-between gap-2">
                                                        <p className="text-xs font-semibold text-gray-800">{event.event}</p>
                                                        <span className="text-[10px] text-gray-400 whitespace-nowrap flex-shrink-0">{format(new Date(event.timestamp), 'MMM d, h:mm a')}</span>
                                                    </div>
                                                    {event.description && (
                                                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{sanitizeDescription(event.description)}</p>
                                                    )}
                                                    {event.updated_by && (
                                                        <p className="text-[10px] text-gray-400 mt-1">By {sanitizeName(event.updated_by)}</p>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-xs text-gray-400 italic py-4">No events yet</p>
                                    )}
                                </div>
                            </div>

                            {/* --- Status History --- */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
                                    <History size={14} className="text-srec-primary" /> Status History
                                </h3>
                                <div className="space-y-2">
                                    {loadingHistory ? (
                                        [1, 2].map(i => <Skeleton key={i} className="h-16 rounded-lg" />)
                                    ) : history.length > 0 ? (
                                        history.map((update, idx) => (
                                            <div key={idx} className="bg-white px-3 py-2.5 rounded-lg border border-gray-100">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <Badge type={update.old_status} variant="status" className="text-[10px]">{update.old_status}</Badge>
                                                    <ChevronRight size={11} className="text-gray-300 flex-shrink-0" />
                                                    <Badge type={update.new_status} variant="status" className="text-[10px] font-bold">{update.new_status}</Badge>
                                                </div>
                                                {update.reason && (
                                                    <p className="text-xs text-gray-500 italic mb-1 line-clamp-2">"{update.reason}"</p>
                                                )}
                                                <div className="flex items-center justify-between text-[10px] text-gray-400">
                                                    <span>{sanitizeName(update.updated_by)}</span>
                                                    <span>{format(new Date(update.updated_at), 'MMM d, h:mm a')}</span>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-xs text-gray-400 italic py-4 text-center">Initial submission pending review</p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Image Verification Section */}
                        {complaint.has_image && complaint.image_verification_status && (() => {
                            let verif = {};
                            const raw = complaint.image_verification_status;
                            try {
                                verif = typeof raw === 'string' ? JSON.parse(raw) : (raw || {});
                            } catch(e) { verif = {}; }
                            const isJsonVerif = verif && (verif.is_relevant !== undefined || verif.is_abusive !== undefined);
                            const isSimpleStatus = !isJsonVerif;
                            return (
                                <div className="mt-8 p-4 bg-gradient-to-br from-blue-50 to-white rounded-xl border border-blue-100 shadow-sm">
                                    <h3 className="text-sm font-bold text-blue-900 mb-2">Image Verification</h3>
                                    {isJsonVerif ? (
                                        <div className="flex flex-wrap gap-2">
                                            {verif.is_relevant === true && (
                                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200 text-xs font-semibold">
                                                    ✓ Image Relevant
                                                </span>
                                            )}
                                            {verif.is_relevant === false && (
                                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold">
                                                    ✗ Image Not Relevant
                                                </span>
                                            )}
                                            {verif.is_abusive === true && (
                                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200 text-xs font-semibold">
                                                    ⚠ Flagged Content
                                                </span>
                                            )}
                                            {verif.confidence !== undefined && (
                                                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-50 text-gray-600 border border-gray-200 text-xs">
                                                    Confidence: {Math.round((verif.confidence || 0) * 100)}%
                                                </span>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-sm">
                                            <span className={`inline-block w-2 h-2 rounded-full ${complaint.image_verified ? 'bg-green-500' : 'bg-orange-500'}`}></span>
                                            <span className={complaint.image_verified ? 'text-green-700 font-medium' : 'text-orange-700 font-medium'}>
                                                {raw}
                                            </span>
                                        </div>
                                    )}
                                    {complaint.image_verification_message && (
                                        <p className="text-xs text-gray-500 mt-2 leading-relaxed">{complaint.image_verification_message}</p>
                                    )}
                                </div>
                            );
                        })()}

                        {/* Escalation Information */}
                        {complaint.escalation_level && complaint.escalation_level > 0 && (
                            <div className="mt-8 p-6 bg-gradient-to-br from-red-50 to-white rounded-xl border border-red-100 shadow-sm">
                                <h3 className="text-sm font-bold text-red-900 mb-2">
                                    ⚠️ Escalated Complaint
                                </h3>
                                <div className="space-y-2 text-sm">
                                    <p className="flex justify-between">
                                        <span className="text-gray-600">Escalation Level:</span>
                                        <span className="font-semibold text-red-700">{complaint.escalation_level}</span>
                                    </p>
                                    {complaint.escalation_reason && (
                                        <p className="text-gray-700">
                                            <span className="font-medium">Reason:</span> {complaint.escalation_reason}
                                        </p>
                                    )}
                                    {complaint.escalated_by && (
                                        <p className="text-gray-600">
                                            <span className="font-medium">Escalated by:</span> {sanitizeName(complaint.escalated_by)}
                                        </p>
                                    )}
                                    {complaint.escalated_at && (
                                        <p className="text-xs text-gray-500 mt-2">
                                            Escalated on {new Date(complaint.escalated_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* ==================== AUTHORITY / ADMIN ACTION PANEL ==================== */}
                        {isAuthorityOrAdmin && (
                            <div className="mt-8 space-y-6">
                                {/* Status Update */}
                                <div className="p-5 bg-amber-50 border border-amber-200 rounded-2xl">
                                    <h3 className="text-sm font-bold text-amber-900 mb-3 flex items-center gap-2">
                                        <ShieldCheck size={16} /> Update Complaint Status
                                    </h3>
                                    <form onSubmit={handleStatusUpdate} className="space-y-3">
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <select
                                                value={newStatus}
                                                onChange={e => setNewStatus(e.target.value)}
                                                className="bg-white border border-amber-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50"
                                                required
                                            >
                                                <option value="">— Select new status —</option>
                                                {(['Raised','In Progress','Resolved','Closed','Spam'].filter(s => s !== complaint.status)).map(s => (
                                                    <option key={s} value={s}>{s}</option>
                                                ))}
                                            </select>
                                            <input
                                                type="text"
                                                placeholder="Reason (required for Closed/Spam)"
                                                value={statusReason}
                                                onChange={e => setStatusReason(e.target.value)}
                                                className="bg-white border border-amber-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400/50"
                                            />
                                        </div>
                                        <button
                                            type="submit"
                                            disabled={isUpdatingStatus || !newStatus}
                                            className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-50"
                                        >
                                            <ShieldCheck size={14} />
                                            {isUpdatingStatus ? 'Updating…' : 'Update Status'}
                                        </button>
                                        {statusUpdateMsg && (
                                            <p className={`text-xs font-medium mt-1 ${statusUpdateMsg.type === 'success' ? 'text-green-700' : 'text-red-600'}`}>
                                                {statusUpdateMsg.text}
                                            </p>
                                        )}
                                    </form>
                                </div>

                                {/* Post a Note / Update to Student */}
                                <div className="p-5 bg-blue-50 border border-blue-200 rounded-2xl">
                                    <h3 className="text-sm font-bold text-blue-900 mb-3 flex items-center gap-2">
                                        <Send size={16} /> Post Update to Student
                                    </h3>
                                    <form onSubmit={handlePostUpdate} className="space-y-3">
                                        <input
                                            type="text"
                                            placeholder="Update title (e.g. 'Action taken')"
                                            value={updateTitle}
                                            onChange={e => setUpdateTitle(e.target.value)}
                                            className="w-full bg-white border border-blue-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                                        />
                                        <textarea
                                            rows={3}
                                            placeholder="Write a note for the student about what action has been taken or is in progress…"
                                            value={updateNote}
                                            onChange={e => setUpdateNote(e.target.value)}
                                            className="w-full bg-white border border-blue-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/50 resize-none"
                                            required
                                        />
                                        <button
                                            type="submit"
                                            disabled={isPostingUpdate || !updateNote.trim()}
                                            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors disabled:opacity-50"
                                        >
                                            <Send size={14} />
                                            {isPostingUpdate ? 'Posting…' : 'Send Note to Student'}
                                        </button>
                                        {postUpdateMsg && (
                                            <p className={`text-xs font-medium mt-1 ${postUpdateMsg.type === 'success' ? 'text-green-700' : 'text-red-600'}`}>
                                                {postUpdateMsg.text}
                                            </p>
                                        )}
                                    </form>
                                </div>
                            </div>
                        )}

                    </div>
                </Card>
            </div>
        </div>
    );
}
