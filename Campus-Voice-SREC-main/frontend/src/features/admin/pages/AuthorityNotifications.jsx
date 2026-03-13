import React, { useState, useEffect } from 'react';
import { Card, EliteButton } from '../../../components/UI';
import { useAuth } from '../../../context/AuthContext';
import authorityService from '../../../services/authority.service';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import { Bell, Check, Trash2, AlertCircle, MessageSquare, CheckCircle } from 'lucide-react';

export default function AuthorityNotifications() {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [unreadOnly, setUnreadOnly] = useState(false);
    const [skip, setSkip] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const LIMIT = 20;

    useEffect(() => {
        fetchNotifications(true);
    }, [unreadOnly]);

    const fetchNotifications = async (reset = false) => {
        try {
            setLoading(true);
            const currentSkip = reset ? 0 : skip;
            // Using studentService as it's likely used for generic notifications or shared endpoints
            const data = await authorityService.getNotifications({
                skip: currentSkip,
                limit: LIMIT,
                unread_only: unreadOnly
            });

            if (data && Array.isArray(data.notifications)) {
                if (reset) {
                    setNotifications(data.notifications);
                    setSkip(LIMIT);
                } else {
                    setNotifications(prev => [...prev, ...data.notifications]);
                    setSkip(prev => prev + LIMIT);
                }
                if (data.notifications.length < LIMIT) {
                    setHasMore(false);
                } else {
                    setHasMore(true);
                }
            }
        } catch (error) {
            console.error("Failed to fetch notifications", error);
        } finally {
            setLoading(false);
        }
    };

    const handleMarkRead = async (id) => {
        try {
            await authorityService.markNotificationRead(id);
            setNotifications(prev => prev.map(n =>
                n.id === id ? { ...n, is_read: true } : n
            ));
        } catch (error) {
            console.error("Failed to mark read", error);
        }
    };

    const handleDelete = async (id) => {
        try {
            await authorityService.deleteNotification(id);
            setNotifications(prev => prev.filter(n => n.id !== id));
        } catch (error) {
            console.error("Failed to delete", error);
        }
    };

    const handleMarkAllRead = async () => {
        try {
            await authorityService.markAllNotificationsRead();
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch (error) {
            console.error("Failed to mark all read", error);
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'escalation': return <AlertCircle className="text-srec-danger" size={20} />;
            case 'complaint_resolved': return <CheckCircle className="text-srec-primary" size={20} />;
            case 'comment_added': return <MessageSquare className="text-blue-500" size={20} />;
            default: return <Bell className="text-srec-primary" size={20} />;
        }
    };

    return (
        <div className="flex min-h-screen bg-srec-background">
            <AuthoritySidebar className="hidden md:flex fixed inset-y-0 left-0 z-10" />

            <div className="flex-1 md:ml-64 flex flex-col min-w-0 transition-all duration-300">
                <AuthorityHeader />

                <main className="flex-1 p-6 sm:p-8 overflow-y-auto">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Notifications</h1>
                            <p className="text-sm text-gray-500 mt-1">Updates on your assigned complaints</p>
                        </div>
                        <div className="flex gap-2">
                            <EliteButton variant="outline" size="sm" onClick={() => setUnreadOnly(!unreadOnly)}>
                                {unreadOnly ? 'Show All' : 'Unread Only'}
                            </EliteButton>
                            <EliteButton variant="primary" size="sm" onClick={handleMarkAllRead}>
                                Mark All Read
                            </EliteButton>
                        </div>
                    </div>

                    <div className="space-y-3">
                        {notifications.length === 0 && !loading ? (
                            <div className="bg-white rounded-2xl p-12 text-center border border-gray-100 shadow-sm">
                                <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4 mx-auto text-gray-400">
                                    <Bell size={28} />
                                </div>
                                <h3 className="text-lg font-bold text-gray-900 mb-2">All caught up!</h3>
                                <p className="text-gray-500 mb-6 max-w-md mx-auto">
                                    You have no new notifications.
                                </p>
                                <EliteButton variant="outline" onClick={() => fetchNotifications(true)}>
                                    Refresh
                                </EliteButton>
                            </div>
                        ) : (
                            notifications.map((n) => (
                                <div
                                    key={n.id}
                                    className={`bg-white p-5 rounded-2xl border transition-all duration-200 flex items-start gap-4 ${n.is_read ? 'border-gray-100 bg-gray-50/50' : 'border-srec-primary/20 shadow-sm'}`}
                                >
                                    <div className={`p-3 rounded-xl shrink-0 ${n.is_read ? 'bg-gray-100' : 'bg-srec-primary/10'}`}>
                                        {getIcon(n.notification_type)}
                                    </div>

                                    <div className="flex-1 min-w-0 pt-1">
                                        <div className="flex items-center justify-between gap-2 mb-1">
                                            <span className="text-xs font-bold uppercase tracking-wider text-srec-primary">
                                                {n.notification_type?.replace(/_/g, ' ')}
                                            </span>
                                            <span className="text-xs text-gray-400 whitespace-nowrap">
                                                {new Date(n.created_at).toLocaleDateString()} {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <p className={`text-sm leading-relaxed ${n.is_read ? 'text-gray-500' : 'text-gray-900 font-medium'}`}>
                                            {n.message}
                                        </p>
                                        {n.complaint_title && (
                                            <p className="text-xs text-gray-400 mt-2 pl-3 border-l-2 border-gray-200">
                                                Ref: {n.complaint_title}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex flex-col gap-2 shrink-0">
                                        {!n.is_read && (
                                            <EliteButton
                                                size="sm"
                                                variant="success"
                                                className="w-8 h-8 !p-0 flex items-center justify-center rounded-lg"
                                                onClick={() => handleMarkRead(n.id)}
                                                title="Mark as read"
                                            >
                                                <Check size={16} />
                                            </EliteButton>
                                        )}
                                        <EliteButton
                                            size="sm"
                                            variant="danger"
                                            className="w-8 h-8 !p-0 flex items-center justify-center rounded-lg bg-red-50 text-red-500 border-red-50 hover:bg-red-100"
                                            onClick={() => handleDelete(n.id)}
                                            title="Delete"
                                        >
                                            <Trash2 size={16} />
                                        </EliteButton>
                                    </div>
                                </div>
                            ))
                        )}

                        {loading && (
                            <div className="text-center py-8">
                                <div className="w-8 h-8 border-2 border-srec-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
                            </div>
                        )}

                        {!loading && hasMore && notifications.length > 0 && (
                            <EliteButton variant="outline" className="w-full mt-4" onClick={() => fetchNotifications(false)}>
                                Load More
                            </EliteButton>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
}
