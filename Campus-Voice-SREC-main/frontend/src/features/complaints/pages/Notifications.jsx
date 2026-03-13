import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TopNav } from '../../../components/Navbars';
import BottomNav from '../../../components/BottomNav';
import { useAuth } from '../../../context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import studentService from '../../../services/student.service';
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
  comment_added:      { Icon: MessageSquare,  bg: 'bg-blue-100',    color: 'text-blue-500' },
  complaint_spam:     { Icon: AlertCircle,    bg: 'bg-red-100',     color: 'text-red-500' },
  petition_approved:  { Icon: FileText,       bg: 'bg-purple-100',  color: 'text-purple-500' },
  petition_milestone: { Icon: Megaphone,      bg: 'bg-violet-100',  color: 'text-violet-500' },
  default:            { Icon: Bell,           bg: 'bg-gray-100',    color: 'text-gray-500' },
};

function getTypeMeta(type) {
  return TYPE_META[type] || TYPE_META.default;
}

// ── Notification Row ─────────────────────────────────────────────────────────
function NotifRow({ n, onDelete }) {
  const { Icon, bg, color } = getTypeMeta(n.notification_type);
  return (
    <div className={`group flex items-center gap-3 px-4 py-3.5 border-b border-gray-100 last:border-0 transition-colors ${
      n.is_read ? 'bg-white' : 'bg-srec-primary/[0.03]'
    }`}>
      {/* Icon circle */}
      <div className={`w-11 h-11 rounded-full flex-shrink-0 flex items-center justify-center ${bg}`}>
        <Icon size={18} className={color} />
      </div>

      {/* Message + time */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm leading-snug ${n.is_read ? 'text-gray-600' : 'font-semibold text-gray-900'}`}>
          {n.message}
        </p>
        <span className="text-[11px] text-gray-400">{timeAgo(n.created_at)}</span>
      </div>

      {/* Unread dot */}
      {!n.is_read && <div className="w-2.5 h-2.5 rounded-full bg-srec-primary flex-shrink-0" />}

      {/* Delete */}
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
export default function Notifications() {
  const { user } = useAuth();
  const { markAllRead } = useNotifications();
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
      const data = await studentService.getNotifications({ skip: currentSkip, limit: LIMIT });
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

  // On mount: fetch + auto-mark all as read (like Instagram)
  useEffect(() => {
    fetchNotifications(true);
    if (!markedRef.current) {
      markedRef.current = true;
      markAllRead().catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (id) => {
    try {
      await studentService.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      console.error('Failed to delete', err);
    }
  };

  return (
    <div className="min-h-screen bg-srec-background">
      <TopNav />
      <div className="animate-fadeIn max-w-2xl mx-auto px-4 pt-4 pb-24 md:pl-24 transition-all duration-300">

        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Notifications</h1>
          <button
            onClick={() => fetchNotifications(true)}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* List */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {loading && notifications.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">Loading…</div>
          ) : notifications.length === 0 ? (
            <div className="py-16 text-center">
              <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center mb-3 mx-auto text-gray-300">
                <Bell size={28} />
              </div>
              <p className="text-base font-semibold text-gray-900">All caught up!</p>
              <p className="text-gray-400 text-sm mt-1">No notifications yet.</p>
            </div>
          ) : (
            <>
              {notifications.map(n => (
                <NotifRow key={n.id} n={n} onDelete={handleDelete} />
              ))}

              {loading && (
                <div className="py-4 text-center text-gray-400 text-sm">Loading…</div>
              )}

              {!loading && hasMore && (
                <button
                  onClick={() => fetchNotifications(false)}
                  className="w-full py-3 text-sm text-srec-primary font-medium hover:bg-gray-50 transition-colors"
                >
                  Load more
                </button>
              )}
            </>
          )}
        </div>

      </div>
      {user?.role === 'Student' && <BottomNav />}
    </div>
  );
}
