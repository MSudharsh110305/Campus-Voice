import React, { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, FileText, User, Users, Megaphone } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';

export default function BottomNav() {
  const location = useLocation();
  const { user } = useAuth();
  const { unreadNoticeCount } = useNotifications();

  if (!user || user.role === 'Admin') return null;

  const navItems = [
    { path: '/home',      label: 'Home',      icon: Home,      routes: ['/home'] },
    { path: '/posts',     label: 'Posts',     icon: FileText,  routes: ['/posts', '/my-complaints'] },
    { path: '/petitions', label: 'Community', icon: Users,     routes: ['/petitions', '/wins', '/changelog'] },
    { path: '/notices',   label: 'Notices',   icon: Megaphone, routes: ['/notices'] },
    { path: '/profile',   label: 'Profile',   icon: User,      routes: ['/profile'] },
  ];

  useEffect(() => {
    const match = navItems.find((item) => item.routes.includes(location.pathname));
    if (match) localStorage.setItem('cv_last_tab', match.path);
  }, [location.pathname]);

  const isActive = (item) => item.routes.includes(location.pathname);

  return (
    <>
      {/* Mobile: Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 bg-white/90 backdrop-blur-xl border-t border-srec-borderLight md:hidden shadow-[0_-1px_8px_rgba(0,0,0,0.06)]" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
        <div className="h-16 flex items-center justify-around px-1 min-w-0">
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
                  relative flex flex-col items-center justify-center flex-1 py-1 min-h-[44px]
                  transition-all duration-200
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-srec-primary
                  ${active ? 'text-srec-primary' : 'text-gray-400 hover:text-gray-600'}
                `}
              >
                <div className="relative flex flex-col items-center justify-center gap-0.5">
                  {active ? (
                    <div className="relative flex items-center gap-1 bg-srec-primarySoft text-srec-primary rounded-full px-2.5 py-1 shadow-inner-soft transition-all duration-300">
                      <IconComponent size={16} strokeWidth={2.5} />
                      <span className="text-[11px] font-semibold leading-none">{item.label}</span>
                      {item.path === '/notices' && unreadNoticeCount > 0 && (
                        <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] bg-red-500 text-white text-[8px] font-bold rounded-full flex items-center justify-center px-0.5 leading-none">
                          {unreadNoticeCount > 9 ? '9+' : unreadNoticeCount}
                        </span>
                      )}
                    </div>
                  ) : (
                    <div className="relative p-2 rounded-full transition-all duration-200">
                      <IconComponent size={20} strokeWidth={2} />
                      {item.path === '/notices' && unreadNoticeCount > 0 && (
                        <span className="absolute top-1 right-1 min-w-[16px] h-[16px] bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center px-0.5 leading-none">
                          {unreadNoticeCount > 9 ? '9+' : unreadNoticeCount}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </NavLink>
            );
          })}
        </div>
        {/* Safe area spacer already handled by paddingBottom on nav */}
      </nav>

      {/* Desktop: Left sidebar */}
      <nav className="hidden md:flex fixed left-0 top-16 bottom-0 z-20 w-20 flex-col items-center bg-white/80 backdrop-blur-xl border-r border-srec-borderLight pt-4 shadow-soft">
        {navItems.map((item) => {
          const active = isActive(item);
          const IconComponent = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              aria-label={item.label}
              title={item.label}
              aria-current={active ? 'page' : undefined}
              onClick={() => localStorage.setItem('cv_last_tab', item.path)}
              className={`
                group my-2 w-12 h-12 flex flex-col items-center justify-center rounded-xl transition-all duration-200 relative gap-0.5
                ${active
                  ? 'bg-srec-primarySoft text-srec-primary shadow-inner-soft'
                  : 'text-gray-400 hover:bg-srec-backgroundAlt hover:text-srec-textSecondary'
                }
              `}
            >
              <div className="relative">
                <IconComponent size={20} strokeWidth={active ? 2.5 : 2} />
                {item.path === '/notices' && unreadNoticeCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] bg-red-500 text-white text-[8px] font-bold rounded-full flex items-center justify-center px-0.5 leading-none">
                    {unreadNoticeCount > 9 ? '9+' : unreadNoticeCount}
                  </span>
                )}
              </div>
              <span className="text-[9px] font-medium leading-none">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}
