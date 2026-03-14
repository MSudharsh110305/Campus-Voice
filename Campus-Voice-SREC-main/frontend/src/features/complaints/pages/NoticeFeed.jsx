import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import studentService from '../../../services/student.service';
import { tokenStorage } from '../../../utils/api';
import {
    Megaphone, Calendar, AlertTriangle, Info, Wrench,
    Users, Paperclip, X, Download, FileText, ChevronRight,
    Bell, Inbox, Pin, Pencil,
} from 'lucide-react';

// ─── Category config ──────────────────────────────────────────────────────────
const CATEGORY_CONFIG = {
    Emergency:      { icon: AlertTriangle, color: 'text-red-600',    iconBg: 'bg-red-100',    border: 'border-red-200',   accent: 'bg-red-600',    badge: 'bg-red-100 text-red-700',    headerBg: 'from-red-600 to-red-700' },
    Announcement:   { icon: Megaphone,    color: 'text-blue-600',   iconBg: 'bg-blue-100',   border: 'border-blue-200',  accent: 'bg-blue-500',   badge: 'bg-blue-100 text-blue-700',  headerBg: 'from-blue-600 to-blue-700' },
    'Policy Change':{ icon: Info,         color: 'text-amber-600',  iconBg: 'bg-amber-100',  border: 'border-amber-200', accent: 'bg-amber-500',  badge: 'bg-amber-100 text-amber-700', headerBg: 'from-amber-500 to-amber-600' },
    Event:          { icon: Calendar,     color: 'text-emerald-600',iconBg: 'bg-emerald-100',border: 'border-emerald-200',accent: 'bg-emerald-500',badge: 'bg-emerald-100 text-emerald-700',headerBg: 'from-emerald-600 to-emerald-700' },
    Maintenance:    { icon: Wrench,       color: 'text-slate-600',  iconBg: 'bg-slate-100',  border: 'border-slate-200', accent: 'bg-slate-500',  badge: 'bg-slate-100 text-slate-600', headerBg: 'from-slate-600 to-slate-700' },
    General:        { icon: Info,         color: 'text-sky-600',    iconBg: 'bg-sky-100',    border: 'border-sky-200',   accent: 'bg-sky-500',    badge: 'bg-sky-100 text-sky-700',    headerBg: 'from-sky-500 to-sky-600' },
};

const PRIORITY_CONFIG = {
    Urgent: { dot: 'bg-red-500',    text: 'text-red-600',    label: 'Urgent' },
    High:   { dot: 'bg-orange-400', text: 'text-orange-600', label: 'High'   },
    Medium: { dot: 'bg-blue-400',   text: 'text-blue-500',   label: 'Medium' },
    Low:    { dot: 'bg-gray-300',   text: 'text-gray-400',   label: 'Low'    },
};

// ─── URL link parser ─────────────────────────────────────────────────────────
function LinkifiedText({ text, className = '' }) {
    if (!text) return null;
    const URL_REGEX = /(https?:\/\/[^\s\n]+)/g;
    const parts = text.split(URL_REGEX);
    return (
        <span className={className}>
            {parts.map((part, i) =>
                URL_REGEX.test(part) ? (
                    <a
                        key={i}
                        href={part}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 underline underline-offset-1 hover:text-blue-800 break-all"
                        onClick={e => e.stopPropagation()}
                    >
                        {part}
                    </a>
                ) : (
                    <span key={i}>{part}</span>
                )
            )}
        </span>
    );
}

// ─── Notice Detail Sheet ──────────────────────────────────────────────────────
function NoticeDetailSheet({ notice, onClose, onOpenAttachment, attachLoading, formatDate, formatExpiry, formatAudience }) {
    useEffect(() => {
        const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handleKey);
        document.body.style.overflow = 'hidden';
        return () => {
            window.removeEventListener('keydown', handleKey);
            document.body.style.overflow = '';
        };
    }, [onClose]);

    if (!notice) return null;
    const cfg = CATEGORY_CONFIG[notice.category] || CATEGORY_CONFIG['Announcement'];
    const pri = PRIORITY_CONFIG[notice.priority] || PRIORITY_CONFIG['Low'];
    const Icon = cfg.icon;
    const isEmergency = notice.category === 'Emergency';
    const expiryLabel = formatExpiry(notice.expires_at, notice.category);
    const hasAttachments = notice.attachments?.length > 0 || notice.attachment_filename;

    return (
        <div
            className="fixed inset-0 z-[90] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={onClose}
        >
            <div
                className="relative bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl w-full sm:max-w-lg max-h-[92vh] sm:max-h-[85vh] flex flex-col overflow-hidden border border-white/20"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Drag handle */}
                <div className="flex justify-center pt-3 pb-0 sm:hidden flex-shrink-0">
                    <div className="w-10 h-1 bg-gray-200 rounded-full" />
                </div>

                {/* Coloured header */}
                <div className={`bg-gradient-to-br ${cfg.headerBg} px-5 pt-4 pb-6 flex-shrink-0 relative overflow-hidden`}>
                    {/* Decorative circles */}
                    <div className="absolute -top-8 -right-8 w-28 h-28 rounded-full bg-white/5 pointer-events-none" />
                    <div className="absolute -bottom-6 -left-4 w-20 h-20 rounded-full bg-white/5 pointer-events-none" />
                    <div className="relative">
                        <div className="flex items-start justify-between gap-3 mb-3">
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/20 text-white text-xs font-semibold backdrop-blur-sm">
                                    <Icon size={11} /> {notice.category}
                                </span>
                                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/15 text-white/90 text-xs font-medium">
                                    <span className={`w-2 h-2 rounded-full ${pri.dot} inline-block ring-1 ring-white/30`} />
                                    {notice.priority}
                                </span>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-full bg-white/20 hover:bg-white/35 text-white transition-colors flex-shrink-0 backdrop-blur-sm"
                            >
                                <X size={16} />
                            </button>
                        </div>
                        <h2 className="text-lg font-bold text-white leading-snug pr-2">{notice.title}</h2>
                        <div className="flex items-center gap-2 mt-2.5">
                            <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                                <Icon size={11} className="text-white" />
                            </div>
                            <span className="text-xs font-semibold text-white/90">{notice.authority_name || 'Authority'}</span>
                            {notice.authority_type && <span className="text-xs text-white/60">· {notice.authority_type}</span>}
                            <span className="ml-auto text-xs text-white/60">{formatDate(notice.created_at)}</span>
                        </div>
                    </div>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4 min-h-0">
                    {/* Content */}
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                            <LinkifiedText text={notice.content} />
                        </p>
                    </div>

                    {expiryLabel && (
                        <div className={`p-3 rounded-xl text-xs font-semibold flex items-center gap-2 border ${
                            isEmergency ? 'bg-red-50 border-red-200 text-red-700' : 'bg-amber-50 border-amber-200 text-amber-700'
                        }`}>
                            <span className="text-base">{isEmergency ? '⚠️' : '⏰'}</span>
                            <span>{expiryLabel}</span>
                        </div>
                    )}

                    <div className="flex items-center gap-2 py-2.5 px-3 bg-gray-50 rounded-xl border border-gray-100 text-xs text-gray-500">
                        <Users size={12} className="flex-shrink-0 text-gray-400" />
                        <span className="font-medium">{formatAudience(notice)}</span>
                    </div>

                    {/* Attachments */}
                    {notice.attachments?.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Attachments</p>
                            {notice.attachments.map(att => (
                                <button
                                    key={att.id}
                                    onClick={() => { onClose(); onOpenAttachment(`${notice.id}/attachments/${att.id}`, att.filename, att.mimetype); }}
                                    className="w-full flex items-center gap-3 py-2.5 px-3 rounded-xl border border-gray-200 hover:border-srec-primary hover:bg-srec-primarySoft transition-all group"
                                >
                                    <div className="w-8 h-8 rounded-lg bg-srec-primarySoft flex items-center justify-center flex-shrink-0 group-hover:bg-srec-primary/20">
                                        <Paperclip size={13} className="text-srec-primary" />
                                    </div>
                                    <span className="flex-1 text-sm text-gray-700 font-medium truncate text-left">{att.filename}</span>
                                    <span className="text-xs text-gray-400 flex-shrink-0">{(att.size / 1024).toFixed(0)} KB</span>
                                    <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
                                </button>
                            ))}
                        </div>
                    )}
                    {(!notice.attachments?.length && notice.attachment_filename) && (
                        <div className="space-y-2">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Attachment</p>
                            <button
                                onClick={() => { onClose(); onOpenAttachment(notice.id, notice.attachment_filename, notice.attachment_mimetype); }}
                                disabled={attachLoading === notice.id}
                                className="w-full flex items-center gap-3 py-2.5 px-3 rounded-xl border border-gray-200 hover:border-srec-primary hover:bg-srec-primarySoft transition-all group disabled:opacity-60"
                            >
                                <div className="w-8 h-8 rounded-lg bg-srec-primarySoft flex items-center justify-center flex-shrink-0">
                                    <Paperclip size={13} className={`text-srec-primary ${attachLoading === notice.id ? 'animate-pulse' : ''}`} />
                                </div>
                                <span className="flex-1 text-sm text-gray-700 font-medium truncate text-left">
                                    {attachLoading === notice.id ? 'Loading…' : notice.attachment_filename}
                                </span>
                                <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ─── Attachment Viewer Modal ──────────────────────────────────────────────────
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
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fadeIn"
            onClick={onClose}
        >
            <div
                className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0">
                    <div className="flex items-center gap-2 min-w-0">
                        {isImage ? <Paperclip size={14} className="text-srec-primary flex-shrink-0" /> : <FileText size={14} className="text-srec-primary flex-shrink-0" />}
                        <p className="text-sm font-semibold text-gray-800 truncate">{filename}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                        <a href={blobUrl} download={filename} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800" title="Download">
                            <Download size={15} />
                        </a>
                        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-800">
                            <X size={15} />
                        </button>
                    </div>
                </div>
                <div className="flex-1 overflow-auto flex items-center justify-center bg-gray-50 min-h-0">
                    {isImage ? (
                        <img src={blobUrl} alt={filename} className="max-w-full max-h-[75vh] object-contain p-4" />
                    ) : isPdf ? (
                        <iframe src={blobUrl} title={filename} className="w-full h-[75vh] border-0" />
                    ) : (
                        <div className="text-center py-12 px-6">
                            <FileText size={40} className="text-gray-300 mx-auto mb-3" />
                            <p className="text-sm text-gray-600 font-medium mb-4">{filename}</p>
                            <a href={blobUrl} download={filename} className="inline-flex items-center gap-2 px-4 py-2 bg-srec-primary text-white rounded-xl text-sm font-semibold hover:bg-srec-primaryDark transition-colors">
                                <Download size={14} /> Download file
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ─── Notice Card ─────────────────────────────────────────────────────────────
function NoticeCard({ notice, onClick, onOpenAttachment, attachLoading, formatDate, formatExpiry, formatAudience, cardRef }) {
    const cfg = CATEGORY_CONFIG[notice.category] || CATEGORY_CONFIG['Announcement'];
    const pri = PRIORITY_CONFIG[notice.priority] || PRIORITY_CONFIG['Low'];
    const Icon = cfg.icon;
    const isEmergency = notice.category === 'Emergency';
    const isAdminNotice = notice.authority_type === 'Admin';
    const expiryLabel = formatExpiry(notice.expires_at, notice.category);
    const isEdited = notice.updated_at && notice.created_at &&
        new Date(notice.updated_at) - new Date(notice.created_at) > 5000;

    return (
        <div
            ref={cardRef}
            onClick={onClick}
            className={`group bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer hover:-translate-y-0.5 relative ${
                isAdminNotice
                    ? 'border-2 border-srec-primary/30 shadow-green-100'
                    : isEmergency ? 'border border-red-200' : 'border border-gray-100'
            }`}
        >
            {/* Admin pinned bar — gradient with shimmer feel */}
            {isAdminNotice && (
                <div className="px-4 py-1.5 bg-gradient-to-r from-srec-primary via-green-700 to-emerald-600 flex items-center gap-2">
                    <Pin size={10} className="text-white flex-shrink-0" />
                    <span className="text-[10px] font-bold text-white tracking-widest uppercase flex-1">Pinned · Admin Notice</span>
                    {isEdited && (
                        <span className="flex items-center gap-0.5 text-[9px] text-white/70 italic">
                            <Pencil size={8} /> edited
                        </span>
                    )}
                </div>
            )}

            {/* Emergency top bar */}
            {!isAdminNotice && isEmergency && (
                <div className="px-4 py-1.5 bg-red-600 flex items-center gap-2">
                    <AlertTriangle size={11} className="text-white flex-shrink-0" />
                    <span className="text-[10px] font-bold text-white tracking-widest uppercase">Emergency Notice</span>
                </div>
            )}

            {/* Left accent bar for admin notices */}
            {isAdminNotice && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-srec-primary to-emerald-500 rounded-l-2xl pointer-events-none" />
            )}

            <div className={`p-4 ${isAdminNotice ? 'pl-5' : ''}`}>
                {/* Top row */}
                <div className="flex items-start gap-3">
                    {/* Category icon */}
                    <div className={`w-10 h-10 rounded-xl ${isAdminNotice ? 'bg-srec-primarySoft' : cfg.iconBg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                        <Icon size={18} className={isAdminNotice ? 'text-srec-primary' : cfg.color} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${isAdminNotice ? 'bg-srec-primarySoft text-srec-primary' : cfg.badge}`}>
                                    {notice.category}
                                </span>
                                <span className={`flex items-center gap-1 text-[10px] font-medium ${pri.text}`}>
                                    <span className={`w-1.5 h-1.5 rounded-full ${pri.dot} inline-block`} />
                                    {notice.priority}
                                </span>
                                {!isAdminNotice && isEdited && (
                                    <span className="flex items-center gap-0.5 text-[9px] text-gray-400 italic">
                                        <Pencil size={8} /> edited
                                    </span>
                                )}
                            </div>
                            <span className="text-[10px] text-gray-400 flex-shrink-0">{formatDate(notice.created_at)}</span>
                        </div>

                        <p className={`text-sm font-semibold leading-snug ${
                            isAdminNotice ? 'text-srec-primaryDark' :
                            isEmergency ? 'text-red-700' : 'text-gray-900'
                        }`}>
                            {notice.title}
                        </p>

                        <p className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-2">
                            {notice.content}
                        </p>
                    </div>
                </div>

                {/* Attachment chips */}
                {notice.attachments?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5 pl-[52px]">
                        {notice.attachments.map(att => (
                            <button
                                key={att.id}
                                onClick={(e) => { e.stopPropagation(); onOpenAttachment(`${notice.id}/attachments/${att.id}`, att.filename, att.mimetype); }}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-gray-50 border border-gray-200 text-[10px] text-srec-primary font-medium hover:bg-srec-primarySoft hover:border-srec-primary transition-colors"
                            >
                                <Paperclip size={9} />
                                <span className="max-w-[120px] truncate">{att.filename}</span>
                            </button>
                        ))}
                    </div>
                )}
                {(!notice.attachments?.length && notice.attachment_filename) && (
                    <div className="mt-3 pl-[52px]">
                        <button
                            onClick={(e) => { e.stopPropagation(); onOpenAttachment(notice.id, notice.attachment_filename, notice.attachment_mimetype); }}
                            disabled={attachLoading === notice.id}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-gray-50 border border-gray-200 text-[10px] text-srec-primary font-medium hover:bg-srec-primarySoft hover:border-srec-primary transition-colors disabled:opacity-60"
                        >
                            <Paperclip size={9} className={attachLoading === notice.id ? 'animate-pulse' : ''} />
                            <span className="max-w-[140px] truncate">{attachLoading === notice.id ? 'Loading…' : notice.attachment_filename}</span>
                        </button>
                    </div>
                )}

                {/* Footer */}
                <div className={`flex items-center justify-between mt-3 pt-3 border-t ${isAdminNotice ? 'border-srec-primary/10' : 'border-gray-50'}`}>
                    <span className="text-[10px] text-gray-500">
                        <span className={`font-semibold ${isAdminNotice ? 'text-srec-primary' : 'text-gray-700'}`}>{notice.authority_name || 'Authority'}</span>
                        {notice.authority_type && <span className="text-gray-400"> · {notice.authority_type}</span>}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-gray-400">
                        <Users size={9} />
                        {formatAudience(notice)}
                    </span>
                </div>
            </div>

            {/* Expiry strip */}
            {expiryLabel && (
                <div className={`px-4 py-1.5 border-t text-[10px] font-medium flex items-center gap-1.5 ${
                    isEmergency && !isAdminNotice ? 'bg-red-50 border-red-100 text-red-700' : 'bg-amber-50 border-amber-100 text-amber-700'
                }`}>
                    <span>{isEmergency && !isAdminNotice ? '⚠️' : '⏰'}</span> {expiryLabel}
                </div>
            )}
        </div>
    );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function NoticeFeed() {
    const { user } = useAuth();
    const { markNoticesSeen } = useNotifications();
    const [notices, setNotices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [skip, setSkip] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [error, setError] = useState(null);
    const [attachment, setAttachment] = useState(null);
    const [attachLoading, setAttachLoading] = useState(null);
    const [selectedNotice, setSelectedNotice] = useState(null);
    const [showPinnedBar, setShowPinnedBar] = useState(false);
    const sentinelRef = useRef(null);
    const observerRef = useRef(null);
    const pinnedCardRef = useRef(null);
    const contentRef = useRef(null);
    const LIMIT = 20;

    const openAttachment = useCallback(async (noticeIdOrPath, filename, mimeType) => {
        if (attachLoading) return;
        setAttachLoading(noticeIdOrPath);
        try {
            const token = tokenStorage.getAccessToken() || '';
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

    const fetchNotices = useCallback(async (reset = false) => {
        try {
            if (reset) setLoading(true); else setLoadingMore(true);
            setError(null);
            const currentSkip = reset ? 0 : skip;
            const data = await studentService.getNotices({ skip: currentSkip, limit: LIMIT });
            const raw = data?.notices || [];
            // Admin notices always pinned to top
            const list = [...raw].sort((a, b) => {
                const aPin = a.authority_type === 'Admin' ? 0 : 1;
                const bPin = b.authority_type === 'Admin' ? 0 : 1;
                return aPin - bPin;
            });
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
            if (reset) setLoading(false); else setLoadingMore(false);
        }
    }, [skip]);

    useEffect(() => {
        fetchNotices(true);
        markNoticesSeen();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Vibrate on recent emergency
    useEffect(() => {
        if (!notices.length) return;
        const hasRecentEmergency = notices.some(n =>
            n.category === 'Emergency' &&
            new Date(n.created_at) > new Date(Date.now() - 48 * 60 * 60 * 1000)
        );
        if (hasRecentEmergency && !sessionStorage.getItem('cv_emergency_vibrated')) {
            navigator.vibrate && navigator.vibrate([200, 100, 200]);
            sessionStorage.setItem('cv_emergency_vibrated', '1');
        }
    }, [notices]);

    // Show sticky pinned bar when pinned card is scrolled out of view
    useEffect(() => {
        const pinnedNotice = notices.find(n => n.authority_type === 'Admin');
        if (!pinnedNotice || !pinnedCardRef.current) return;
        const obs = new IntersectionObserver(
            ([entry]) => setShowPinnedBar(!entry.isIntersecting),
            { threshold: 0 }
        );
        obs.observe(pinnedCardRef.current);
        return () => obs.disconnect();
    }, [notices]);

    // Infinite scroll
    useEffect(() => {
        if (observerRef.current) observerRef.current.disconnect();
        if (!sentinelRef.current || !hasMore || loading) return;
        observerRef.current = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) fetchNotices(false); },
            { rootMargin: '200px' }
        );
        observerRef.current.observe(sentinelRef.current);
        return () => observerRef.current?.disconnect();
    }, [hasMore, loading, fetchNotices]);

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
        const days = Math.floor((now - d) / 86400000);
        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    };

    const formatExpiry = (expiresAt, category) => {
        if (!expiresAt) return null;
        const exp = new Date(expiresAt);
        const diffMs = exp - new Date();
        if (diffMs <= 0) return null;
        const diffHours = diffMs / (1000 * 60 * 60);
        const diffDays = diffMs / (1000 * 60 * 60 * 24);
        if ((category === 'Emergency' || category === 'Maintenance') && diffHours <= 48) {
            const h = Math.round(diffHours);
            return `Expires in ${h} hour${h !== 1 ? 's' : ''}`;
        }
        if (category === 'General' || category === 'Announcement') {
            return `Active until ${exp.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: diffDays > 365 ? 'numeric' : undefined })}`;
        }
        if (diffDays <= 7) {
            const d = Math.round(diffDays);
            return `Expires in ${d} day${d !== 1 ? 's' : ''}`;
        }
        return null;
    };

    const pinnedNotice = notices.find(n => n.authority_type === 'Admin');
    let firstAdminSeen = false;

    return (
        <div className="min-h-screen bg-srec-background">
            <TopNav />

            {/* WhatsApp-style sticky pinned indicator */}
            {pinnedNotice && showPinnedBar && (
                <div
                    className="fixed top-14 left-0 right-0 z-40 flex justify-center pointer-events-none md:pl-20"
                >
                    <button
                        onClick={() => pinnedCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                        className="pointer-events-auto flex items-center gap-2 px-4 py-2 bg-srec-primary/95 backdrop-blur-sm text-white rounded-full shadow-lg shadow-green-900/20 text-xs font-semibold hover:bg-srec-primaryDark transition-colors animate-fadeIn"
                    >
                        <Pin size={11} className="flex-shrink-0" />
                        <span className="max-w-[200px] truncate">{pinnedNotice.title}</span>
                        <span className="text-white/60">↑</span>
                    </button>
                </div>
            )}

            <div ref={contentRef} className="max-w-2xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">

                {/* Header banner */}
                <div className="mb-5 rounded-2xl bg-gradient-to-br from-srec-primary via-green-800 to-emerald-700 px-5 py-5 shadow-md shadow-green-900/10 relative overflow-hidden">
                    <div className="absolute -top-6 -right-6 w-28 h-28 rounded-full bg-white/5 pointer-events-none" />
                    <div className="absolute -bottom-8 -right-2 w-20 h-20 rounded-full bg-white/5 pointer-events-none" />
                    <div className="flex items-center justify-between relative">
                        <div>
                            <p className="text-emerald-300/70 text-[10px] font-semibold uppercase tracking-[0.2em] mb-1">SREC Campus Voice</p>
                            <h1 className="text-xl font-bold text-white tracking-tight font-heading">Notice Board</h1>
                            <p className="text-green-300/80 text-xs mt-0.5">Official campus announcements</p>
                        </div>
                        <div className="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center">
                            <Bell size={20} className="text-white" />
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm">{error}</div>
                )}

                <div className="space-y-3">
                    {loading && notices.length === 0 ? (
                        [1, 2, 3].map(i => <Skeleton key={i} className="h-28 rounded-2xl" />)
                    ) : notices.length === 0 ? (
                        <div className="py-20 text-center">
                            <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                                <Inbox size={24} className="text-gray-300" />
                            </div>
                            <p className="text-sm font-semibold text-gray-600">No notices yet</p>
                            <p className="text-xs text-gray-400 mt-1">Check back later for campus announcements.</p>
                        </div>
                    ) : (
                        notices.map((notice) => {
                            const isFirstAdmin = notice.authority_type === 'Admin' && !firstAdminSeen;
                            if (isFirstAdmin) firstAdminSeen = true;
                            return (
                                <NoticeCard
                                    key={notice.id}
                                    notice={notice}
                                    onClick={() => setSelectedNotice(notice)}
                                    onOpenAttachment={openAttachment}
                                    attachLoading={attachLoading}
                                    formatDate={formatDate}
                                    formatExpiry={formatExpiry}
                                    formatAudience={formatAudience}
                                    cardRef={isFirstAdmin ? pinnedCardRef : undefined}
                                />
                            );
                        })
                    )}

                    {/* Infinite scroll sentinel */}
                    <div ref={sentinelRef} className="h-1" />

                    {loadingMore && (
                        <div className="flex justify-center py-4">
                            <div className="w-6 h-6 border-2 border-srec-primary border-t-transparent rounded-full animate-spin" />
                        </div>
                    )}

                    {!hasMore && notices.length > 0 && (
                        <p className="text-center text-xs text-gray-400 py-4">You've seen all notices</p>
                    )}
                </div>
            </div>

            {user?.role === 'Student' && <BottomNav />}

            {selectedNotice && (
                <NoticeDetailSheet
                    notice={selectedNotice}
                    onClose={() => setSelectedNotice(null)}
                    onOpenAttachment={openAttachment}
                    attachLoading={attachLoading}
                    formatDate={formatDate}
                    formatExpiry={formatExpiry}
                    formatAudience={formatAudience}
                />
            )}

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
