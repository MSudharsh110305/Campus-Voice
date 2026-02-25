import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Home, FileText, User, Megaphone } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';

export default function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { unreadCount, unreadNoticeCount } = useNotifications();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);

  // Only show for student users, not admin
  if (!user || user.role === 'Admin') return null;

  const navItems = [
    {
      path: '/home',
      label: 'Home',
      icon: Home,
      routes: ['/home']
    },
    {
      path: '/posts',
      label: 'Posts',
      icon: FileText,
      routes: ['/posts']
    },
    {
      path: '/notices',
      label: 'Notices',
      icon: Megaphone,
      routes: ['/notices'],
      badge: unreadNoticeCount
    },
    {
      path: '/profile',
      label: 'Profile',
      icon: User,
      routes: ['/profile']
    },
  ];

  // Save last visited tab to localStorage
  useEffect(() => {
    const match = navItems.find((item) =>
      item.routes.includes(location.pathname)
    );
    if (match) {
      localStorage.setItem('cv_last_tab', match.path);
    }
  }, [location.pathname]);

  // Close menu on outside click / touch
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, []);

  // Check if a nav item is active based on current route
  const isActive = (item) => {
    return item.routes.includes(location.pathname);
  };

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'U';

  return (
    <>
      {/* Mobile: Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 bg-srec-card border-t border-gray-100 md:hidden safe-area-pb">
        <div className="h-16 flex items-center px-2">

          {/* Profile avatar — positioned left of nav bar */}
          <div ref={menuRef} className="relative flex items-center pl-1 pr-2 flex-shrink-0">
            <button
              onClick={() => setShowMenu(v => !v)}
              className="relative w-9 h-9 rounded-full bg-srec-primary text-white text-sm font-bold flex items-center justify-center shadow-sm flex-shrink-0">
              {initials}
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {showMenu && (
              <div className="absolute bottom-full left-0 mb-3 w-52 bg-white rounded-2xl shadow-xl border border-gray-100 p-3 z-50">
                <p className="font-semibold text-gray-900 text-sm truncate">{user?.name}</p>
                <p className="text-xs text-gray-400 mb-3">{user?.roll_no}</p>
                <button
                  onClick={() => { setShowMenu(false); navigate('/profile'); }}
                  className="w-full text-left text-sm text-gray-700 hover:text-srec-primary py-1.5 transition-colors">
                  View Profile
                </button>
                <hr className="my-2 border-gray-100" />
                <button
                  onClick={() => { logout(); navigate('/login'); }}
                  className="w-full text-left text-sm text-red-600 hover:text-red-700 py-1.5 font-medium transition-colors">
                  Sign Out
                </button>
              </div>
            )}
          </div>

          {/* Nav items — fill remaining space */}
          <div className="flex items-center justify-around flex-1">
            {navItems.map((item) => {
              const active = isActive(item);
              const IconComponent = item.icon;

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  aria-label={item.label}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => localStorage.setItem('cv_last_tab', item.path)}
                  className={`
                    relative flex flex-col items-center justify-center flex-1 py-1
                    transition-all duration-200
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-srec-primary
                    ${active
                      ? 'text-srec-primary'
                      : 'text-gray-400 hover:text-gray-600'
                    }
                  `}
                >
                  <div className="relative flex flex-col items-center justify-center gap-0.5">
                    {active ? (
                      <div className="relative flex items-center gap-1.5 bg-srec-primary/10 text-srec-primary rounded-full px-3 py-1 transition-all duration-200">
                        <IconComponent
                          size={20}
                          strokeWidth={2.5}
                          className="text-srec-primary"
                        />
                        <span className="text-xs font-semibold text-srec-primary leading-none">
                          {item.label}
                        </span>
                        {item.badge > 0 && (
                          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                            {item.badge > 9 ? '9+' : item.badge}
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="relative p-2 rounded-full transition-all duration-200">
                        <IconComponent
                          size={22}
                          strokeWidth={2}
                        />
                        {item.badge > 0 && (
                          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                            {item.badge > 9 ? '9+' : item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </NavLink>
              );
            })}
          </div>
        </div>
        {/* Safe area for devices with home indicator */}
        <div className="h-[env(safe-area-inset-bottom,0px)] bg-srec-card" />
      </nav>

      {/* Desktop: Left sidebar */}
      <nav className="hidden md:flex fixed left-0 top-16 bottom-0 z-20 w-20 flex-col items-center bg-srec-card border-r border-srec-border pt-6 shadow-sm">
        {navItems.map((item) => {
          const active = isActive(item);
          const IconComponent = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              aria-label={item.label}
              aria-current={active ? 'page' : undefined}
              onClick={() => localStorage.setItem('cv_last_tab', item.path)}
              className={`
                group my-3 w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 relative
                ${active
                  ? 'bg-srec-primary/10 text-srec-primary shadow-inner'
                  : 'text-gray-400 hover:bg-gray-50 hover:text-gray-600'
                }
              `}
            >
              <IconComponent
                size={24}
                strokeWidth={active ? 2.5 : 2}
                className={active ? 'text-srec-primary' : ''}
              />
              {item.badge > 0 && (
                <span className="absolute top-1 right-1 min-w-[16px] h-4 px-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                  {item.badge > 9 ? '9+' : item.badge}
                </span>
              )}
              <span className="sr-only">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}
