import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Bell, User, LogOut, CheckCheck, ShieldCheck, ArrowUpRight } from 'lucide-react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import authorityService from '../../../services/authority.service';

const PAGE_TITLES = {
  '/authority-dashboard': 'Dashboard',
  '/authority-notices': 'Notices',
  '/authority-notifications': 'Notifications',
  '/authority-profile': 'Profile',
  '/admin': 'Dashboard',
  '/admin/complaints': 'All Complaints',
  '/admin/authorities': 'Manage Authorities',
  '/admin/escalations': 'Escalations',
  '/admin/departments': 'Categories',
  '/admin/departments/list': 'Departments',
  '/admin/notifications': 'Notifications',
  '/admin/profile': 'Profile',
};

const NOTIFICATION_TYPE_LABELS = {
  complaint_assigned: 'Complaint assigned to you',
  escalation: 'Complaint escalated to you',
  status_updated: 'Complaint status updated',
  new_complaint: 'New complaint received',
};

const AuthorityHeader = ({ className = '' }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Profile dropdown
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Notification dropdown
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);
  const [markingRead, setMarkingRead] = useState(false);

  const pageTitle = PAGE_TITLES[location.pathname] || 'Overview';

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      setNotifLoading(true);
      const data = await authorityService.getNotifications({ skip: 0, limit: 10 });
      const list = Array.isArray(data) ? data : data?.notifications || [];
      setNotifications(list);
      const unread = list.filter(n => !n.is_read).length;
      setUnreadCount(unread);
    } catch (err) {
      console.log('Could not fetch authority notifications:', err.message);
    } finally {
      setNotifLoading(false);
    }
  }, []);

  // On mount and every 30 seconds, fetch notifications
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close notification dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close dropdowns on route change
  useEffect(() => {
    setMenuOpen(false);
    setNotifOpen(false);
  }, [location.pathname]);

  const handleMarkAllRead = async () => {
    try {
      setMarkingRead(true);
      await authorityService.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.log('Could not mark notifications read:', err.message);
    } finally {
      setMarkingRead(false);
    }
  };

  const handleNotifClick = (notif) => {
    setNotifOpen(false);
    if (notif.complaint_id) {
      navigate(`/complaint/${notif.complaint_id}`);
    } else {
      if (user?.role === 'Admin') {
        navigate('/admin/notifications');
      } else {
        navigate('/authority-notifications');
      }
    }
  };

  const handleBellClick = () => {
    setNotifOpen(v => !v);
    if (!notifOpen) {
      fetchNotifications();
    }
  };

  const formatTimeAgo = (ts) => {
    if (!ts) return '';
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <header className={`h-14 sm:h-16 border-b border-gray-100 bg-white flex items-center justify-between px-4 sm:px-6 md:px-8 shadow-sm relative z-30 ${className}`}>
      <div className="flex items-center gap-4 min-w-0">
        <h1 className="text-base sm:text-lg font-semibold text-gray-900 truncate">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Authority Info */}
        <div className="text-right hidden sm:block mr-2">
          <p className="text-sm font-semibold text-gray-900">{user?.name || 'Authority'}</p>
          <p className="text-xs text-srec-primary font-medium">{user?.authority_type || user?.role || 'Authority'}</p>
        </div>

        {/* Notification Bell with badge and dropdown */}
        <div ref={notifRef} className="relative">
          <button
            onClick={handleBellClick}
            className="relative p-2 rounded-full text-gray-400 hover:bg-gray-50 hover:text-srec-primary transition-colors"
            aria-label="Notifications"
          >
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notification Dropdown */}
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] border border-gray-100 z-[100] overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50/50">
                <h3 className="text-sm font-bold text-gray-900">Notifications</h3>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    disabled={markingRead}
                    className="flex items-center gap-1 text-xs text-srec-primary hover:text-srec-primaryHover font-semibold transition-colors disabled:opacity-50"
                  >
                    <CheckCheck size={13} />
                    Mark all read
                  </button>
                )}
              </div>

              {/* Notification list */}
              <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
                {notifLoading ? (
                  <div className="py-8 text-center text-sm text-gray-400">Loading...</div>
                ) : notifications.length === 0 ? (
                  <div className="py-8 text-center">
                    <ShieldCheck size={28} className="mx-auto text-gray-300 mb-2" />
                    <p className="text-sm text-gray-400">No notifications yet</p>
                  </div>
                ) : (
                  notifications.map((notif, idx) => (
                    <button
                      key={notif.id || idx}
                      onClick={() => handleNotifClick(notif)}
                      className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${!notif.is_read ? 'bg-srec-primary/5' : ''}`}
                    >
                      <div className="flex items-start gap-2.5">
                        {!notif.is_read && (
                          <span className="mt-1.5 w-2 h-2 rounded-full bg-srec-primary flex-shrink-0" />
                        )}
                        <div className={`flex-1 min-w-0 ${notif.is_read ? 'pl-[18px]' : ''}`}>
                          <p className="text-xs font-semibold text-gray-800 truncate">
                            {NOTIFICATION_TYPE_LABELS[notif.notification_type] || notif.notification_type || 'Notification'}
                          </p>
                          <p className="text-xs text-gray-500 leading-relaxed mt-0.5 line-clamp-2">
                            {notif.message || notif.content || 'View details'}
                          </p>
                          <p className="text-[10px] text-gray-400 mt-1">{formatTimeAgo(notif.created_at)}</p>
                        </div>
                        <ArrowUpRight size={14} className="text-gray-300 flex-shrink-0 mt-0.5" />
                      </div>
                    </button>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-gray-100 px-4 py-2.5 bg-gray-50/50">
                <button
                  onClick={() => {
                    setNotifOpen(false);
                    navigate(user?.role === 'Admin' ? '/admin/notifications' : '/authority-notifications');
                  }}
                  className="w-full text-center text-xs text-srec-primary font-semibold hover:text-srec-primaryHover transition-colors"
                >
                  View all notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Profile Icon with click dropdown */}
        <div ref={menuRef} className="relative">
          <button
            onClick={() => setMenuOpen(v => !v)}
            className="w-9 h-9 bg-srec-primary/10 rounded-full flex items-center justify-center border border-srec-primary/20 text-srec-primary shadow-sm hover:bg-srec-primary/20 transition-colors"
            aria-label="Profile menu"
          >
            <User size={18} />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] border border-gray-100 py-1 z-[100]">
              <div className="px-4 py-3 border-b border-gray-50">
                <p className="text-sm font-semibold text-gray-900 truncate">{user?.name || 'Authority'}</p>
                <p className="text-xs text-srec-primary font-medium">{user?.authority_type || user?.role}</p>
              </div>
              <Link
                to={user?.role === 'Admin' ? '/admin/profile' : '/authority-profile'}
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <User size={15} /> Profile
              </Link>
              <button
                onClick={() => { setMenuOpen(false); logout(); navigate('/login'); }}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors text-left"
              >
                <LogOut size={15} /> Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default AuthorityHeader;
