import React, { useState, useEffect } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { EliteButton, Skeleton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import studentService from '../../../services/student.service';
import { Megaphone, Calendar, AlertTriangle, Info, Wrench, RefreshCw, Users } from 'lucide-react';

// Category config: icon + color palette
const CATEGORY_CONFIG = {
    Emergency:      { icon: AlertTriangle, color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-l-red-500',   badge: 'bg-red-100 text-red-700' },
    Announcement:   { icon: Megaphone,    color: 'text-blue-600',   bg: 'bg-blue-50',   border: 'border-l-blue-500',  badge: 'bg-blue-100 text-blue-700' },
    'Policy Change':{ icon: Info,         color: 'text-amber-600',  bg: 'bg-amber-50',  border: 'border-l-amber-500', badge: 'bg-amber-100 text-amber-700' },
    Event:          { icon: Calendar,     color: 'text-green-600',  bg: 'bg-green-50',  border: 'border-l-green-500', badge: 'bg-green-100 text-green-700' },
    Maintenance:    { icon: Wrench,       color: 'text-gray-600',   bg: 'bg-gray-50',   border: 'border-l-gray-400',  badge: 'bg-gray-100 text-gray-600' },
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
    const LIMIT = 20;

    useEffect(() => {
        fetchNotices(true);
        markNoticesSeen();
    }, []);

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

    return (
        <div className="min-h-screen bg-srec-background">
            <TopNav />
            <div className="max-w-2xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                    <div>
                        <h1 className="text-xl font-bold text-gray-900">Notice Board</h1>
                        <p className="text-xs text-gray-400 mt-0.5">Official campus announcements</p>
                    </div>
                    <button
                        onClick={() => fetchNotices(true)}
                        className="p-2 rounded-xl text-gray-400 hover:text-srec-primary hover:bg-srec-primary/5 transition-colors"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    </button>
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

                            return (
                                <div
                                    key={notice.id}
                                    className={`bg-white rounded-xl border border-gray-100 border-l-4 ${cfg.border} overflow-hidden shadow-sm hover:shadow-md transition-shadow`}
                                >
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
                                        <p className={`text-sm font-semibold leading-snug mb-1 ${isUrgent ? 'text-gray-900' : 'text-gray-800'}`}>
                                            {notice.title}
                                        </p>

                                        {/* Content */}
                                        <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">
                                            {notice.content}
                                        </p>

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

                                    {/* Expiry warning strip */}
                                    {notice.expires_at && new Date(notice.expires_at) < new Date(Date.now() + 24 * 60 * 60 * 1000) && (
                                        <div className="px-4 py-1.5 bg-amber-50 border-t border-amber-100 text-[10px] text-amber-700 font-medium">
                                            ⏰ Expires {new Date(notice.expires_at).toLocaleDateString()}
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
        </div>
    );
}
