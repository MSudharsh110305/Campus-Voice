import React, { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, FileText, User, Megaphone } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';

export default function BottomNav() {
  const location = useLocation();
  const { user } = useAuth();
  const { unreadNoticeCount } = useNotifications();

  // Only show for student users, not admin
  if (!user || user.role === 'Admin') return null;

  const navItems = [
    { path: '/home',    label: 'Home',    icon: Home,     routes: ['/home'] },
    { path: '/posts',   label: 'Posts',   icon: FileText, routes: ['/posts'] },
    { path: '/notices', label: 'Notices', icon: Megaphone,routes: ['/notices'], badge: unreadNoticeCount },
    { path: '/profile', label: 'Profile', icon: User,     routes: ['/profile'] },
  ];

  // Save last visited tab to localStorage
  useEffect(() => {
    const match = navItems.find((item) => item.routes.includes(location.pathname));
    if (match) localStorage.setItem('cv_last_tab', match.path);
  }, [location.pathname]);

  const isActive = (item) => item.routes.includes(location.pathname);

  return (
    <>
      {/* Mobile: Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 bg-white/90 backdrop-blur-xl border-t border-srec-borderLight md:hidden safe-area-pb shadow-[0_-1px_8px_rgba(0,0,0,0.06)]">
        <div className="h-16 flex items-center justify-around px-2">
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
                  ${active ? 'text-srec-primary' : 'text-gray-400 hover:text-gray-600'}
                `}
              >
                <div className="relative flex flex-col items-center justify-center gap-0.5">
                  {active ? (
                    <div className="relative flex items-center gap-1.5 bg-srec-primarySoft text-srec-primary rounded-full px-3 py-1 shadow-inner-soft transition-all duration-300">
                      <IconComponent size={18} strokeWidth={2.5} />
                      <span className="text-xs font-semibold leading-none">{item.label}</span>
                      {item.badge > 0 && (
                        <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center border border-white leading-none">
                          {item.badge > 9 ? '9+' : item.badge}
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="relative p-2 rounded-full transition-all duration-200">
                      <IconComponent size={22} strokeWidth={2} />
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
        {/* Safe area for devices with home indicator */}
        <div className="h-[env(safe-area-inset-bottom,0px)] bg-white/90" />
      </nav>

      {/* Desktop: Left sidebar */}
      <nav className="hidden md:flex fixed left-0 top-16 bottom-0 z-20 w-20 flex-col items-center bg-white/80 backdrop-blur-xl border-r border-srec-borderLight pt-6 shadow-soft">
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
                  ? 'bg-srec-primarySoft text-srec-primary shadow-inner-soft'
                  : 'text-gray-400 hover:bg-srec-backgroundAlt hover:text-srec-textSecondary'
                }
              `}
            >
              <IconComponent size={22} strokeWidth={active ? 2.5 : 2} />
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
