import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import studentService from '../services/student.service';

const NotificationContext = createContext({ unreadCount: 0, unreadNoticeCount: 0, refresh: () => {}, markNoticesSeen: () => {}, markAllRead: async () => {} });

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadNoticeCount, setUnreadNoticeCount] = useState(0);
  const intervalRef = useRef(null);
  const prevCountRef = useRef(0);

  const fetchCount = useCallback(async () => {
    try {
      const data = await studentService.getUnreadCount();
      const count = data.unread_count || 0;
      setUnreadCount((prev) => {
        if (count > prev && prev !== 0) {
          // New notification arrived — let pages know so they can refresh data
          window.dispatchEvent(new CustomEvent('cv:new-notification', { detail: { count } }));
        }
        prevCountRef.current = count;
        return count;
      });
      // Badging API — update app badge with unread count
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

  const markAllRead = useCallback(async () => {
    try {
      await studentService.markAllNotificationsRead();
      setUnreadCount(0);
      if ('clearAppBadge' in navigator) navigator.clearAppBadge().catch(() => {});
    } catch {
      // Non-fatal — badge just won't clear until next poll
    }
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

  // BroadcastChannel: receive push-received signal from Service Worker
  // so we immediately refresh counts when a push arrives (even if tab is open)
  useEffect(() => {
    if (!('BroadcastChannel' in window)) return;
    const bc = new BroadcastChannel('cv-notifications');
    bc.onmessage = (e) => {
      if (e.data?.type === 'PUSH_RECEIVED') {
        fetchCount();
        fetchNoticeCount();
      }
    };
    return () => bc.close();
  }, [fetchCount, fetchNoticeCount]);

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
    <NotificationContext.Provider value={{ unreadCount, unreadNoticeCount, refresh: fetchCount, markNoticesSeen, markAllRead }}>
      {children}
    </NotificationContext.Provider>
  );
}

export const useNotifications = () => useContext(NotificationContext);
