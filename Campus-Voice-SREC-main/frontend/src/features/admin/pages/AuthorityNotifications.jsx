import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../../context/AuthContext';
import authorityService from '../../../services/authority.service';
import AuthoritySidebar from '../components/AuthoritySidebar';
import AuthorityHeader from '../components/AuthorityHeader';
import {
  Bell, AlertCircle, MessageSquare, CheckCircle, Trash2,
  ArrowUpCircle, FileText, Megaphone,
} from 'lucide-react';

// ── Helpers ──────────────────────────────────────────────────────────────────
function timeAgo(dateStr) {
  const s = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  if (s < 604800) return `${Math.floor(s / 86400)}d`;
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

const TYPE_META = {
  escalation:         { Icon: ArrowUpCircle,  bg: 'bg-amber-100',   color: 'text-amber-500' },
  complaint_resolved: { Icon: CheckCircle,    bg: 'bg-emerald-100', color: 'text-emerald-500' },
  complaint_assigned: { Icon: Bell,           bg: 'bg-blue-100',    color: 'text-blue-500' },
  comment_added:      { Icon: MessageSquare,  bg: 'bg-indigo-100',  color: 'text-indigo-500' },
  complaint_spam:     { Icon: AlertCircle,    bg: 'bg-red-100',     color: 'text-red-500' },
  petition_approved:  { Icon: FileText,       bg: 'bg-purple-100',  color: 'text-purple-500' },
  petition_milestone: { Icon: Megaphone,      bg: 'bg-violet-100',  color: 'text-violet-500' },
  default:            { Icon: Bell,           bg: 'bg-gray-100',    color: 'text-gray-400' },
};

function getTypeMeta(type) {
  return TYPE_META[type] || TYPE_META.default;
}

function NotifRow({ n, onDelete }) {
  const { Icon, bg, color } = getTypeMeta(n.notification_type);
  return (
    <div className={`group flex items-center gap-3 px-5 py-4 border-b border-gray-100 last:border-0 transition-colors ${
      n.is_read ? 'bg-white' : 'bg-srec-primary/[0.03]'
    }`}>
      <div className={`w-11 h-11 rounded-full flex-shrink-0 flex items-center justify-center ${bg}`}>
        <Icon size={18} className={color} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            {(n.notification_type || 'notification').replace(/_/g, ' ')}
          </span>
        </div>
        <p className={`text-sm leading-snug ${n.is_read ? 'text-gray-600' : 'font-semibold text-gray-900'}`}>
          {n.message}
        </p>
        {n.complaint_title && (
          <p className="text-[11px] text-gray-400 mt-1 pl-2 border-l-2 border-gray-200 truncate">
            {n.complaint_title}
          </p>
        )}
        <span className="text-[11px] text-gray-400 mt-0.5 block">{timeAgo(n.created_at)}</span>
      </div>

      {!n.is_read && <div className="w-2.5 h-2.5 rounded-full bg-srec-primary flex-shrink-0" />}

      <button
        onClick={() => onDelete(n.id)}
        className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-300 hover:text-red-400 transition-all rounded-lg flex-shrink-0"
        title="Delete"
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function AuthorityNotifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const markedRef = useRef(false);
  const LIMIT = 20;

  const fetchNotifications = useCallback(async (reset = false) => {
    try {
      setLoading(true);
      const currentSkip = reset ? 0 : skip;
      const data = await authorityService.getNotifications({ skip: currentSkip, limit: LIMIT });
      if (data && Array.isArray(data.notifications)) {
        if (reset) {
          setNotifications(data.notifications);
          setSkip(LIMIT);
        } else {
          setNotifications(prev => [...prev, ...data.notifications]);
          setSkip(prev => prev + LIMIT);
        }
        setHasMore(data.notifications.length >= LIMIT);
      }
    } catch (err) {
      console.error('Failed to fetch notifications', err);
    } finally {
      setLoading(false);
    }
  }, [skip]);

  useEffect(() => {
    fetchNotifications(true);
    if (!markedRef.current) {
      markedRef.current = true;
      authorityService.markAllNotificationsRead().catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (id) => {
    try {
      await authorityService.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      console.error('Failed to delete', err);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="flex min-h-screen bg-srec-background">
      <AuthoritySidebar className="hidden md:flex fixed inset-y-0 left-0 z-10" />

      <div className="flex-1 md:ml-64 flex flex-col min-w-0 transition-all duration-300">
        <AuthorityHeader />

        <main className="flex-1 p-6 sm:p-8 overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Notifications</h1>
              {unreadCount > 0 && (
                <p className="text-sm text-srec-primary mt-0.5">{unreadCount} new</p>
              )}
            </div>
            <button
              onClick={() => fetchNotifications(true)}
              className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              Refresh
            </button>
          </div>

          {/* List */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden max-w-3xl">
            {loading && notifications.length === 0 ? (
              <div className="py-12 text-center">
                <div className="w-8 h-8 border-2 border-srec-primary border-t-transparent rounded-full animate-spin mx-auto" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-16 text-center">
                <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4 mx-auto text-gray-300">
                  <Bell size={28} />
                </div>
                <h3 className="text-lg font-bold text-gray-900">All caught up!</h3>
                <p className="text-gray-400 text-sm mt-1">No new notifications.</p>
              </div>
            ) : (
              <>
                {notifications.map(n => (
                  <NotifRow key={n.id} n={n} onDelete={handleDelete} />
                ))}
                {loading && (
                  <div className="py-4 text-center">
                    <div className="w-6 h-6 border-2 border-srec-primary border-t-transparent rounded-full animate-spin mx-auto" />
                  </div>
                )}
                {!loading && hasMore && (
                  <button
                    onClick={() => fetchNotifications(false)}
                    className="w-full py-3.5 text-sm text-srec-primary font-medium hover:bg-gray-50 transition-colors"
                  >
                    Load more
                  </button>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
