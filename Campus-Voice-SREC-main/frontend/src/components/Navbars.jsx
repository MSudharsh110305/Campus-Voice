import React from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { Bell, User, LogOut, Gamepad2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { useState } from 'react';
import OfflineGame from './OfflineGame';

export function TopNav() {
  const { user, logout } = useAuth();
  const { unreadCount, markAllRead } = useNotifications();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'Admin';
  const isStudent = user?.role === 'Student';
  const [showGame, setShowGame] = useState(false);

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U';

  return (
    <>
    <div className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-srec-borderLight shadow-soft">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between min-w-0">
        <Link to={isAdmin ? '/admin' : '/'} className="flex items-center gap-2 sm:gap-2.5 group min-w-0 flex-shrink-0">
          <div className="w-8 h-8 flex-shrink-0 rounded-lg bg-gradient-to-br from-srec-primaryLight to-srec-primary flex items-center justify-center text-white font-bold text-sm shadow-md shadow-srec-primary/15 group-hover:scale-105 transition-transform duration-200">
            CV
          </div>
          <span className="font-bold text-srec-textPrimary tracking-tight text-base sm:text-lg group-hover:text-srec-primary transition-colors duration-200 truncate max-w-[120px] sm:max-w-none">CampusVoice</span>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2 text-sm font-medium flex-shrink-0">
          {isAdmin ? (
            <Link to="/admin" className={`text-base font-semibold transition-colors ${location.pathname === '/admin' ? 'text-srec-primary' : 'text-srec-textSecondary hover:text-srec-textPrimary'}`}>Dashboard</Link>
          ) : isStudent ? (
            <>
              {/* Notification Bell */}
              <button
                onClick={() => { if (unreadCount > 0) markAllRead(); navigate('/notifications'); }}
                className="relative p-2 rounded-full hover:bg-srec-primarySoft transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-srec-primary"
                aria-label="Notifications"
              >
                <Bell
                  size={20}
                  className={unreadCount > 0 ? 'text-srec-primary' : 'text-srec-textMuted'}
                />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 min-w-[16px] h-4 px-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Game shortcut */}
              <button
                onClick={() => setShowGame(true)}
                className="p-2 rounded-full hover:bg-srec-primarySoft transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-srec-primary"
                aria-label="Play game"
                title="Campus Dash"
              >
                <Gamepad2 size={20} className="text-srec-textMuted hover:text-srec-primary transition-colors" />
              </button>

              {/* Profile Avatar with dropdown */}
              <div className="relative group">
                <button
                  className="w-9 h-9 rounded-full bg-srec-primary text-white text-sm font-bold flex items-center justify-center shadow-card hover:shadow-card-hover hover:bg-srec-primaryHover transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-srec-primary will-change-transform"
                  aria-label="Profile"
                >
                  {initials}
                </button>
                {/* Dropdown */}
                <div className="absolute right-0 mt-2 w-48 glass rounded-2xl shadow-elevated border border-srec-borderLight py-1.5 invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-200 origin-top-right z-50 animate-scale-in">
                  <div className="px-4 py-2.5 border-b border-srec-borderLight">
                    <p className="text-xs font-semibold text-srec-textPrimary truncate">{user?.name}</p>
                    <p className="text-[11px] text-srec-textMuted truncate">{user?.roll_no}</p>
                  </div>
                  <Link to="/profile" className="flex items-center gap-2 px-4 py-2 text-sm text-srec-textSecondary hover:bg-srec-backgroundAlt hover:text-srec-textPrimary transition-colors">
                    <User size={14} /> Profile
                  </Link>
                  <button
                    onClick={() => { logout(); navigate('/login'); }}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 text-left transition-colors"
                  >
                    <LogOut size={14} /> Sign Out
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </nav>
      </div>
    </div>
    {showGame && <OfflineGame onClose={() => setShowGame(false)} />}
    </>
  );
}

export function AdminSidebar({ children }) {
  return (
    <div className="min-h-screen sm:grid sm:grid-cols-[220px_1fr]">
      <aside className="hidden sm:block border-r border-srec-border p-4">
        <div className="font-semibold text-gray-900 mb-4">Campus Voice</div>
        <nav className="space-y-2 text-sm">
          <Link to="/admin" className="block text-gray-600 hover:text-gray-900">Dashboard</Link>
        </nav>
      </aside>
      <main>{children}</main>
    </div>
  );
}
