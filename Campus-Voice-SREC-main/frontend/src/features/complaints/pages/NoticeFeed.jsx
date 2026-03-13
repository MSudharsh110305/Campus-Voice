import React, { useState, useEffect, useCallback } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { EliteButton, Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import studentService from '../../../services/student.service';
import { tokenStorage } from '../../../utils/api';
import { Megaphone, Calendar, AlertTriangle, Info, Wrench, RefreshCw, Users, Paperclip, X, Download, FileText } from 'lucide-react';

// ─── Notice Detail Modal ──────────────────────────────────────────────────────
function NoticeDetailModal({ notice, onClose, onOpenAttachment, attachLoading, CATEGORY_CONFIG, PRIORITY_DOT, formatDate, formatExpiry, formatAudience }) {
    useEffect(() => {
        const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [onClose]);

    if (!notice) return null;
    const cfg = CATEGORY_CONFIG[notice.category] || CATEGORY_CONFIG['Announcement'];
    const Icon = cfg.icon;
    const dotColor = PRIORITY_DOT[notice.priority] || PRIORITY_DOT['Low'];
    const isEmergency = notice.category === 'Emergency';
    const expiryLabel = formatExpiry(notice.expires_at, notice.category);

    return (
        <div
            className="fixed inset-0 z-[90] flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4 animate-fadeIn"
            onClick={onClose}
        >
            <div
                className="relative bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl w-full sm:max-w-lg max-h-[85vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Drag handle (mobile) */}
                <div className="flex justify-center pt-3 pb-1 sm:hidden">
                    <div className="w-10 h-1 bg-gray-200 rounded-full" />
                </div>

                {isEmergency && (
                    <div className="px-5 py-1.5 bg-red-600 flex items-center gap-2">
                        <AlertTriangle size={11} className="text-white flex-shrink-0" />
                        <span className="text-[10px] font-bold text-white tracking-widest uppercase">Emergency Notice</span>
                    </div>
                )}

                <div className="px-5 pt-4 pb-2 border-b border-gray-100">
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.badge}`}>
                                <Icon size={11} /> {notice.category}
                            </span>
                            <span className="flex items-center gap-1 text-xs text-gray-400">
                                <span className={`w-2 h-2 rounded-full ${dotColor} inline-block`} />
                                {notice.priority}
                            </span>
                        </div>
                        <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1 rounded-lg flex-shrink-0">
                            <X size={18} />
                        </button>
                    </div>
                    <h2 className="text-base font-bold text-gray-900 mt-3 leading-snug">{notice.title}</h2>
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
                        <span className="font-medium text-gray-600">{notice.authority_name || 'Authority'}</span>
                        {notice.authority_type && <span>· {notice.authority_type}</span>}
                        <span className="ml-auto">{formatDate(notice.created_at)}</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto px-5 py-4">
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{notice.content}</p>

                    {expiryLabel && (
                        <div className={`mt-4 p-3 rounded-xl text-xs font-medium flex items-center gap-2 ${
                            isEmergency ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                        }`}>
                            {isEmergency ? '⚠' : '⏰'} {expiryLabel}
                        </div>
                    )}

                    <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                            <Users size={11} /> {formatAudience(notice)}
                        </span>
                    </div>

                    {notice.attachments?.length > 0 && (
                        <div className="mt-3 space-y-2">
                            {notice.attachments.map(att => (
                                <button
                                    key={att.id}
                                    onClick={() => { onClose(); onOpenAttachment(`${notice.id}/attachments/${att.id}`, att.filename, att.mimetype); }}
                                    className="w-full flex items-center gap-2 py-2.5 px-3 rounded-xl border border-srec-border text-sm text-srec-primary font-medium hover:bg-srec-primarySoft transition-colors"
                                >
                                    <Paperclip size={14} />
                                    <span className="truncate">{att.filename}</span>
                                    <span className="ml-auto text-xs text-gray-400 flex-shrink-0">{(att.size / 1024).toFixed(0)} KB</span>
                                </button>
                            ))}
                        </div>
                    )}
                    {(!notice.attachments?.length && notice.attachment_filename) && (
                        <button
                            onClick={() => { onClose(); onOpenAttachment(notice.id, notice.attachment_filename, notice.attachment_mimetype); }}
                            disabled={attachLoading === notice.id}
                            className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-srec-border text-sm text-srec-primary font-medium hover:bg-srec-primarySoft transition-colors disabled:opacity-60"
                        >
                            <Paperclip size={14} className={attachLoading === notice.id ? 'animate-pulse' : ''} />
                            {attachLoading === notice.id ? 'Loading…' : `View Attachment: ${notice.attachment_filename}`}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

// ─── Attachment Viewer Modal ─────────────────────────────────────────────────
function AttachmentModal({ filename, mimeType, blobUrl, onClose }) {
    useEffect(() => {
        const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [onClose]);

    const isImage = mimeType && mimeType.startsWith('image/');
    const isPdf = mimeType === 'application/pdf' || filename?.toLowerCase().endsWith('.pdf');

    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-fadeIn"
            onClick={onClose}
        >
            <div
                className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0">
                    <div className="flex items-center gap-2 min-w-0">
                        {isImage ? <Paperclip size={14} className="text-srec-primary flex-shrink-0" /> : <FileText size={14} className="text-srec-primary flex-shrink-0" />}
                        <p className="text-sm font-semibold text-gray-800 truncate">{filename}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                        <a
                            href={blobUrl}
                            download={filename}
                            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
                            title="Download"
                        >
                            <Download size={15} />
                        </a>
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800"
                        >
                            <X size={15} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto flex items-center justify-center bg-gray-50 min-h-0">
                    {isImage ? (
                        <img
                            src={blobUrl}
                            alt={filename}
                            className="max-w-full max-h-[75vh] object-contain p-4"
                        />
                    ) : isPdf ? (
                        <iframe
                            src={blobUrl}
                            title={filename}
                            className="w-full h-[75vh] border-0"
                        />
                    ) : (
                        <div className="text-center py-12 px-6">
                            <FileText size={40} className="text-gray-300 mx-auto mb-3" />
                            <p className="text-sm text-gray-600 font-medium mb-4">{filename}</p>
                            <a
                                href={blobUrl}
                                download={filename}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-srec-primary text-white rounded-xl text-sm font-semibold hover:bg-srec-primaryDark transition-colors"
                            >
                                <Download size={14} /> Download file
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Category config: icon + color palette
const CATEGORY_CONFIG = {
    Emergency:      { icon: AlertTriangle, color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-l-red-600',   badge: 'bg-red-100 text-red-700',   urgent: true },
    Announcement:   { icon: Megaphone,    color: 'text-blue-600',   bg: 'bg-blue-50',   border: 'border-l-blue-500',  badge: 'bg-blue-100 text-blue-700',  urgent: false },
    'Policy Change':{ icon: Info,         color: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-l-amber-500', badge: 'bg-amber-100 text-amber-700', urgent: false },
    Event:          { icon: Calendar,     color: 'text-green-600',  bg: 'bg-green-50',  border: 'border-l-green-500', badge: 'bg-green-100 text-green-700', urgent: false },
    Maintenance:    { icon: Wrench,       color: 'text-gray-600',   bg: 'bg-gray-50',   border: 'border-l-gray-400',  badge: 'bg-gray-100 text-gray-600',   urgent: false },
    General:        { icon: Info,         color: 'text-sky-600',    bg: 'bg-sky-50',    border: 'border-l-sky-400',   badge: 'bg-sky-100 text-sky-700',     urgent: false },
};

const PRIORITY_DOT = {
    Urgent: 'bg-red-500',
    High:   'bg-orange-400',
    Medium: 'bg-blue-400',
    Low:    'bg-gray-300',
};

export default function NoticeFeed() {
    const { user } = useAuth();
    const { markNoticesSeen } = useNotifications();
    const [notices, setNotices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [skip, setSkip] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [error, setError] = useState(null);
    const [attachment, setAttachment] = useState(null); // { blobUrl, filename, mimeType }
    const [attachLoading, setAttachLoading] = useState(null); // noticeId being loaded
    const [selectedNotice, setSelectedNotice] = useState(null); // notice shown in detail modal
    const LIMIT = 20;

    const openAttachment = useCallback(async (noticeIdOrPath, filename, mimeType) => {
        if (attachLoading) return;
        setAttachLoading(noticeIdOrPath);
        try {
            const token = tokenStorage.getAccessToken() || '';
            // Multi-file path looks like "123/attachments/456"; legacy is just a notice id
            const urlPath = String(noticeIdOrPath).includes('/attachments/')
                ? `/api/authorities/notices/${noticeIdOrPath}`
                : `/api/authorities/notices/${noticeIdOrPath}/attachment`;
            const res = await fetch(`${urlPath}?token=${token}`);
            if (!res.ok) throw new Error('Failed to load attachment');
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);
            setAttachment({ blobUrl, filename, mimeType: mimeType || blob.type });
        } catch (err) {
            console.error('Attachment load error:', err);
        } finally {
            setAttachLoading(null);
        }
    }, [attachLoading]);

    const closeAttachment = useCallback(() => {
        if (attachment?.blobUrl) URL.revokeObjectURL(attachment.blobUrl);
        setAttachment(null);
    }, [attachment]);

    useEffect(() => {
        fetchNotices(true);
        markNoticesSeen();
    }, []);

    // Feature 4: Vibration API — vibrate once per session for recent Emergency notices
    useEffect(() => {
        if (!notices || notices.length === 0) return;
        const hasRecentEmergency = notices.some(n =>
            n.category === 'Emergency' &&
            new Date(n.created_at) > new Date(Date.now() - 48 * 60 * 60 * 1000)
        );
        if (hasRecentEmergency && !sessionStorage.getItem('cv_emergency_vibrated')) {
            navigator.vibrate && navigator.vibrate([200, 100, 200]);
            sessionStorage.setItem('cv_emergency_vibrated', '1');
        }
    }, [notices]);

    const fetchNotices = async (reset = false) => {
        try {
            setLoading(true);
            setError(null);
            const currentSkip = reset ? 0 : skip;
            const data = await studentService.getNotices({ skip: currentSkip, limit: LIMIT });
            const list = data?.notices || [];
            if (reset) {
                setNotices(list);
                setSkip(LIMIT);
            } else {
                setNotices(prev => [...prev, ...list]);
                setSkip(prev => prev + LIMIT);
            }
            setHasMore(list.length === LIMIT);
        } catch (err) {
            setError(err.message || 'Failed to load notices');
        } finally {
            setLoading(false);
        }
    };

    const formatAudience = (notice) => {
        const parts = [];
        if (notice.target_gender?.length) parts.push(notice.target_gender.join('/'));
        if (notice.target_stay_types?.length) parts.push(notice.target_stay_types.join('/'));
        if (notice.target_departments?.length) parts.push(notice.target_departments.join(', '));
        if (notice.target_years?.length) parts.push(`Yr ${notice.target_years.join(', ')}`);
        return parts.length ? parts.join(' · ') : 'All Students';
    };

    const formatDate = (ts) => {
        if (!ts) return '';
        const d = new Date(ts);
        const now = new Date();
        const diff = now - d;
        const days = Math.floor(diff / 86400000);
        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    };

    const formatExpiry = (expiresAt, category) => {
        if (!expiresAt) return null;
        const exp = new Date(expiresAt);
        const now = new Date();
        const diffMs = exp - now;
        if (diffMs <= 0) return null; // already expired — won't show in feed
        const diffHours = diffMs / (1000 * 60 * 60);
        const diffDays = diffMs / (1000 * 60 * 60 * 24);
        // Emergency / Maintenance: show hours if within 48h
        if ((category === 'Emergency' || category === 'Maintenance') && diffHours <= 48) {
            const h = Math.round(diffHours);
            return `Expires in ${h} hour${h !== 1 ? 's' : ''}`;
        }
        // General / Announcement: show "Active until DATE"
        if (category === 'General' || category === 'Announcement') {
            return `Active until ${exp.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: diffDays > 365 ? 'numeric' : undefined })}`;
        }
        // Other: show days remaining if <= 7 days
        if (diffDays <= 7) {
            const d = Math.round(diffDays);
            return `Expires in ${d} day${d !== 1 ? 's' : ''}`;
        }
        return null;
    };

    return (
        <div className="min-h-screen bg-srec-background">
            <TopNav />
            <div className="max-w-2xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">
                {/* Header banner */}
                <div className="mb-5 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-4 shadow-md shadow-green-900/10 relative overflow-hidden">
                    <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-white/5 pointer-events-none" />
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-green-200 text-[10px] font-semibold uppercase tracking-widest mb-0.5">SREC Campus Voice</p>
                            <h1 className="text-xl font-bold text-white tracking-tight">Notice Board</h1>
                            <p className="text-green-300 text-xs mt-0.5">Official campus announcements</p>
                        </div>
                        <button
                            onClick={() => fetchNotices(true)}
                            className="p-2.5 rounded-xl text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                        >
                            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm">
                        {error}
                    </div>
                )}

                <div className="space-y-3">
                    {loading && notices.length === 0 ? (
                        [1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)
                    ) : notices.length === 0 ? (
                        <div className="py-16 text-center">
                            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                                <Megaphone size={22} className="text-gray-300" />
                            </div>
                            <p className="text-sm font-medium text-gray-500">No notices yet</p>
                            <p className="text-xs text-gray-400 mt-1">Check back later for campus announcements.</p>
                        </div>
                    ) : (
                        notices.map((notice) => {
                            const cfg = CATEGORY_CONFIG[notice.category] || CATEGORY_CONFIG['Announcement'];
                            const Icon = cfg.icon;
                            const dotColor = PRIORITY_DOT[notice.priority] || PRIORITY_DOT['Low'];
                            const isUrgent = notice.priority === 'Urgent' || notice.priority === 'High';
                            const isEmergency = notice.category === 'Emergency';
                            const expiryLabel = formatExpiry(notice.expires_at, notice.category);

                            return (
                                <div
                                    key={notice.id}
                                    onClick={() => setSelectedNotice(notice)}
                                    className={`bg-white rounded-xl border overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-pointer ${
                                        isEmergency
                                            ? 'border-red-300 border-l-4 border-l-red-600'
                                            : `border-gray-100 border-l-4 ${cfg.border}`
                                    }`}
                                >
                                    {/* Emergency URGENT banner */}
                                    {isEmergency && (
                                        <div className="px-4 py-1.5 bg-red-600 flex items-center gap-2">
                                            <AlertTriangle size={11} className="text-white flex-shrink-0" />
                                            <span className="text-[10px] font-bold text-white tracking-widest uppercase">Urgent</span>
                                        </div>
                                    )}

                                    <div className="px-4 py-3">
                                        {/* Top row: category badge + priority dot + date */}
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${cfg.badge}`}>
                                                    <Icon size={10} />
                                                    {notice.category}
                                                </span>
                                                <span className="flex items-center gap-1 text-[10px] text-gray-400">
                                                    <span className={`w-1.5 h-1.5 rounded-full ${dotColor} inline-block`} />
                                                    {notice.priority}
                                                </span>
                                            </div>
                                            <span className="text-[10px] text-gray-400">{formatDate(notice.created_at)}</span>
                                        </div>

                                        {/* Title */}
                                        <p className={`text-sm font-semibold leading-snug mb-1 ${isUrgent || isEmergency ? 'text-gray-900' : 'text-gray-800'}`}>
                                            {notice.title}
                                        </p>

                                        {/* Content — fixed height, scrollable so card ratio stays consistent */}
                                        <div className="text-xs text-gray-500 leading-relaxed max-h-[54px] overflow-y-auto pr-0.5" style={{scrollbarWidth:'thin',scrollbarColor:'#d1d5db transparent'}}>
                                            {notice.content}
                                        </div>

                                        {/* Attachments — multi-file support */}
                                        {notice.attachments?.length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {notice.attachments.map(att => (
                                                    <button
                                                        key={att.id}
                                                        onClick={(e) => { e.stopPropagation(); openAttachment(`${notice.id}/attachments/${att.id}`, att.filename, att.mimetype); }}
                                                        className="inline-flex items-center gap-1 text-[10px] text-srec-primary hover:underline"
                                                    >
                                                        <Paperclip size={10} />
                                                        {att.filename}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                        {(!notice.attachments?.length && notice.attachment_filename) && (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); openAttachment(notice.id, notice.attachment_filename, notice.attachment_mimetype); }}
                                                disabled={attachLoading === notice.id}
                                                className="mt-2 inline-flex items-center gap-1.5 text-[10px] text-srec-primary hover:underline disabled:opacity-60"
                                            >
                                                <Paperclip size={10} className={attachLoading === notice.id ? 'animate-pulse' : ''} />
                                                {attachLoading === notice.id ? 'Loading…' : notice.attachment_filename}
                                            </button>
                                        )}

                                        {/* Footer */}
                                        <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-gray-50">
                                            <span className="text-[10px] text-gray-500">
                                                <span className="font-medium text-gray-700">{notice.authority_name || 'Authority'}</span>
                                                {notice.authority_type && (
                                                    <span className="text-gray-400"> · {notice.authority_type}</span>
                                                )}
                                            </span>
                                            <span className="flex items-center gap-1 text-[10px] text-gray-400">
                                                <Users size={9} />
                                                {formatAudience(notice)}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Expiry info strip */}
                                    {expiryLabel && (
                                        <div className={`px-4 py-1.5 border-t text-[10px] font-medium ${
                                            isEmergency
                                                ? 'bg-red-50 border-red-100 text-red-700'
                                                : 'bg-amber-50 border-amber-100 text-amber-700'
                                        }`}>
                                            {isEmergency ? '⚠' : '⏰'} {expiryLabel}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}

                    {!loading && hasMore && notices.length > 0 && (
                        <div className="flex justify-center pt-2">
                            <EliteButton variant="outline" size="sm" onClick={() => fetchNotices(false)}>
                                Load more
                            </EliteButton>
                        </div>
                    )}

                    {loading && notices.length > 0 && (
                        <Skeleton className="h-24 rounded-xl" />
                    )}
                </div>
            </div>
            {user?.role === 'Student' && <BottomNav />}

            {/* Notice detail modal */}
            {selectedNotice && (
                <NoticeDetailModal
                    notice={selectedNotice}
                    onClose={() => setSelectedNotice(null)}
                    onOpenAttachment={openAttachment}
                    attachLoading={attachLoading}
                    CATEGORY_CONFIG={CATEGORY_CONFIG}
                    PRIORITY_DOT={PRIORITY_DOT}
                    formatDate={formatDate}
                    formatExpiry={formatExpiry}
                    formatAudience={formatAudience}
                />
            )}

            {/* Attachment viewer modal */}
            {attachment && (
                <AttachmentModal
                    filename={attachment.filename}
                    mimeType={attachment.mimeType}
                    blobUrl={attachment.blobUrl}
                    onClose={closeAttachment}
                />
            )}
        </div>
    );
}
