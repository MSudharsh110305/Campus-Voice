import React, { useState, useEffect } from 'react';
import authorityService from '../../../services/authority.service';
import { EliteButton } from '../../../components/UI';
import { Bell, Check, Trash2, AlertCircle, MessageSquare, CheckCircle, ArrowUpCircle } from 'lucide-react';

export default function AdminNotifications() {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [unreadOnly, setUnreadOnly] = useState(false);

    useEffect(() => {
        fetchNotifications();
    }, [unreadOnly]);

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const data = await authorityService.getNotifications({ unread_only: unreadOnly, limit: 50 });
            setNotifications(data.notifications || []);
        } catch (err) {
            console.error("Failed to load admin notifications", err);
        } finally {
            setLoading(false);
        }
    };

    const handleMarkRead = async (id) => {
        try {
            await authorityService.markNotificationRead(id);
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        } catch (e) { console.error(e); }
    };

    const handleMarkAllRead = async () => {
        try {
            await authorityService.markAllNotificationsRead();
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch (e) { console.error(e); }
    };

    const handleDelete = async (id) => {
        try {
            await authorityService.deleteNotification(id);
            setNotifications(prev => prev.filter(n => n.id !== id));
        } catch (e) { console.error(e); }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'escalation': return <ArrowUpCircle className="text-amber-500" size={20} />;
            case 'complaint_resolved': return <CheckCircle className="text-green-500" size={20} />;
            case 'complaint_assigned': return <Bell className="text-srec-primary" size={20} />;
            case 'complaint_update': return <MessageSquare className="text-blue-500" size={20} />;
            default: return <Bell className="text-srec-primary" size={20} />;
        }
    };

    const unreadCount = notifications.filter(n => !n.is_read).length;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
                    {unreadCount > 0 && (
                        <p className="text-sm text-srec-primary mt-0.5">{unreadCount} unread</p>
                    )}
                </div>
                <div className="flex gap-2">
                    <EliteButton variant="outline" size="sm" onClick={() => setUnreadOnly(!unreadOnly)}>
                        {unreadOnly ? 'Show All' : 'Unread Only'}
                    </EliteButton>
                    {unreadCount > 0 && (
                        <EliteButton variant="primary" size="sm" onClick={handleMarkAllRead}>
                            Mark All Read
                        </EliteButton>
                    )}
                    <EliteButton variant="ghost" size="sm" onClick={fetchNotifications}>Refresh</EliteButton>
                </div>
            </div>

            <div className="space-y-3">
                {loading ? (
                    <div className="text-center py-12">
                        <div className="w-8 h-8 border-2 border-srec-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
                    </div>
                ) : notifications.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-2xl border border-gray-100">
                        <Bell className="mx-auto text-gray-300 mb-3" size={32} />
                        <p className="text-gray-500 font-medium">No notifications</p>
                        <p className="text-xs text-gray-400 mt-1">Complaint assignments and escalations will appear here</p>
                    </div>
                ) : (
                    notifications.map(n => (
                        <div
                            key={n.id}
                            className={`bg-white p-4 rounded-xl border flex items-start gap-4 transition-all ${n.is_read ? 'border-gray-100' : 'border-srec-primary/20 shadow-sm'}`}
                        >
                            <div className={`p-2 rounded-lg shrink-0 ${n.is_read ? 'bg-gray-100' : 'bg-srec-primary/10'}`}>
                                {getIcon(n.notification_type)}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-xs font-bold uppercase tracking-wider text-srec-primary">
                                        {n.notification_type?.replace(/_/g, ' ')}
                                    </span>
                                    {!n.is_read && (
                                        <span className="w-2 h-2 rounded-full bg-srec-primary inline-block"></span>
                                    )}
                                </div>
                                <p className={`text-sm ${n.is_read ? 'text-gray-600' : 'text-gray-900 font-medium'}`}>{n.message}</p>
                                <span className="text-xs text-gray-400 mt-1 block">{new Date(n.created_at).toLocaleString()}</span>
                            </div>
                            <div className="flex gap-1 shrink-0">
                                {!n.is_read && (
                                    <button
                                        onClick={() => handleMarkRead(n.id)}
                                        className="p-1.5 text-srec-primary hover:bg-srec-primary/10 rounded-lg transition-colors"
                                        title="Mark as read"
                                    >
                                        <Check size={16} />
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDelete(n.id)}
                                    className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
