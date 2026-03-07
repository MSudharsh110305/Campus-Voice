import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import studentService from '../services/student.service';

const NotificationContext = createContext({ unreadCount: 0, unreadNoticeCount: 0, refresh: () => {}, markNoticesSeen: () => {} });

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadNoticeCount, setUnreadNoticeCount] = useState(0);
  const intervalRef = useRef(null);

  const fetchCount = useCallback(async () => {
    try {
      const data = await studentService.getUnreadCount();
      const count = data.unread_count || 0;
      setUnreadCount(count);
      // Feature 5: Badging API — update app badge with unread count
      if ('setAppBadge' in navigator) {
        if (count > 0) {
          navigator.setAppBadge(count).catch(() => {});
        } else {
          navigator.clearAppBadge().catch(() => {});
        }
      }
    } catch {
      // Silently ignore — don't spam console with polling errors
    }
  }, []);

  const fetchNoticeCount = useCallback(async () => {
    try {
      const lastSeen = localStorage.getItem('cv_notices_seen_at');
      const data = await studentService.getNotices({ skip: 0, limit: 20 });
      const notices = data?.notices || (Array.isArray(data) ? data : []);
      if (!notices.length) { setUnreadNoticeCount(0); return; }
      if (!lastSeen) {
        setUnreadNoticeCount(notices.length);
        return;
      }
      const seenAt = new Date(lastSeen).getTime();
      const newCount = notices.filter(n => new Date(n.created_at).getTime() > seenAt).length;
      setUnreadNoticeCount(newCount);
    } catch {
      // Silently ignore
    }
  }, []);

  const markNoticesSeen = useCallback(() => {
    localStorage.setItem('cv_notices_seen_at', new Date().toISOString());
    setUnreadNoticeCount(0);
  }, []);

  const startPolling = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      fetchCount();
      fetchNoticeCount();
    }, 30000); // every 30 seconds
  }, [fetchCount, fetchNoticeCount]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (user?.role !== 'Student') {
      setUnreadCount(0);
      setUnreadNoticeCount(0);
      stopPolling();
      // Clear badge when not logged in as student
      if ('clearAppBadge' in navigator) {
        navigator.clearAppBadge().catch(() => {});
      }
      return;
    }

    // Initial fetch
    fetchCount();
    fetchNoticeCount();
    startPolling();

    // Pause when tab hidden, resume when visible (Page Visibility API)
    const onVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        fetchCount();
        fetchNoticeCount();
        startPolling();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [user?.role, fetchCount, fetchNoticeCount, startPolling, stopPolling]);

  return (
    <NotificationContext.Provider value={{ unreadCount, unreadNoticeCount, refresh: fetchCount, markNoticesSeen }}>
      {children}
    </NotificationContext.Provider>
  );
}

export const useNotifications = () => useContext(NotificationContext);
