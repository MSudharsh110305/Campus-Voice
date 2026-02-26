import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, User, LogOut } from 'lucide-react';

export default function AdminHeader({ onMenuClick }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [menuOpen, setMenuOpen] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const menuRef = useRef(null);

    useEffect(() => {
        const handler = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    useEffect(() => {
        const fetchUnread = () => {
            const token = localStorage.getItem('token');
            if (!token) return;
            fetch('/api/admin/notifications/unread-count', { headers: { Authorization: `Bearer ${token}` } })
                .then(r => r.ok ? r.json() : null)
                .then(data => { if (data) setUnreadCount(data.unread_count ?? data.count ?? 0); })
                .catch(() => {});
        };
        fetchUnread();
        const interval = setInterval(fetchUnread, 60000);
        return () => clearInterval(interval);
    }, []);

    return (
        <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 sticky top-0 z-20">
            <div className="flex items-center gap-4">
                <button
                    onClick={onMenuClick}
                    className="md:hidden p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
            </div>

            <div className="flex items-center gap-3">
                <button
                    onClick={() => navigate('/admin/notifications')}
                    className="relative p-2 text-gray-400 hover:text-srec-primary hover:bg-gray-50 rounded-full transition-colors"
                    aria-label="Notifications"
                >
                    <Bell size={20} />
                    {unreadCount > 0 && (
                        <span className="absolute top-1 right-1 min-w-[16px] h-4 px-0.5 bg-srec-danger text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white">
                            {unreadCount > 9 ? '9+' : unreadCount}
                        </span>
                    )}
                </button>

                <div className="h-6 w-px bg-gray-200 mx-1"></div>

                <div className="text-right hidden sm:block">
                    <div className="text-sm font-semibold text-gray-900">{user?.name || 'Admin'}</div>
                    <div className="text-xs text-srec-primary font-medium">Administrator</div>
                </div>

                <div ref={menuRef} className="relative">
                    <button
                        onClick={() => setMenuOpen(v => !v)}
                        className="w-9 h-9 bg-srec-primary/10 text-srec-primary rounded-full flex items-center justify-center border border-srec-primary/20 shadow-sm hover:bg-srec-primary/20 transition-colors"
                        aria-label="Profile menu"
                    >
                        <User size={18} />
                    </button>

                    {menuOpen && (
                        <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] border border-gray-100 py-1 z-[100]">
                            <div className="px-4 py-3 border-b border-gray-50">
                                <p className="text-sm font-medium text-gray-900 truncate">{user?.name || 'Admin'}</p>
                                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                            </div>
                            <Link
                                to="/admin/profile"
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
}
